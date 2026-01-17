#!/usr/bin/env python3
"""
Comprehensive Gate Test
Tests all provided cards through each auth and charge gate
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_CARDS = [
    ("5350160566324809", "01", "2026", "519"),
    ("5502096147527790", "09", "2030", "463"),
    ("4108634490168621", "07", "2028", "884"),
    ("5234211922588868", "08", "2027", "745"),
    ("4108639615799085", "05", "2028", "737"),
    ("4305350036346131", "06", "2027", "900"),
    ("5226880771758218", "02", "2030", "622"),
    ("5162929105072907", "07", "2030", "847"),
    ("4593150390664801", "06", "2027", "526"),
    ("4984423523765275", "10", "2027", "976"),
    ("5502098162982769", "06", "2029", "015"),
    ("4108634077470101", "12", "2028", "517"),
    ("5502092742027732", "07", "2027", "024"),
    ("4329584362397019", "02", "2026", "791"),
    ("4568580858619106", "04", "2027", "748"),
    ("5447313442037054", "02", "2028", "396"),
    ("4705980035713430", "07", "2028", "458"),
    ("4350870174535611", "03", "2026", "483"),
    ("2231151331895027", "10", "2029", "818"),
    ("4108633909479009", "01", "2028", "197"),
    ("5502097337051161", "10", "2027", "997"),
    ("4078430021923956", "07", "2027", "963"),
    ("5502095397377385", "09", "2029", "744"),
    ("5162926744371005", "07", "2029", "319"),
    ("4984082028489557", "11", "2027", "824"),
    ("4984011104949390", "02", "2028", "029"),
    ("5502092934683292", "03", "2029", "625"),
    ("5447318309483648", "05", "2026", "117"),
    ("4763336209229118", "01", "2028", "034"),
]

AUTH_GATES = {}
CHARGE_GATES = {}

def load_gates():
    global AUTH_GATES, CHARGE_GATES
    
    try:
        from gates.stripe_auth import stripe_auth_check
        AUTH_GATES["stripe_auth"] = stripe_auth_check
    except Exception as e:
        print(f"[!] Failed to load stripe_auth: {e}")
    
    try:
        from gates.stripe_auth_epicalarc import stripe_auth_epicalarc_check
        AUTH_GATES["stripe_epicalarc"] = stripe_auth_epicalarc_check
    except Exception as e:
        print(f"[!] Failed to load stripe_epicalarc: {e}")
    
    try:
        from gates.stripe_js import stripe_js_check
        AUTH_GATES["stripe_js"] = stripe_js_check
    except Exception as e:
        print(f"[!] Failed to load stripe_js: {e}")
    
    try:
        from gates.pariyatti_auth import pariyatti_auth_check
        AUTH_GATES["pariyatti_auth"] = pariyatti_auth_check
    except Exception as e:
        print(f"[!] Failed to load pariyatti_auth: {e}")
    
    try:
        from gates.braintree import braintree_check
        AUTH_GATES["braintree"] = braintree_check
    except Exception as e:
        print(f"[!] Failed to load braintree: {e}")
    
    try:
        from gates.braintree_auth import braintree_auth_check
        AUTH_GATES["braintree_auth"] = braintree_auth_check
    except Exception as e:
        print(f"[!] Failed to load braintree_auth: {e}")
    
    try:
        from gates.stripe import stripe_check
        CHARGE_GATES["stripe"] = stripe_check
    except Exception as e:
        print(f"[!] Failed to load stripe: {e}")
    
    try:
        from gates.stripe_sk_charge import stripe_sk_charge
        CHARGE_GATES["stripe_sk_charge"] = stripe_sk_charge
    except Exception as e:
        print(f"[!] Failed to load stripe_sk_charge: {e}")
    
    try:
        from gates.lions_club import lions_club_check
        CHARGE_GATES["lions_club"] = lambda n,m,y,c,proxy=None: lions_club_check(n,m,y,c,None)
    except Exception as e:
        print(f"[!] Failed to load lions_club: {e}")
    
    try:
        from gates.tsa_charge import tsa_check
        CHARGE_GATES["tsa_charge"] = tsa_check
    except Exception as e:
        print(f"[!] Failed to load tsa_charge: {e}")

def test_card(gate_name, gate_func, card):
    cc, mm, yy, cvv = card
    card_display = f"{cc[:6]}...{cc[-4:]}"
    
    try:
        start = time.time()
        result = gate_func(cc, mm, yy[-2:], cvv)
        elapsed = time.time() - start
        
        if isinstance(result, tuple):
            response = str(result[0])
        else:
            response = str(result)
        
        response_upper = response.upper()
        
        if "CHARGED" in response_upper or "APPROVED" in response_upper or "SUCCESS" in response_upper:
            status = "APPROVED"
        elif "CCN LIVE" in response_upper or "TOKENIZED" in response_upper or "3DS" in response_upper:
            status = "LIVE"
        elif "CVV" in response_upper or "CVC" in response_upper:
            status = "CVV_ISSUE"
        elif "INSUFFICIENT" in response_upper or "NSF" in response_upper:
            status = "NSF"
        elif "DECLINED" in response_upper:
            status = "DECLINED"
        elif "ERROR" in response_upper or "EXCEPTION" in response_upper:
            status = "ERROR"
        else:
            status = "UNKNOWN"
        
        return {
            "card": card_display,
            "gate": gate_name,
            "status": status,
            "response": response[:100],
            "time_ms": int(elapsed * 1000)
        }
        
    except Exception as e:
        return {
            "card": card_display,
            "gate": gate_name,
            "status": "ERROR",
            "response": str(e)[:100],
            "time_ms": 0
        }

def run_tests(limit_cards=None, limit_gates=None):
    print("=" * 70)
    print("  COMPREHENSIVE GATE TEST")
    print(f"  {len(TEST_CARDS)} cards x {len(AUTH_GATES) + len(CHARGE_GATES)} gates")
    print("=" * 70)
    print()
    
    cards_to_test = TEST_CARDS[:limit_cards] if limit_cards else TEST_CARDS
    
    results = {
        "auth": {},
        "charge": {}
    }
    
    print("=== AUTH GATES ===")
    for gate_name, gate_func in AUTH_GATES.items():
        if limit_gates and gate_name not in limit_gates:
            continue
            
        print(f"\n[{gate_name}] Testing {len(cards_to_test)} cards...")
        gate_results = {"approved": 0, "live": 0, "declined": 0, "error": 0, "details": []}
        
        for card in cards_to_test:
            result = test_card(gate_name, gate_func, card)
            gate_results["details"].append(result)
            
            if result["status"] in ["APPROVED", "LIVE"]:
                gate_results["approved"] += 1
                print(f"  [+] {result['card']}: {result['status']} - {result['response'][:60]}")
            elif result["status"] == "DECLINED":
                gate_results["declined"] += 1
                print(f"  [-] {result['card']}: DECLINED - {result['response'][:60]}")
            elif result["status"] == "CVV_ISSUE":
                gate_results["live"] += 1
                print(f"  [~] {result['card']}: CVV - {result['response'][:60]}")
            elif result["status"] == "NSF":
                gate_results["live"] += 1
                print(f"  [$] {result['card']}: NSF - {result['response'][:60]}")
            else:
                gate_results["error"] += 1
                print(f"  [!] {result['card']}: {result['status']} - {result['response'][:60]}")
            
            time.sleep(0.5)
        
        results["auth"][gate_name] = gate_results
        print(f"  Summary: {gate_results['approved']} approved/live, {gate_results['declined']} declined, {gate_results['error']} errors")
    
    print("\n" + "=" * 70)
    print("=== CHARGE GATES ===")
    for gate_name, gate_func in CHARGE_GATES.items():
        if limit_gates and gate_name not in limit_gates:
            continue
            
        print(f"\n[{gate_name}] Testing {len(cards_to_test)} cards...")
        gate_results = {"approved": 0, "live": 0, "declined": 0, "error": 0, "details": []}
        
        for card in cards_to_test:
            result = test_card(gate_name, gate_func, card)
            gate_results["details"].append(result)
            
            if result["status"] in ["APPROVED", "LIVE"]:
                gate_results["approved"] += 1
                print(f"  [+] {result['card']}: {result['status']} - {result['response'][:60]}")
            elif result["status"] == "DECLINED":
                gate_results["declined"] += 1
                print(f"  [-] {result['card']}: DECLINED - {result['response'][:60]}")
            elif result["status"] == "CVV_ISSUE":
                gate_results["live"] += 1
                print(f"  [~] {result['card']}: CVV - {result['response'][:60]}")
            elif result["status"] == "NSF":
                gate_results["live"] += 1
                print(f"  [$] {result['card']}: NSF - {result['response'][:60]}")
            else:
                gate_results["error"] += 1
                print(f"  [!] {result['card']}: {result['status']} - {result['response'][:60]}")
            
            time.sleep(0.5)
        
        results["charge"][gate_name] = gate_results
        print(f"  Summary: {gate_results['approved']} approved/live, {gate_results['declined']} declined, {gate_results['error']} errors")
    
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)
    
    print("\nAUTH GATES:")
    for gate_name, gate_results in results["auth"].items():
        total = len(gate_results["details"])
        approved = gate_results["approved"] + gate_results["live"]
        print(f"  {gate_name}: {approved}/{total} passed ({approved/total*100:.1f}%)")
    
    print("\nCHARGE GATES:")
    for gate_name, gate_results in results["charge"].items():
        total = len(gate_results["details"])
        approved = gate_results["approved"] + gate_results["live"]
        print(f"  {gate_name}: {approved}/{total} passed ({approved/total*100:.1f}%)")
    
    return results


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    
    load_gates()
    
    print(f"Loaded {len(AUTH_GATES)} auth gates: {list(AUTH_GATES.keys())}")
    print(f"Loaded {len(CHARGE_GATES)} charge gates: {list(CHARGE_GATES.keys())}")
    
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        run_tests(limit_cards=limit)
    else:
        run_tests(limit_cards=5)
