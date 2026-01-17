"""
Gateway information and formatting utilities.
Extracted from transferto.py for domain organization.
"""
from config import GATEWAY_AMOUNTS

__all__ = ['GATE_INFO', 'get_gate_display', 'get_gateway_amount']

GATE_INFO = {
    # Auth Gates
    'stripe_auth': {
        'name': 'Stripe Auth',
        'cmd': '/sa',
        'amount': GATEWAY_AMOUNTS.get('stripe_auth', 0.00),
        'desc': 'Stripe authentication',
        'type': 'auth'
    },
    'braintree_auth': {
        'name': 'Braintree Auth',
        'cmd': '/mbt',
        'amount': GATEWAY_AMOUNTS.get('braintree_auth', 0.00),
        'desc': 'Braintree authentication',
        'type': 'auth'
    },
    'paypal_auth': {
        'name': 'PayPal Auth',
        'cmd': '/pp',
        'amount': GATEWAY_AMOUNTS.get('paypal_auth', 0.00),
        'desc': 'PayPal authentication',
        'type': 'auth'
    },
    'woostripe_auth': {
        'name': 'WooStripe Auth',
        'cmd': '/wsa',
        'amount': GATEWAY_AMOUNTS.get('woostripe_auth', 0.00),
        'desc': 'WooCommerce 3D Secure',
        'type': 'auth'
    },
    # Charge Gates
    'charge1': {
        'name': 'Charge 1',
        'cmd': '/c1',
        'amount': GATEWAY_AMOUNTS.get('stripe', 8.00),
        'desc': 'Standard charge processor',
        'type': 'charge'
    },
    'charge2': {
        'name': 'Charge 2',
        'cmd': '/c2',
        'amount': GATEWAY_AMOUNTS.get('stripe_20', 14.00),
        'desc': 'Standard charge processor',
        'type': 'charge'
    },
    'charge3': {
        'name': 'Charge 3',
        'cmd': '/c3',
        'amount': GATEWAY_AMOUNTS.get('saintvinson_givewp', 0.25),
        'desc': 'Standard charge processor',
        'type': 'charge'
    },
    'charge4': {
        'name': 'Charge 4',
        'cmd': '/c4',
        'amount': GATEWAY_AMOUNTS.get('stripe_js', 25.00),
        'desc': 'Standard charge processor',
        'type': 'charge'
    },
    'charge5': {
        'name': 'Charge 5',
        'cmd': '/c5',
        'amount': GATEWAY_AMOUNTS.get('stripe_payment_intent', 8.00),
        'desc': 'Standard charge processor',
        'type': 'charge'
    },
    'woostripe_charge': {
        'name': 'WooStripe Charge',
        'cmd': '/wsc',
        'amount': GATEWAY_AMOUNTS.get('woostripe_charge', 18.00),
        'desc': 'WooCommerce + Stripe',
        'type': 'charge'
    },
    'paypal_charge': {
        'name': 'PayPal Charge',
        'cmd': '/ppc',
        'amount': GATEWAY_AMOUNTS.get('paypal_charge', 5.00),
        'desc': 'PayPal direct charging',
        'type': 'charge'
    },
    'checkout': {
        'name': 'Checkout',
        'cmd': '/co',
        'amount': GATEWAY_AMOUNTS.get('checkout', 4.00),
        'desc': 'Checkout.com processor',
        'type': 'charge'
    },
    'madystripe': {
        'name': 'MadyStripe',
        'cmd': '/ms',
        'amount': GATEWAY_AMOUNTS.get('madystripe', 7.00),
        'desc': 'Custom Stripe variant',
        'type': 'charge'
    },
}

def get_gate_display(gate_key: str) -> str:
    """Format a gate for display with amount"""
    info = GATE_INFO.get(gate_key, {})
    name = info.get('name', gate_key)
    cmd = info.get('cmd', '')
    amount = info.get('amount', 0)
    return f"{name} ({cmd}) - ${amount:.2f}"

def get_gateway_amount(gateway_name: str) -> float:
    """Get the USD amount for a gateway by name"""
    gateway_map = {
        'paypal': GATEWAY_AMOUNTS.get('paypal_charge', 5.00),
        'paypal_charge': GATEWAY_AMOUNTS.get('paypal_charge', 5.00),
        'stripe_20': GATEWAY_AMOUNTS.get('stripe_20', 14.00),
        'stripe': GATEWAY_AMOUNTS.get('stripe', 8.00),
        'shopify': GATEWAY_AMOUNTS.get('shopify_nano', 0.01),
        'braintree': GATEWAY_AMOUNTS.get('braintree', 1.00),
        'blemart': GATEWAY_AMOUNTS.get('blemart', 0.01),
        'districtpeople': GATEWAY_AMOUNTS.get('districtpeople', 0.99),
        'saintvinson_givewp': GATEWAY_AMOUNTS.get('saintvinson_givewp', 0.25),
        'bgddesigns': GATEWAY_AMOUNTS.get('bgddesigns', 1.99),
        'staleks_florida': GATEWAY_AMOUNTS.get('staleks_florida', 5.99),
        'ccfoundation': GATEWAY_AMOUNTS.get('ccfoundation', 1.00),
        'madystripe': GATEWAY_AMOUNTS.get('madystripe', 7.00),
        'checkout': GATEWAY_AMOUNTS.get('checkout', 4.00),
        'woostripe': GATEWAY_AMOUNTS.get('woostripe', 10.00),
        'woostripe_auth': GATEWAY_AMOUNTS.get('woostripe_auth', 2.99),
        'woostripe_charge': GATEWAY_AMOUNTS.get('woostripe_charge', 18.00),
        'stripe_auth': GATEWAY_AMOUNTS.get('stripe_auth', 0.00),
        'stripe_js': GATEWAY_AMOUNTS.get('stripe_js', 25.00),
        'stripe_payment_intent': GATEWAY_AMOUNTS.get('stripe_payment_intent', 8.00),
    }
    return gateway_map.get(gateway_name.lower(), 0.01)
