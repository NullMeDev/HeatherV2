#!/usr/bin/env python3
"""
Niche Site Scraper - Standalone CLI tool to find Stripe/WooCommerce sites
Run from terminal: python niche_scraper.py sites.txt --output results.json
"""

import requests
import re
import json
import argparse
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import time

warnings.filterwarnings('ignore')
requests.packages.urllib3.disable_warnings()

class NicheScraper:
    def __init__(self, proxy: str = None, timeout: int = 15):
        self.proxy = proxy
        self.timeout = timeout
        self.proxies = {'http': proxy, 'https': proxy} if proxy else None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    def normalize_url(self, url: str) -> str:
        url = url.strip()
        if url.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
            url = re.sub(r'^\d+\.\s*', '', url)
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    def get_domain(self, url: str) -> str:
        parsed = urlparse(self.normalize_url(url))
        return parsed.netloc.replace('www.', '')
    
    def scan_site(self, url: str) -> Dict:
        url = self.normalize_url(url)
        domain = self.get_domain(url)
        
        result = {
            'url': url,
            'domain': domain,
            'platform': None,
            'stripe_key': None,
            'stripe_type': None,
            'woocommerce': False,
            'shopify': False,
            'bigcommerce': False,
            'magento': False,
            'braintree': False,
            'paypal': False,
            'square': False,
            'status': 'pending',
            'error': None
        }
        
        try:
            response = requests.get(
                url, 
                headers=self.headers, 
                timeout=self.timeout, 
                proxies=self.proxies, 
                verify=False,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                result['status'] = 'error'
                result['error'] = f'HTTP {response.status_code}'
                return result
            
            html = response.text.lower()
            html_original = response.text
            
            # Detect Stripe keys
            pk_live = re.findall(r'pk_live_[a-zA-Z0-9]{20,}', html_original)
            pk_test = re.findall(r'pk_test_[a-zA-Z0-9]{20,}', html_original)
            
            if pk_live:
                result['stripe_key'] = pk_live[0]
                result['stripe_type'] = 'live'
            elif pk_test:
                result['stripe_key'] = pk_test[0]
                result['stripe_type'] = 'test'
            
            # Detect platforms
            if 'woocommerce' in html or 'wc-ajax' in html or '/wp-content/plugins/woocommerce' in html:
                result['woocommerce'] = True
                result['platform'] = 'WooCommerce'
            
            if 'shopify' in html or 'cdn.shopify.com' in html or 'myshopify.com' in html:
                result['shopify'] = True
                result['platform'] = 'Shopify'
            
            if 'bigcommerce' in html or 'cdn.bigcommerce.com' in html:
                result['bigcommerce'] = True
                result['platform'] = 'BigCommerce'
            
            if 'magento' in html or 'mage-init' in html:
                result['magento'] = True
                result['platform'] = 'Magento'
            
            # Detect payment processors
            if 'braintree' in html or 'braintreegateway' in html:
                result['braintree'] = True
            
            if 'paypal' in html or 'paypalobjects.com' in html:
                result['paypal'] = True
            
            if 'squareup.com' in html or 'square.com' in html:
                result['square'] = True
            
            # Set status
            if result['stripe_key']:
                result['status'] = 'stripe_found'
            elif result['woocommerce'] or result['shopify'] or result['bigcommerce']:
                result['status'] = 'ecommerce'
            else:
                result['status'] = 'scanned'
            
            return result
            
        except requests.exceptions.Timeout:
            result['status'] = 'error'
            result['error'] = 'Timeout'
        except requests.exceptions.ConnectionError:
            result['status'] = 'error'
            result['error'] = 'Connection error'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)[:50]
        
        return result
    
    def scan_sites(self, urls: List[str], concurrency: int = 10, callback=None) -> List[Dict]:
        results = []
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(self.scan_site, url): url for url in urls}
            
            for i, future in enumerate(as_completed(futures)):
                try:
                    result = future.result()
                    results.append(result)
                    
                    if callback:
                        callback(i + 1, len(urls), result)
                except Exception as e:
                    results.append({
                        'url': futures[future],
                        'status': 'error',
                        'error': str(e)
                    })
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Niche Site Scraper - Find Stripe/WooCommerce sites')
    parser.add_argument('input', help='Input file with URLs (one per line)')
    parser.add_argument('-o', '--output', default='results.json', help='Output JSON file')
    parser.add_argument('-c', '--concurrency', type=int, default=10, help='Concurrent requests')
    parser.add_argument('-p', '--proxy', help='Proxy URL (http://user:pass@host:port)')
    parser.add_argument('-t', '--timeout', type=int, default=15, help='Request timeout in seconds')
    parser.add_argument('--stripe-only', action='store_true', help='Only output sites with Stripe keys')
    parser.add_argument('--woo-only', action='store_true', help='Only output WooCommerce sites')
    
    args = parser.parse_args()
    
    # Read URLs
    with open(args.input, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    # Remove duplicates and numbered prefixes
    clean_urls = []
    seen = set()
    for url in urls:
        url = re.sub(r'^\d+\.\s*', '', url)
        if url and url not in seen:
            clean_urls.append(url)
            seen.add(url)
    
    print(f'Scanning {len(clean_urls)} unique sites...')
    print('=' * 50)
    
    scraper = NicheScraper(proxy=args.proxy, timeout=args.timeout)
    
    stripe_found = []
    woo_found = []
    
    def progress(current, total, result):
        status = result.get('status', 'unknown')
        domain = result.get('domain', 'unknown')
        
        if result.get('stripe_key'):
            stripe_found.append(result)
            print(f'[{current}/{total}] STRIPE: {domain} - {result["stripe_key"][:30]}...')
        elif result.get('woocommerce'):
            woo_found.append(result)
            print(f'[{current}/{total}] WOO: {domain}')
        elif current % 10 == 0:
            print(f'[{current}/{total}] Scanning...')
    
    start = time.time()
    results = scraper.scan_sites(clean_urls, concurrency=args.concurrency, callback=progress)
    elapsed = time.time() - start
    
    # Filter results if needed
    if args.stripe_only:
        results = [r for r in results if r.get('stripe_key')]
    elif args.woo_only:
        results = [r for r in results if r.get('woocommerce')]
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    print('=' * 50)
    print(f'Scan complete in {elapsed:.1f}s')
    print(f'Total scanned: {len(clean_urls)}')
    print(f'Stripe keys found: {len(stripe_found)}')
    print(f'WooCommerce sites: {len(woo_found)}')
    print(f'Results saved to: {args.output}')
    
    if stripe_found:
        print('\n=== STRIPE KEYS FOUND ===')
        for r in stripe_found:
            print(f'{r["domain"]}: {r["stripe_key"]}')


if __name__ == '__main__':
    main()
