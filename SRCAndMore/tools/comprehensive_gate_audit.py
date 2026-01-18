#!/usr/bin/env python3
"""
Comprehensive Gate Audit Tool
Tests all provided cards against each working gate to verify real API calls
Measures response times and analyzes behavior patterns
"""

import sys
import os
import time
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Tuple, List, Dict

GOOD_CARDS = [
    ("4223240003853798", "12", "27", "621", "Unknown Visa"),
    ("4758330007582445", "02", "26", "288", "Unknown Visa"),
    ("4569330184105878", "08", "29", "788", "Unknown Visa"),
    ("5573770009390653", "03", "28", "963", "Unknown MC"),
    ("5429331453045149", "07", "26", "961", "Unknown MC"),
]

BAD_CARDS = [
    ("4000000000000002", "12", "29", "123", "Stripe Test Declined"),
    ("4000000000009995", "12", "29", "123", "Stripe Insufficient Funds"),
    ("4000000000000069", "12", "29", "123", "Stripe Expired Card"),
    ("4100000000000019", "12", "29", "123", "Visa Fraud Block"),
    ("5100000000000016", "12", "29", "123", "MC Fraud Block"),
]

EDGE_CARDS = [
    ("4111111111111111", "12", "29", "123", "Common Test Card"),
    ("5500000000000004", "12", "29", "111", "MC Test Card"),
    ("378282246310005", "12", "29", "1234", "Amex Test"),
    ("4000000000000127", "12", "29", "000", "Stripe Wrong CVV"),
    ("4242424242424242", "12", "29", "999", "Stripe Standard Test"),
]

ALL_CARDS = GOOD_CARDS + BAD_CARDS + EDGE_CARDS

def test_gate(gate_name: str, gate_fn, cards: List[Tuple]) -> Dict:
    """Test a gate with all cards and collect metrics"""
    results = {
        "gate": gate_name,
        "total_cards": len(cards),
        "live": 0,
        "declined": 0,
        "errors": 0,
        "bad_card_live": 0,
        "avg_time_ms": 0,
        "min_time_ms": float('inf'),
        "max_time_ms": 0,
        "responses": [],
        "suspicious": False,
        "false_positive": False,
        "reason": ""
    }
    
    total_time = 0
    bad_card_nums = [c[0] for c in BAD_CARDS]
    
    for i, card_tuple in enumerate(cards):
        if len(card_tuple) == 5:
            card_num, mon, year, cvv, desc = card_tuple
        else:
            card_num, mon, year, cvv = card_tuple
            desc = "Unknown"
        try:
            start = time.time()
            response, proxy_ok = gate_fn(card_num, mon, year, cvv)
            elapsed_ms = (time.time() - start) * 1000
            
            total_time += elapsed_ms
            results["min_time_ms"] = min(results["min_time_ms"], elapsed_ms)
            results["max_time_ms"] = max(results["max_time_ms"], elapsed_ms)
            
            card_short = f"{card_num[:6]}...{card_num[-4:]}"
            
            is_live = "LIVE" in response.upper() or "APPROVED" in response.upper() or "TOKENIZED" in response.upper() or "CHARGED" in response.upper()
            is_error = "ERROR" in response.upper() or "TIMEOUT" in response.upper()
            
            if is_live:
                results["live"] += 1
                status = "LIVE"
                if card_num in bad_card_nums:
                    results["bad_card_live"] += 1
            elif is_error:
                results["errors"] += 1
                status = "ERROR"
            else:
                results["declined"] += 1
                status = "DECLINED"
            
            results["responses"].append({
                "card": card_short,
                "desc": desc,
                "status": status,
                "response": response[:60],
                "time_ms": round(elapsed_ms, 1)
            })
            
            flag = " ⚠️ FALSE POS" if (is_live and card_num in bad_card_nums) else ""
            print(f"  [{i+1:02d}/{len(cards)}] {card_short} ({desc[:15]}): {response[:45]} ({elapsed_ms:.0f}ms){flag}")
            
            time.sleep(0.3)
            
        except Exception as e:
            results["errors"] += 1
            results["responses"].append({
                "card": f"{card_num[:6]}...{card_num[-4:]}",
                "status": "ERROR",
                "response": str(e)[:50],
                "time_ms": 0
            })
            print(f"  [{i+1:02d}/{len(cards)}] ERROR: {str(e)[:40]}")
    
    if results["min_time_ms"] == float('inf'):
        results["min_time_ms"] = 0
    
    results["avg_time_ms"] = total_time / len(cards) if cards else 0
    
    if results["bad_card_live"] > 0:
        results["false_positive"] = True
        results["suspicious"] = True
        results["reason"] = f"FALSE POSITIVE: {results['bad_card_live']} bad cards approved"
    elif results["avg_time_ms"] < 100 and results["live"] > 0:
        results["suspicious"] = True
        results["reason"] = "Too fast (<100ms avg) - likely mocked"
    elif results["errors"] == len(cards):
        results["suspicious"] = True
        results["reason"] = "All cards errored - gate broken"
    elif results["live"] == len(cards):
        results["suspicious"] = True
        results["reason"] = "All LIVE - no declines = suspicious"
    
    return results


