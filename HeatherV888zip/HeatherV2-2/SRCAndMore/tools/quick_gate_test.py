#!/usr/bin/env python3
"""
Quick Gate Status Check

Tests one card through each gate to verify basic functionality.
Use this after code changes for quick smoke testing.

Usage:
    python3 tools/quick_gate_test.py
"""

import os
import sys
import time

# Load environment variables from .env file
env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test one card
TEST_CARD = "4430577601819849|08|28|005"

# Proxy (proper dict format)
PROXY_URL = "http://user_pinta:1acNvmOToR6d-country-US-state-Colorado-city-Denver@residential.ip9.io:8000"
PROXY = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

def test_gate(gate_name: str, module_name: str, func_name: str):
    """Test a single gate with one card"""
    try:
        # Dynamic import
        module = __import__(f"gates.{module_name}", fromlist=[func_name])
        gate_fn = getattr(module, func_name)
        
        # Parse card
        parts = TEST_CARD.split('|')
        card_num, card_mon, card_yer, card_cvc = parts
        
        print(f"\n  Testing {gate_name}...", end=" ", flush=True)
        
        start_time = time.time()
        result, proxy_ok = gate_fn(card_num, card_mon, card_yer, card_cvc, proxy=PROXY)
        elapsed = round(time.time() - start_time, 2)
        
        # Classify
        if result:
            result_lower = result.lower()
            # Handle explicit UNKNOWN responses from gates
            if "unknown" in result_lower and "⚠️" in result:
                status = "⚠️  UNKNOWN (from gate)"
            elif "error" in result_lower or "timeout" in result_lower:
                status = "❌ ERROR"
            elif any(kw in result_lower for kw in ["charged", "approved", "success", "ccn", "live", "tokenized"]):
                status = "✅ OK"
            elif "declined" in result_lower:
                status = "✅ OK (declined)"
            elif "cvv" in result_lower:
                status = "✅ OK (cvv)"
            elif "3ds" in result_lower:
                status = "✅ OK (3ds)"
            else:
                status = "⚠️  UNKNOWN"
        else:
            status = "❌ NO RESPONSE"
        
        print(f"{status} ({elapsed}s)")
        return True if "✅" in status else False
        
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)[:50]}")
        return False


def main():
    print("=" * 60)
    print("QUICK GATE STATUS CHECK")
    print("=" * 60)
    print(f"Test Card: {TEST_CARD}")
    print(f"Proxy: {PROXY_URL[:50]}...")
    print("=" * 60)
    
    # Define gates to test
    gates = [
        ("Pariyatti Auth", "pariyatti_auth", "pariyatti_auth_check"),
        ("Cedine Auth", "cedine_auth", "cedine_auth_check"),
        ("Stripe", "stripe", "stripe_check"),
        ("Stripe Multi", "stripe_multi", "stripe_multi_check"),
        ("Stripe Charity", "stripe_charity", "stripe_charity_check"),
        ("Lions Club", "lions_club", "lions_club_check"),
        ("Mady Stripe", "madystripe", "madystripe_check"),
        ("Stripe Epicalarc", "stripe_auth_epicalarc", "stripe_auth_epicalarc_check"),
        ("Braintree Laguna", "braintree_laguna", "gateway_check"),
        ("WooStripe Auth", "woostripe_auth", "woostripe_auth_check"),
        ("Shopify Checkout", "shopify_checkout", "shopify_checkout_check"),
    ]
    
    working = 0
    total = len(gates)
    
    for gate_name, module_name, func_name in gates:
        if test_gate(gate_name, module_name, func_name):
            working += 1
        time.sleep(1)  # Brief delay between tests
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {working}/{total} gates working ({working/total*100:.0f}%)")
    print("=" * 60)
    
    return 0 if working == total else 1


if __name__ == "__main__":
    sys.exit(main())
