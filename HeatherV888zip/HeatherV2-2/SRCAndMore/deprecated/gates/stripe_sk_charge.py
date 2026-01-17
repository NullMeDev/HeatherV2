"""
Stripe SK Charge Gate - Uses stored secret key to charge cards
Uses Payment Methods + Payment Intents API (modern Stripe flow)
"""

import os
import requests
from typing import Tuple

STRIPE_SK = os.environ.get("STRIPE_SK", "")


def stripe_sk_charge(card_num: str, card_mon: str, card_yer: str, card_cvc: str,
                     amount_cents: int = 100, proxy: dict = None) -> Tuple[str, bool]:
    """
    Charge a card using stored Stripe SK via Payment Intents API
    
    Args:
        card_num: Card number
        card_mon: Expiry month
        card_yer: Expiry year
        card_cvc: CVV/CVC
        amount_cents: Amount to charge in cents (default $1.00)
        proxy: Optional proxy dict
    
    Returns:
        Tuple of (status_message, proxy_alive)
    """
    if not STRIPE_SK:
        return ("Error: STRIPE_SK secret not configured", False)
    
    if len(card_yer) == 2:
        card_yer = "20" + card_yer
    
    try:
        session = requests.Session()
        if proxy:
            session.proxies = proxy
        
        headers = {
            'Authorization': f'Bearer {STRIPE_SK}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        pm_data = {
            'type': 'card',
            'card[number]': card_num,
            'card[exp_month]': card_mon,
            'card[exp_year]': card_yer,
            'card[cvc]': card_cvc,
        }
        
        pm_resp = session.post('https://api.stripe.com/v1/payment_methods', 
                               headers=headers, data=pm_data, timeout=20)
        pm_json = pm_resp.json()
        
        if 'error' in pm_json:
            error_msg = pm_json['error'].get('message', 'Unknown error')
            error_code = pm_json['error'].get('code', '')
            decline_code = pm_json['error'].get('decline_code', '')
            
            if error_code == 'incorrect_cvc':
                return ("CCN LIVE - Incorrect CVV", True)
            if error_code == 'invalid_cvc':
                return ("CCN LIVE - Invalid CVV", True)
            if error_code == 'expired_card':
                return ("DECLINED - Expired Card", True)
            if decline_code == 'insufficient_funds':
                return ("CCN LIVE - Insufficient Funds", True)
            if decline_code == 'lost_card':
                return ("DECLINED - Lost Card", True)
            if decline_code == 'stolen_card':
                return ("DECLINED - Stolen Card", True)
            if error_code == 'card_declined':
                return (f"DECLINED - {decline_code or error_msg[:40]}", True)
            return (f"DECLINED - {error_msg[:50]}", True)
        
        pm_id = pm_json.get('id')
        if not pm_id:
            return ("DECLINED - Payment method creation failed", True)
        
        pi_data = {
            'amount': amount_cents,
            'currency': 'usd',
            'payment_method': pm_id,
            'confirm': 'true',
            'off_session': 'true',
            'description': 'Card validation charge',
        }
        
        pi_resp = session.post('https://api.stripe.com/v1/payment_intents',
                               headers=headers, data=pi_data, timeout=20)
        pi_json = pi_resp.json()
        
        if 'error' in pi_json:
            error_msg = pi_json['error'].get('message', 'Unknown error')
            error_code = pi_json['error'].get('code', '')
            decline_code = pi_json['error'].get('decline_code', '')
            
            if error_code == 'incorrect_cvc' or 'cvc' in error_msg.lower():
                return ("CCN LIVE - CVV Issue", True)
            if decline_code == 'insufficient_funds':
                return ("CCN LIVE - Insufficient Funds", True)
            if 'expired' in error_msg.lower():
                return ("DECLINED - Expired Card", True)
            if decline_code in ('lost_card', 'stolen_card', 'pickup_card'):
                return (f"DECLINED - {decline_code.replace('_', ' ').title()}", True)
            if error_code == 'card_declined':
                return (f"DECLINED - {decline_code or error_msg[:40]}", True)
            if 'authentication' in error_msg.lower() or 'authenticate' in error_msg.lower():
                return ("CCN LIVE - 3DS Required", True)
            return (f"DECLINED - {error_msg[:50]}", True)
        
        status = pi_json.get('status', '')
        
        if status == 'succeeded':
            amount = pi_json.get('amount', 0) / 100
            return (f"CHARGED ${amount:.2f}", True)
        
        if status == 'requires_action':
            return ("CCN LIVE - 3DS Required", True)
        
        if status == 'requires_payment_method':
            return ("DECLINED - Payment method failed", True)
        
        return (f"DECLINED - Status: {status}", True)
        
    except requests.exceptions.Timeout:
        return ("Error: Request timeout", False)
    except requests.exceptions.RequestException:
        return ("Error: Network issue", False)
    except Exception as e:
        return (f"Error: {str(e)[:40]}", False)


def stripe_sk_charge_1(card_num: str, card_mon: str, card_yer: str, card_cvc: str,
                       proxy: dict = None) -> Tuple[str, bool]:
    """$1.00 charge"""
    return stripe_sk_charge(card_num, card_mon, card_yer, card_cvc, amount_cents=100, proxy=proxy)


def stripe_sk_charge_5(card_num: str, card_mon: str, card_yer: str, card_cvc: str,
                       proxy: dict = None) -> Tuple[str, bool]:
    """$5.00 charge"""
    return stripe_sk_charge(card_num, card_mon, card_yer, card_cvc, amount_cents=500, proxy=proxy)


if __name__ == "__main__":
    result, alive = stripe_sk_charge_1("4000000000000002", "12", "29", "123")
    print(f"Result: {result}, Proxy OK: {alive}")
