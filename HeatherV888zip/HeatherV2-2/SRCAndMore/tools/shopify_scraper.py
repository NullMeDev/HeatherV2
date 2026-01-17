"""
Shopify Store Scraper - Scrapes stores, finds cheapest products, saves to database
"""

import requests
import random
import re
import asyncio
from typing import Tuple, Optional, List
from urllib.parse import urlparse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]


def scrape_store_products(store_url: str, max_price: float = 50.0, limit: int = 10) -> dict:
    """
    Scrape a Shopify store for products under max_price.
    
    Returns dict with:
    - success: bool
    - domain: str
    - products: list of dicts with variant_id, title, price, available
    - cheapest: dict with cheapest product info
    - storefront_token: str if found
    - currency: str
    - error: str if failed
    """
    session = requests.Session()
    session.verify = False
    session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
    
    if not store_url.startswith('http'):
        store_url = f"https://{store_url}"
    
    base_url = store_url.rstrip('/')
    parsed = urlparse(base_url)
    domain = parsed.netloc
    
    result = {
        'success': False,
        'domain': domain,
        'products': [],
        'cheapest': None,
        'storefront_token': None,
        'currency': 'USD',
        'error': None,
    }
    
    try:
        resp = session.get(f"{base_url}/products.json?limit=100", timeout=15)
        if resp.status_code != 200:
            result['error'] = f"HTTP {resp.status_code}"
            return result
        
        data = resp.json()
        products_raw = data.get('products', [])
        
        if not products_raw:
            result['error'] = "No products found"
            return result
        
        products = []
        for product in products_raw:
            title = product.get('title', 'Unknown')
            variants = product.get('variants', [])
            
            for variant in variants:
                try:
                    price = float(variant.get('price', 99999))
                    if price > max_price or price < 0.01:
                        continue
                    
                    available = variant.get('available', True)
                    if not available:
                        continue
                    
                    variant_id = variant.get('id')
                    if not variant_id:
                        continue
                    
                    products.append({
                        'variant_id': str(variant_id),
                        'title': f"{title} - {variant.get('title', '')}"[:200],
                        'price': price,
                        'available': True,
                        'currency': 'USD',
                    })
                    
                    if len(products) >= limit:
                        break
                        
                except (ValueError, TypeError):
                    continue
            
            if len(products) >= limit:
                break
        
        if not products:
            result['error'] = f"No products under ${max_price}"
            return result
        
        products.sort(key=lambda x: x['price'])
        result['products'] = products
        result['cheapest'] = products[0]
        result['success'] = True
        
        try:
            home_resp = session.get(base_url, timeout=10)
            token_match = re.search(r'"accessToken"\s*:\s*"([a-f0-9]+)"', home_resp.text)
            if token_match:
                result['storefront_token'] = token_match.group(1)
            
            currency_match = re.search(r'"currency"\s*:\s*"([A-Z]{3})"', home_resp.text)
            if currency_match:
                result['currency'] = currency_match.group(1)
        except:
            pass
        
    except requests.exceptions.Timeout:
        result['error'] = "Timeout"
    except requests.exceptions.ConnectionError:
        result['error'] = "Connection failed"
    except Exception as e:
        result['error'] = str(e)[:50]
    
    return result


def scan_and_save_store(store_url: str, max_price: float = 50.0) -> Tuple[bool, str]:
    """
    Scan a store and save products to database.
    Returns (success, message)
    """
    from tools.shopify_db import (
        add_store, get_store_with_products, update_store_products, 
        mark_store_error, get_engine
    )
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from tools.shopify_db import ShopifyStore
    
    eng = get_engine()
    if not eng:
        return False, "Database not configured"
    
    scraped = scrape_store_products(store_url, max_price=max_price)
    domain = scraped['domain']
    
    with Session(eng) as session:
        store = session.execute(
            select(ShopifyStore).where(ShopifyStore.domain == domain)
        ).scalar_one_or_none()
        
        if not store:
            add_store(store_url)
            store = session.execute(
                select(ShopifyStore).where(ShopifyStore.domain == domain)
            ).scalar_one_or_none()
        
        if not store:
            return False, f"Failed to add store: {domain}"
        
        store_id = store.id
    
    if not scraped['success']:
        mark_store_error(store_id, scraped['error'])
        return False, f"{domain}: {scraped['error']}"
    
    update_store_products(
        store_id=store_id,
        products=scraped['products'],
        storefront_token=scraped['storefront_token'],
        currency=scraped['currency'],
    )
    
    cheapest = scraped['cheapest']
    return True, f"{domain}: {len(scraped['products'])} products, cheapest ${cheapest['price']:.2f}"


