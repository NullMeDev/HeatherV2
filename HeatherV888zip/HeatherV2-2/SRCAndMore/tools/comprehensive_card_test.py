#!/usr/bin/env python3
"""
Test all 12 provided cards through working gates
This gives us real-world success rate data
"""
import os
import sys
import time

# Load environment variables
env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
requests.packages.urllib3.disable_warnings()

# Test cards provided by user
TEST_CARDS = [
    "4430577601819849|08|28|005",
    "4046440006243030|03|27|405",
    "4506940071087207|10|26|572",
    "4242424242424242|12|30|123",
    "4000056655665556|03|29|555",
    "5555555555554444|11|27|123",
    "2223003122003222|06|29|789",
    "5200828282828210|02|28|456",
    "378282246310005|08|27|1234",
    "371449635398431|05|26|4567",
    "6011111111111117|09|29|321",
    "3056930009020004|04|28|987"
]

PROXY_URL = "http://user_pinta:1acNvmOToR6d-country-US-state-Colorado-city-Denver@residential.ip9.io:8000"
PROXY = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

# Top 3 working gates for comprehensive testing
GATES_TO_TEST = [
    ("Stripe", "stripe", "stripe_check"),
    ("Cedine Auth", "cedine_auth", "cedine_auth_check"),
    ("Shopify", "shopify_checkout", "shopify_checkout_check"),
]

def test_card_on_gate(gate_name, module_name, func_name, card):
    """Test one card on one gate"""
    try:
        module = __import__(f"gates.{module_name}", fromlist=[func_name])
        gate_fn = getattr(module, func_name)
        
        parts = card.split('|')
        card_num, card_mon, card_yer, card_cvc = parts
        
        start_time = time.time()
        result, proxy_ok = gate_fn(card_num, card_mon, card_yer, card_cvc, proxy=PROXY)
        elapsed = round(time.time() - start_time, 2)
        
        # Simplified classification
        result_lower = result.lower() if result else ""
        if "live" in result_lower or "approved" in result_lower or "success" in result_lower:
            status = "✅ LIVE"
        elif "declined" in result_lower or "insufficient" in result_lower:
            status = "❌ DECLINED"
        elif "cvv" in result_lower or "cvc" in result_lower:
            status = "⚠️  CVV"
        elif "error" in result_lower:
            status = "❌ ERROR"
        else:
            status = "❓ UNKNOWN"
        
        return {
            'status': status,
            'time': elapsed,
            'result': result[:80] if result else "No response",
            'success': status in ["✅ LIVE", "⚠️  CVV", "❌ DECLINED"]
        }
    except Exception as e:
        return {
            'status': "❌ EXCEPTION",
            'time': 0,
            'result': str(e)[:80],
            'success': False
        }

def main():
    print("=" * 70)
    print("COMPREHENSIVE CARD TESTING - All 12 Cards x 3 Gates")
    print("=" * 70)
    print(f"Proxy: {PROXY_URL[:50]}...")
    print("=" * 70)
    
    overall_results = []
    
    for gate_name, module_name, func_name in GATES_TO_TEST:
        print(f"\n🔍 Testing {gate_name}")
        print("-" * 70)
        
        gate_results = []
        for i, card in enumerate(TEST_CARDS, 1):
            card_label = card.split('|')[0][-4:]
            print(f"  Card {i}/12 (*{card_label})...", end=" ", flush=True)
            
            result = test_card_on_gate(gate_name, module_name, func_name, card)
            gate_results.append(result)
            overall_results.append(result)
            
            print(f"{result['status']} ({result['time']}s)")
            if result['status'] != "✅ LIVE" and result['status'] != "❌ DECLINED":
                print(f"    └─ {result['result']}")
        
        # Gate summary
        successful = sum(1 for r in gate_results if r['success'])
        avg_time = sum(r['time'] for r in gate_results) / len(gate_results)
        print(f"\n  {gate_name} Results: {successful}/{len(TEST_CARDS)} successful ({successful*100//len(TEST_CARDS)}%) | Avg: {avg_time:.2f}s")
    
    # Overall summary
    print("\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)
    total_tests = len(overall_results)
    total_success = sum(1 for r in overall_results if r['success'])
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {total_success} ({total_success*100//total_tests}%)")
    print(f"Failed: {total_tests - total_success} ({(total_tests-total_success)*100//total_tests}%)")
    print("=" * 70)

if __name__ == "__main__":
    main()
