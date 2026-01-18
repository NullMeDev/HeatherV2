"""
Stripe Verified - Complete Payment Intent Flow
Creates Payment Method → Payment Intent → Confirms → Returns Bank Status

CRITICAL: This gate makes REAL charges using Payment Intent API
Returns tuple: (result_message: str, proxy_ok: bool)
"""

import requests
import random
import json
from typing import Tuple, Optional
from urllib.parse import quote_plus
from faker import Faker
from config import get_proxy_for_gateway, STRIPE_SK

# Working Stripe public key
STRIPE_PK = "pk_live_51J9QBJB3FKKIqNlqK2Z7V6Ll6pVH1LLYQD6CxI7QJW3o2dNNZ1Y9B2VKM0KGJ3aF6i4QFoD2Z5VK8"


def _create_payment_method(
    session: requests.Session,
    stripe_pk: str,
    card_num: str,
    card_mon: str,
    card_yer: str,
    card_cvc: str
) -> Tuple[Optional[str], Optional[str]]:
    """Step 1: Create Payment Method via Stripe.js API"""
    fake = Faker()
    url = "https://api.stripe.com/v1/payment_methods"
    
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
            f'&key={stripe_pk}')
    
    try:
        response = session.post(url, headers=headers, data=data, timeout=20)
        
        if response.status_code == 402:
            try:
                error_data = response.json().get('error', {})
                message = error_data.get('message', 'Card declined')
                code = error_data.get('decline_code', error_data.get('code', ''))
                return None, f"{code}: {message}" if code else message
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


def _create_payment_intent_sk(
    session: requests.Session,
    amount_cents: int = 100,
    currency: str = 'usd'
) -> Tuple[Optional[str], Optional[str]]:
    """Step 2: Create Payment Intent using Secret Key"""
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


def _confirm_payment_intent(
    session: requests.Session,
    client_secret: str,
    pm_id: str,
    stripe_pk: str
) -> Tuple[str, bool]:
    """Step 3: Confirm Payment Intent with Payment Method"""
    pi_id = client_secret.split('_secret_')[0]
    url = f"https://api.stripe.com/v1/payment_intents/{pi_id}/confirm"
    
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://js.stripe.com',
        'Referer': 'https://js.stripe.com/'
    }
    
    data = f'payment_method={pm_id}&client_secret={client_secret}&key={stripe_pk}'
    
    try:
        response = session.post(url, headers=headers, data=data, timeout=25)
        data = response.json()
        
        if 'error' in data:
            error = data['error']
            message = error.get('message', 'Unknown error')
            code = error.get('code', error.get('decline_code', ''))
            
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


def gateway_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str, proxy: dict = None) -> Tuple[str, bool]:
    """
    Complete Stripe charge using Payment Intent API
    
    Flow:
    1. Create Payment Method with PK
    2. Create Payment Intent with SK
    3. Confirm Payment Intent
    4. Return bank authorization status
    """
    session = requests.Session()
    session.verify = False
    
    if not proxy:
        proxy = get_proxy_for_gateway('stripe')
    if proxy:
        session.proxies.update(proxy)
    
    if len(card_yer) == 4:
        card_yer = card_yer[2:]
    
    # Step 1: Create PM
    pm_id, pm_error = _create_payment_method(
        session, STRIPE_PK, card_num, card_mon, card_yer, card_cvc
    )
    
    if pm_error:
        if 'insufficient' in pm_error.lower():
            return "APPROVED ✅ CCN Valid - Insufficient Funds", True
        elif 'cvc' in pm_error.lower() or 'cvv' in pm_error.lower():
            return "DECLINED ❌ CVV Mismatch", True
        elif 'expired' in pm_error.lower():
            return "DECLINED ❌ Expired Card", True
        else:
            return f"DECLINED ❌ {pm_error[:60]}", True
    
    if not pm_id:
        return "DECLINED ❌ Payment method creation failed", True
    
    # Step 2: Create PI
    client_secret, pi_error = _create_payment_intent_sk(session, amount_cents=100)
    
    if pi_error:
        return f"DECLINED ❌ {pi_error}", True
    
    if not client_secret:
        return "DECLINED ❌ Could not create payment intent", True
    
    # Step 3: Confirm PI
    result, proxy_ok = _confirm_payment_intent(session, client_secret, pm_id, STRIPE_PK)
    
    return result, proxy_ok


def check_card(card_num: str, card_mon: str, card_yer: str, card_cvc: str, proxy: dict = None) -> Tuple[str, bool]:
    """Alias for gateway_check"""
    return gateway_check(card_num, card_mon, card_yer, card_cvc, proxy)