async def scan_stores_batch(store_urls: List[str], max_price: float = 50.0, 
                            concurrency: int = 10, progress_callback=None) -> dict:
    """
    Scan multiple stores concurrently and save to database.
    
    Returns dict with:
    - success: int count
    - failed: int count
    - results: list of (domain, success, message)
    """
    semaphore = asyncio.Semaphore(concurrency)
    results = []
    total = len(store_urls)
    
    async def scan_one(url: str, index: int):
        async with semaphore:
            loop = asyncio.get_event_loop()
            success, message = await loop.run_in_executor(
                None, scan_and_save_store, url, max_price
            )
            
            if progress_callback and (index + 1) % 10 == 0:
                try:
                    await progress_callback(index + 1, total)
                except:
                    pass
            
            return (url, success, message)
    
    tasks = [scan_one(url, i) for i, url in enumerate(store_urls)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = 0
    failed_count = 0
    processed = []
    
    for result in results:
        if isinstance(result, Exception):
            failed_count += 1
            processed.append(("unknown", False, str(result)[:50]))
        else:
            url, success, message = result
            if success:
                success_count += 1
            else:
                failed_count += 1
            processed.append((url, success, message))
    
    return {
        'success': success_count,
        'failed': failed_count,
        'results': processed,
    }


def get_next_store_for_checkout() -> Optional[dict]:
    """
    Get next store with products for checkout, cycling through available stores.
    
    Returns dict with:
    - domain: str
    - url: str
    - variant_id: str
    - price: float
    - title: str
    - storefront_token: str (if available)
    """
    from tools.shopify_db import get_random_store_with_product
    
    store = get_random_store_with_product()
    if not store:
        return None
    
    product = store.get('cheapest_product')
    if not product:
        return None
    
    return {
        'domain': store['domain'],
        'url': store['url'],
        'variant_id': product['variant_id'],
        'price': product['price'],
        'title': product.get('title', 'Unknown'),
        'storefront_token': store.get('storefront_token'),
    }


def get_stores_summary() -> dict:
    """Get summary of stored Shopify stores and products"""
    from tools.shopify_db import count_stores, get_engine
    from sqlalchemy.orm import Session
    from sqlalchemy import select, func
    from tools.shopify_db import ShopifyStore, ShopifyProduct
    
    stats = count_stores()
    
    eng = get_engine()
    if eng:
        with Session(eng) as session:
            total_products = session.execute(
                select(func.count(ShopifyProduct.id)).where(ShopifyProduct.available == True)
            ).scalar_one()
            
            avg_price = session.execute(
                select(func.avg(ShopifyProduct.price)).where(ShopifyProduct.available == True)
            ).scalar_one()
            
            min_price = session.execute(
                select(func.min(ShopifyProduct.price)).where(ShopifyProduct.available == True)
            ).scalar_one()
            
            stats['total_products'] = total_products or 0
            stats['avg_price'] = round(avg_price or 0, 2)
            stats['min_price'] = round(min_price or 0, 2)
    
    return stats


if __name__ == "__main__":
    result = scrape_store_products("kyliecosmetics.com", max_price=50)
    print(f"Success: {result['success']}")
    print(f"Products: {len(result['products'])}")
    if result['cheapest']:
        print(f"Cheapest: ${result['cheapest']['price']:.2f} - {result['cheapest']['title'][:50]}")
