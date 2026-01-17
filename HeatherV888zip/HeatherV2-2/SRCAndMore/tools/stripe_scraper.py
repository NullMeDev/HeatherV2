import requests
import re
import os
import warnings
from typing import Optional, Tuple, List, Dict
from urllib.parse import urlparse

warnings.filterwarnings('ignore', message='Unverified HTTPS request')
requests.packages.urllib3.disable_warnings()

def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def extract_stripe_key(url: str, timeout: int = 10) -> Tuple[bool, Optional[str], str]:
    """
    Scan a website for Stripe public keys.
    Returns: (found, pk_key, message)
    """
    url = normalize_url(url)
    domain = urlparse(url).netloc or url
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
    }
    
    proxy = os.environ.get('PROXY')
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout, proxies=proxies, verify=False)
        
        if response.status_code != 200:
            return False, None, f"HTTP {response.status_code}"
        
        html = response.text
        
        pk_patterns = [
            r'pk_live_[a-zA-Z0-9]{20,}',
            r'pk_test_[a-zA-Z0-9]{20,}',
        ]
        
        for pattern in pk_patterns:
            matches = re.findall(pattern, html)
            if matches:
                pk_key = matches[0]
                return True, pk_key, f"Found: {pk_key[:20]}..."
        
        if 'stripe' in html.lower():
            return False, None, "Stripe detected but no key found"
        
        return False, None, "No Stripe integration"
        
    except requests.exceptions.Timeout:
        return False, None, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, None, "Connection error"
    except Exception as e:
        return False, None, str(e)[:50]

def validate_stripe_key(pk_key: str) -> Tuple[bool, str]:
    """
    Validate a Stripe public key by format check only.
    We verify the key format is correct without making API calls.
    """
    if not pk_key:
        return False, "No key provided"
    
    if pk_key.startswith('pk_live_'):
        if len(pk_key) >= 28:
            return True, "Live key format valid"
        return False, "Key too short"
    
    if pk_key.startswith('pk_test_'):
        if len(pk_key) >= 28:
            return True, "Test key format valid"
        return False, "Key too short"
    
    return False, "Invalid key prefix"

def scan_site_for_stripe(url: str) -> Dict:
    """
    Full scan of a site for Stripe integration.
    Returns dict with results.
    """
    found, pk_key, msg = extract_stripe_key(url)
    
    result = {
        'url': url,
        'has_stripe': found,
        'pk_key': pk_key,
        'message': msg,
        'key_valid': False,
    }
    
    if found and pk_key:
        valid, val_msg = validate_stripe_key(pk_key)
        result['key_valid'] = valid
        result['validation_message'] = val_msg
    
    return result
