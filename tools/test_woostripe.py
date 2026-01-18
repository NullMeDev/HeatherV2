#!/usr/bin/env python3
"""
Test script for WooStripe gate improvements.
Tests:
1. Stripe key extraction with multiple fallback methods
2. Error classification mapping
3. WooCommerce response parsing
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gates.woostripe import (
    extract_stripe_key,
    classify_stripe_error,
    parse_woo_response,
    DECLINE_CODE_MAP
)
from unittest.mock import Mock
import json


def test_extract_stripe_key():
    """Test all Stripe key extraction methods."""
    print("=" * 60)
    print("Testing Stripe Key Extraction")
    print("=" * 60)
    
    test_cases = [
        {
            'name': 'Direct pk_live in HTML',
            'html': '<html><body>pk_live_abc123XYZ</body></html>',
            'expected': 'pk_live_abc123XYZ'
        },
        {
            'name': 'stripe_params object',
            'html': '''<script>var stripe_params = {"key": "pk_live_fromParams123"};</script>''',
            'expected': 'pk_live_fromParams123'
        },
        {
            'name': 'wc_stripe_params object',
            'html': '''<script>var wc_stripe_params = {key: 'pk_live_wcParams456'};</script>''',
            'expected': 'pk_live_wcParams456'
        },
        {
            'name': 'data-publishable-key attribute',
            'html': '''<div data-publishable-key="pk_live_dataAttr789"></div>''',
            'expected': 'pk_live_dataAttr789'
        },
        {
            'name': 'data-key attribute',
            'html': '''<form data-key="pk_live_shortAttr111"></form>''',
            'expected': 'pk_live_shortAttr111'
        },
        {
            'name': 'Stripe() initialization',
            'html': '''<script>const stripe = Stripe('pk_live_initCall222');</script>''',
            'expected': 'pk_live_initCall222'
        },
        {
            'name': 'new Stripe() initialization',
            'html': '''<script>var stripe = new Stripe("pk_live_newInit333");</script>''',
            'expected': 'pk_live_newInit333'
        },
        {
            'name': 'loadStripe() call',
            'html': '''<script>loadStripe('pk_live_loadStripe444');</script>''',
            'expected': 'pk_live_loadStripe444'
        },
        {
            'name': 'Script block search',
            'html': '''<html><script type="text/javascript">
                // Some config
                window.config = {stripe_key: 'pk_live_scriptBlock555'};
            </script></html>''',
            'expected': 'pk_live_scriptBlock555'
        },
        {
            'name': 'No key found',
            'html': '<html><body>No stripe key here</body></html>',
            'expected': None
        },
    ]
    
    passed = 0
    failed = 0
    
    for tc in test_cases:
        result = extract_stripe_key(tc['html'])
        status = "✅ PASS" if result == tc['expected'] else "❌ FAIL"
        if result == tc['expected']:
            passed += 1
        else:
            failed += 1
        print(f"  {status} - {tc['name']}")
        if result != tc['expected']:
            print(f"       Expected: {tc['expected']}")
            print(f"       Got: {result}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_error_classification():
    """Test Stripe error classification."""
    print("\n" + "=" * 60)
    print("Testing Error Classification")
    print("=" * 60)
    
    test_cases = [
        {
            'name': 'Insufficient funds',
            'error': {'decline_code': 'insufficient_funds', 'message': 'Insufficient funds'},
            'expected': "CCN LIVE - Insufficient Funds"
        },
        {
            'name': 'Incorrect CVC',
            'error': {'decline_code': 'incorrect_cvc', 'message': 'CVC incorrect'},
            'expected': "CCN LIVE - CVV Mismatch"
        },
        {
            'name': 'Invalid CVC',
            'error': {'decline_code': 'invalid_cvc', 'message': 'Invalid CVC'},
            'expected': "CCN LIVE - CVV Mismatch"
        },
        {
            'name': 'Card declined',
            'error': {'decline_code': 'card_declined', 'message': 'Card was declined'},
            'expected': "DECLINED - Card Declined"
        },
        {
            'name': 'Expired card',
            'error': {'decline_code': 'expired_card', 'message': 'Card expired'},
            'expected': "DECLINED - Expired Card"
        },
        {
            'name': 'Do not honor',
            'error': {'decline_code': 'do_not_honor', 'message': 'Do not honor'},
            'expected': "DECLINED - Do Not Honor"
        },
        {
            'name': 'Generic decline',
            'error': {'decline_code': 'generic_decline', 'message': 'Generic decline'},
            'expected': "DECLINED - Generic Decline"
        },
        {
            'name': 'Message fallback - insufficient',
            'error': {'message': 'Your card has insufficient funds'},
            'expected': "CCN LIVE - Insufficient Funds"
        },
        {
            'name': 'Message fallback - security code',
            'error': {'message': "Your card's security code is incorrect"},
            'expected': "CCN LIVE - CVV Mismatch"
        },
        {
            'name': 'Message fallback - expired',
            'error': {'message': 'Your card has expired'},
            'expected': "DECLINED - Expired Card"
        },
        {
            'name': 'Unknown error with message',
            'error': {'code': 'unknown_code', 'message': 'Some unknown error'},
            'expected': "DECLINED - Some unknown error"
        },
    ]
    
    passed = 0
    failed = 0
    
    for tc in test_cases:
        result, _ = classify_stripe_error(tc['error'])
        status = "✅ PASS" if result == tc['expected'] else "❌ FAIL"
        if result == tc['expected']:
            passed += 1
        else:
            failed += 1
        print(f"  {status} - {tc['name']}")
        if result != tc['expected']:
            print(f"       Expected: {tc['expected']}")
            print(f"       Got: {result}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_woo_response_parsing():
    """Test WooCommerce response parsing."""
    print("\n" + "=" * 60)
    print("Testing WooCommerce Response Parsing")
    print("=" * 60)
    
    class MockResponse:
        def __init__(self, json_data=None, text=''):
            self._json = json_data
            self.text = text
        
        def json(self):
            if self._json is None:
                raise json.JSONDecodeError("No JSON", "", 0)
            return self._json
    
    test_cases = [
        {
            'name': 'Success with redirect',
            'response': MockResponse({'success': True, 'redirect': 'https://example.com/thank-you'}),
            'expected_success': True,
            'expected_msg': "Payment Approved"
        },
        {
            'name': 'Success result string',
            'response': MockResponse({'result': 'success', 'redirect': 'https://example.com/order'}),
            'expected_success': True,
            'expected_msg': "Payment Approved"
        },
        {
            'name': 'Error in data.messages',
            'response': MockResponse({'success': False, 'data': {'messages': '<ul><li>Card declined</li></ul>'}}),
            'expected_success': False,
            'expected_msg': "Card declined"
        },
        {
            'name': 'Error in data.error',
            'response': MockResponse({'success': False, 'data': {'error': 'Payment failed'}}),
            'expected_success': False,
            'expected_msg': "Payment failed"
        },
        {
            'name': 'Error in top-level messages',
            'response': MockResponse({'success': False, 'messages': 'Insufficient funds'}),
            'expected_success': False,
            'expected_msg': "Insufficient funds"
        },
        {
            'name': 'Text fallback - success',
            'response': MockResponse(text='Order received. Thank you for your purchase!'),
            'expected_success': True,
            'expected_msg': "Payment Approved"
        },
        {
            'name': 'Text fallback - declined',
            'response': MockResponse(text='Payment failed. Your card was declined.'),
            'expected_success': False,
            'expected_msg': "Payment Declined"
        },
    ]
    
    passed = 0
    failed = 0
    
    for tc in test_cases:
        success, message, _ = parse_woo_response(tc['response'])
        success_match = success == tc['expected_success']
        msg_match = tc['expected_msg'].lower() in message.lower() or message.lower() in tc['expected_msg'].lower()
        
        if success_match and msg_match:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        print(f"  {status} - {tc['name']}")
        if not (success_match and msg_match):
            print(f"       Expected: success={tc['expected_success']}, msg contains '{tc['expected_msg']}'")
            print(f"       Got: success={success}, msg='{message}'")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_decline_code_map():
    """Verify all required decline codes are mapped."""
    print("\n" + "=" * 60)
    print("Testing Decline Code Map Coverage")
    print("=" * 60)
    
    required_codes = [
        'insufficient_funds',
        'incorrect_cvc',
        'card_declined',
        'expired_card',
        'do_not_honor',
    ]
    
    passed = 0
    failed = 0
    
    for code in required_codes:
        if code in DECLINE_CODE_MAP:
            print(f"  ✅ PASS - {code} -> {DECLINE_CODE_MAP[code]}")
            passed += 1
        else:
            print(f"  ❌ FAIL - {code} not found in DECLINE_CODE_MAP")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    print(f"\nTotal decline codes mapped: {len(DECLINE_CODE_MAP)}")
    return failed == 0


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("WooStripe Gate Unit Tests")
    print("=" * 60 + "\n")
    
    results = []
    
    results.append(("Stripe Key Extraction", test_extract_stripe_key()))
    results.append(("Error Classification", test_error_classification()))
    results.append(("WooCommerce Response Parsing", test_woo_response_parsing()))
    results.append(("Decline Code Map", test_decline_code_map()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