def main():
    print("=" * 70)
    print("COMPREHENSIVE GATE AUDIT")
    print(f"Testing {len(ALL_CARDS)} cards ({len(GOOD_CARDS)} good, {len(BAD_CARDS)} bad, {len(EDGE_CARDS)} edge)")
    print("=" * 70)
    print()
    
    gates = {}
    
    print("[*] Loading gates...")
    
    try:
        from gates.stripe_auth import stripe_auth_check
        gates["stripe_auth (/sa)"] = stripe_auth_check
        print("  [+] stripe_auth loaded")
    except Exception as e:
        print(f"  [-] stripe_auth FAILED: {e}")
    
    try:
        from gates.stripe_charity import gateway_check as stripe_charity_check
        gates["stripe_charity (/sc2)"] = stripe_charity_check
        print("  [+] stripe_charity loaded")
    except Exception as e:
        print(f"  [-] stripe_charity FAILED: {e}")
    
    try:
        from gates.shopify_nano import shopify_nano_check
        gates["shopify_nano (/sn)"] = shopify_nano_check
        print("  [+] shopify_nano loaded")
    except Exception as e:
        print(f"  [-] shopify_nano FAILED: {e}")
    
    try:
        from gates.pariyatti_auth import pariyatti_auth_check
        gates["pariyatti_auth (/pa)"] = pariyatti_auth_check
        print("  [+] pariyatti_auth loaded")
    except Exception as e:
        print(f"  [-] pariyatti_auth FAILED: {e}")
    
    try:
        from gates.cedine_auth import cedine_auth_check
        gates["cedine_auth (/ced)"] = cedine_auth_check
        print("  [+] cedine_auth loaded")
    except Exception as e:
        print(f"  [-] cedine_auth FAILED: {e}")
    
    try:
        from gates.lions_club import lions_club_check
        gates["lions_club (/lc5)"] = lions_club_check
        print("  [+] lions_club loaded")
    except Exception as e:
        print(f"  [-] lions_club FAILED: {e}")
    
    try:
        from gates.tsa import tsa_check
        gates["tsa (/tsa)"] = tsa_check
        print("  [+] tsa loaded")
    except Exception as e:
        print(f"  [-] tsa FAILED: {e}")
    
    try:
        from gates.woostripe import woostripe_check
        gates["woostripe (/wsc1)"] = woostripe_check
        print("  [+] woostripe loaded")
    except Exception as e:
        print(f"  [-] woostripe FAILED: {e}")
    
    try:
        from gates.woostripe_auth import woostripe_auth_check
        gates["woostripe_auth (/wsa)"] = woostripe_auth_check
        print("  [+] woostripe_auth loaded")
    except Exception as e:
        print(f"  [-] woostripe_auth FAILED: {e}")
    
    try:
        from gates.shopify_charge import shopify_charge_check
        gates["shopify_charge (/shc)"] = shopify_charge_check
        print("  [+] shopify_charge loaded")
    except Exception as e:
        print(f"  [-] shopify_charge FAILED: {e}")
    
    try:
        from gates.braintree import braintree_check
        gates["braintree (/b3)"] = braintree_check
        print("  [+] braintree loaded")
    except Exception as e:
        print(f"  [-] braintree FAILED: {e}")
    
    try:
        from gates.braintree_vkrm import braintree_vkrm_check
        gates["braintree_vkrm (/bv)"] = braintree_vkrm_check
        print("  [+] braintree_vkrm loaded")
    except Exception as e:
        print(f"  [-] braintree_vkrm FAILED: {e}")
    
    try:
        from gates.stripe_20 import stripe_20_check
        gates["stripe_20 (/s20)"] = stripe_20_check
        print("  [+] stripe_20 loaded")
    except Exception as e:
        print(f"  [-] stripe_20 FAILED: {e}")
    
    print()
    print(f"[*] Loaded {len(gates)} gates for testing")
    print()
    
    all_results = []
    
    for gate_name, gate_fn in gates.items():
        print("-" * 70)
        print(f"TESTING: {gate_name}")
        print("-" * 70)
        
        result = test_gate(gate_name, gate_fn, ALL_CARDS)
        all_results.append(result)
        
        print()
        print(f"  Summary: {result['live']} LIVE | {result['declined']} DECLINED | {result['errors']} ERRORS")
        print(f"  Timing: avg={result['avg_time_ms']:.0f}ms, min={result['min_time_ms']:.0f}ms, max={result['max_time_ms']:.0f}ms")
        if result['suspicious']:
            print(f"  [!] SUSPICIOUS: {result['reason']}")
        print()
    
    print("=" * 70)
    print("FINAL AUDIT RESULTS")
    print("=" * 70)
    print()
    print(f"{'Gate':<30} {'LIVE':>6} {'DECL':>6} {'ERR':>5} {'FP':>4} {'Avg ms':>8} {'Status':<25}")
    print("-" * 95)
    
    working = []
    broken = []
    suspicious = []
    false_pos = []
    
    for r in all_results:
        gate_short = r['gate'][:28]
        status = ""
        
        if r.get('false_positive'):
            status = f"FALSE POS ({r['bad_card_live']} bad approved)"
            false_pos.append(r['gate'])
        elif r['suspicious']:
            status = f"SUSPICIOUS: {r['reason'][:20]}"
            suspicious.append(r['gate'])
        elif r['errors'] > len(ALL_CARDS) * 0.5:
            status = "BROKEN (>50% errors)"
            broken.append(r['gate'])
        elif r['live'] == 0 and r['declined'] == len(ALL_CARDS):
            status = "BROKEN (all declined)"
            broken.append(r['gate'])
        else:
            status = "WORKING ✓"
            working.append(r['gate'])
        
        print(f"{gate_short:<30} {r['live']:>6} {r['declined']:>6} {r['errors']:>5} {r.get('bad_card_live',0):>4} {r['avg_time_ms']:>8.0f} {status:<25}")
    
    print()
    print("=" * 70)
    print("FINAL CLASSIFICATION")
    print("=" * 70)
    
    print(f"\n✅ VERIFIED WORKING ({len(working)}):")
    for g in working:
        print(f"    {g}")
    
    print(f"\n⚠️  FALSE POSITIVE GATES ({len(false_pos)}):")
    for g in false_pos:
        print(f"    {g} - APPROVED BAD CARDS (simulation/mock)")
    
    print(f"\n🔍 SUSPICIOUS GATES ({len(suspicious)}):")
    for g in suspicious:
        print(f"    {g}")
    
    print(f"\n❌ BROKEN GATES ({len(broken)}):")
    for g in broken:
        print(f"    {g}")
    
    return all_results


if __name__ == "__main__":
    main()
