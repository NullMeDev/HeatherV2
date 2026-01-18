"""
Mady Stripe Charitable - REAL BANK AUTHORIZATION
Uses charitable donation endpoint for real Payment Intent authorization
"""
import requests
from gates.stripe_payment_intent import process_payment_intent

def madystripe_check(card_number, mm, yy, cvc, proxy=None, timeout=30):
    """
    Mady Stripe - REAL BANK AUTHORIZATION via charitable donation form
    Uses process_payment_intent which submits through donation endpoint for real auth.
    
    Returns tuple (result_str, proxy_ok_bool).
    """
    try:
        result = process_payment_intent(card_number, mm, yy, cvc, proxy=proxy, timeout=timeout)
        if result:
            return (result, True)
    except Exception as e:
        return (f"Error: {str(e)[:50]}", False)
    
    return ("ERROR - Payment Intent processing failed", False)
