"""
Stripe Direct Gate - Uses STRIPE_SK secret key for direct card validation
Most reliable Stripe gate - no site scraping required
Creates PaymentMethod then confirms via PaymentIntent for actual verification
"""

import os
import requests
import random
from typing import Tuple
from faker import Faker


def _get_stripe_sk() -> str:
    """Retrieve Stripe secret key from environment at runtime"""
    return os.environ.get('STRIPE_SK', '')


def stripe_direct_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str, 
                        amount: int = 100, proxy=None) -> Tuple[str, bool]:
    """
    Direct Stripe card verification using secret key.
    Creates PaymentMethod -> Creates PaymentIntent -> Confirms
    
    Args:
        card_num: Card number
        card_mon: Expiry month (MM)
        card_yer: Expiry year (YY or YYYY)
        card_cvc: CVV
        amount: Amount in cents (default 100 = $1.00)
        proxy: Optional proxy dict
    
    Returns:
        Tuple of (status_message, proxy_alive)
    """
    stripe_sk = _get_stripe_sk()
    
    if not stripe_sk:
        return ("DECLINED ❌ STRIPE_SK not configured", False)
    
    if not stripe_sk.startswith('sk_'):
        return ("DECLINED ❌ Invalid STRIPE_SK format", False)
    
    fake = Faker()
    session = requests.Session()
    
    if proxy:
        if isinstance(proxy, dict):
            session.proxies.update(proxy)
        elif isinstance(proxy, str):
            parts = proxy.split(':')
            if len(parts) == 4:
                session.proxies = {
                    'http': f'http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}',
                    'https': f'http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}'
                }
    
    year = card_yer if len(card_yer) == 4 else f'20{card_yer}'
    
    headers = {
        'Authorization': f'Bearer {stripe_sk}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    try:
        pm_data = {
            'type': 'card',
            'card[number]': card_num,
            'card[exp_month]': card_mon,
            'card[exp_year]': year,
            'card[cvc]': card_cvc,
            'billing_details[name]': fake.name(),
            'billing_details[email]': fake.email(),
            'billing_details[address][postal_code]': fake.postcode(),
            'billing_details[address][country]': 'US',
        }
        
        pm_resp = session.post(
            'https://api.stripe.com/v1/payment_methods',
            headers=headers,
            data=pm_data,
            timeout=20
        )
        
        if pm_resp.status_code == 402:
            err = pm_resp.json().get('error', {})
            return _parse_stripe_error(err, card_num)
        
        pm_json = pm_resp.json()
        
        if 'error' in pm_json:
            return _parse_stripe_error(pm_json['error'], card_num)
        
        pm_id = pm_json.get('id')
        if not pm_id:
            return ("DECLINED ❌ Failed to create payment method", False)
        
        card_info = pm_json.get('card', {})
        brand = card_info.get('brand', 'unknown').upper()
        last4 = card_info.get('last4', card_num[-4:])
        
        pi_data = {
            'amount': amount,
            'currency': 'usd',
            'payment_method': pm_id,
            'confirm': 'true',
            'description': 'Card verification',
            'capture_method': 'manual',
        }
        
        pi_resp = session.post(
            'https://api.stripe.com/v1/payment_intents',
            headers=headers,
            data=pi_data,
            timeout=25
        )
        
        pi_json = pi_resp.json()
        
        if 'error' in pi_json:
            return _parse_stripe_error(pi_json['error'], card_num, brand)
        
        status = pi_json.get('status', '')
        amount_val = pi_json.get('amount', 0) / 100
        
        if status == 'requires_capture':
            pi_id = pi_json.get('id')
            if pi_id:
                session.post(
                    f'https://api.stripe.com/v1/payment_intents/{pi_id}/cancel',
                    headers=headers,
                    timeout=10
                )
            return (f"APPROVED ✅ {brand} ...{last4} | Authorized ${amount_val:.2f}", True)
        
        elif status == 'succeeded':
            return (f"CHARGED ✅ {brand} ...{last4} | ${amount_val:.2f}", True)
        
        elif status == 'requires_action':
            action_type = pi_json.get('next_action', {}).get('type', '3DS')
            return (f"CCN LIVE ✅ {brand} ...{last4} | 3DS Required ({action_type})", True)
        
        elif status == 'requires_payment_method':
            last_error = pi_json.get('last_payment_error', {})
            if last_error:
                return _parse_stripe_error(last_error, card_num, brand)
            return (f"DECLINED ❌ {brand} ...{last4} | Card declined", True)
        
        else:
            return (f"UNKNOWN | {brand} ...{last4} | Status: {status}", True)
        
    except requests.exceptions.Timeout:
        return ("DECLINED ❌ Request timeout", False)
    except requests.exceptions.ConnectionError:
        return ("DECLINED ❌ Connection error", False)
    except Exception as e:
        return (f"ERROR | {str(e)[:50]}", False)


def _parse_stripe_error(error: dict, card_num: str, brand: str = "") -> Tuple[str, bool]:
    """Parse Stripe error and return appropriate response"""
    code = error.get('code', '')
    decline_code = error.get('decline_code', '')
    message = error.get('message', 'Unknown error')
    last4 = card_num[-4:]
    brand_str = f"{brand} " if brand else ""
    
    if decline_code == 'insufficient_funds' or 'insufficient' in message.lower():
        return (f"CCN LIVE ✅ {brand_str}...{last4} | Insufficient Funds (CVV Match)", True)
    
    if code == 'incorrect_cvc' or 'security code' in message.lower() or 'cvc' in message.lower():
        return (f"CVV DEAD ❌ {brand_str}...{last4} | CVV Mismatch - CCN Live", True)
    
    if decline_code == 'expired_card' or 'expired' in message.lower():
        return (f"DECLINED ❌ {brand_str}...{last4} | Expired Card", True)
    
    if decline_code == 'lost_card':
        return (f"DECLINED ❌ {brand_str}...{last4} | Lost Card", True)
    
    if decline_code == 'stolen_card':
        return (f"DECLINED ❌ {brand_str}...{last4} | Stolen Card", True)
    
    if decline_code == 'fraudulent' or 'fraud' in message.lower():
        return (f"DECLINED ❌ {brand_str}...{last4} | Fraud Detected", True)
    
    if decline_code == 'do_not_honor':
        return (f"DECLINED ❌ {brand_str}...{last4} | Do Not Honor", True)
    
    if decline_code == 'incorrect_number' or code == 'invalid_number':
        return (f"DECLINED ❌ {brand_str}...{last4} | Invalid Card Number", True)
    
    if decline_code == 'card_velocity_exceeded':
        return (f"DECLINED ❌ {brand_str}...{last4} | Velocity Limit Exceeded", True)
    
    if code == 'card_declined' or decline_code == 'generic_decline':
        return (f"DECLINED ❌ {brand_str}...{last4} | Card Declined", True)
    
    if 'test' in message.lower() or 'test mode' in message.lower():
        return (f"DECLINED ❌ {brand_str}...{last4} | Test Card Rejected", True)
    
    return (f"DECLINED ❌ {brand_str}...{last4} | {decline_code or code or message[:30]}", True)
