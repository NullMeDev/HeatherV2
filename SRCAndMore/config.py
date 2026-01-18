"""
Configuration loader for Phase 6 bot.
Loads settings from .env file with sensible defaults.
"""
import os
from pathlib import Path

# Load .env file if it exists
ENV_FILE = Path(__file__).parent / '.env'
if ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except ImportError:
        print("[WARN] python-dotenv not installed. Reading .env manually.")
        # Simple manual .env parser
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
else:
    print("[WARN] .env file not found. Using environment variables or defaults.")

# ============================================================================
# Telegram Bot Configuration
# ============================================================================
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
if not BOT_TOKEN:
    print("[WARN] BOT_TOKEN not set. Please set BOT_TOKEN in secrets or environment.")

# ============================================================================
# Proxy Configuration
# ============================================================================
PROXY_RAW = os.getenv('PROXY', '')
PROXY_HTTP = os.getenv('PROXY_HTTP', PROXY_RAW if PROXY_RAW else '')
PROXY_HTTPS = os.getenv('PROXY_HTTPS', PROXY_RAW if PROXY_RAW else '')

# Residential proxy for PayPal (required for GraphQL API - bypasses bot detection)
RESIDENTIAL_PROXY = os.getenv('RESIDENTIAL_PROXY', os.getenv('PROXY_RESIDENTIAL', ''))

PROXY = {
    'http': PROXY_HTTP,
    'https': PROXY_HTTPS
}

def get_proxy_for_gateway(gateway_name: str) -> dict:
    """
    Return appropriate proxy configuration based on gateway requirements.
    
    PayPal requires residential proxy for GraphQL API to bypass bot detection.
    Other gateways can use regular HTTP/HTTPS proxies.
    
    Args:
        gateway_name: Name of the gateway (e.g., 'paypal', 'stripe', 'braintree')
        
    Returns:
        dict with 'http' and 'https' proxy URLs, or None if no proxy configured
    """
    paypal_gateways = ['paypal', 'paypal_auth', 'paypal_charge', 'paypal_graphql']
    
    if gateway_name.lower() in paypal_gateways:
        # PayPal REQUIRES residential proxy
        if RESIDENTIAL_PROXY:
            return {'http': RESIDENTIAL_PROXY, 'https': RESIDENTIAL_PROXY}
        else:
            print(f"[WARN] No residential proxy configured for {gateway_name}. PayPal may fail.")
            return None
    else:
        # Other gateways use regular proxy if available
        if PROXY_HTTP and PROXY_HTTPS:
            return {'http': PROXY_HTTP, 'https': PROXY_HTTPS}
        return None

# ============================================================================
# Stripe API Keys
# ============================================================================
# Stripe Secret Key for real payment verification
STRIPE_SK = os.getenv('STRIPE_SK', '')

# Working Stripe public keys from various donation sites
STRIPE_PUBLIC_KEYS = [
    "pk_live_51PigK6CkPPe3zC4rKhd3YawvVPW2yuay4jJXXJuvXfSPjeRxFwjYacM81vRPF2sTipYxqcef70XkpHtZImfYBVrB0028EaRDO4",
    "pk_live_51S7o5bAlwkQv2HnDV77YryHEwVg7wy6ijTgNwepTpMxVHpQbltXi5DBnkMTI9SSu43LfXGu17QuxjumC6atqQ85F00TeJ0lPYw",
    "pk_live_51H2kayClFZfiknz0ZOHZW5F4awL951srQfyibbHj6AhPsJJMeW8DvslUQ1BlvylhWPJ1R1YNMYHdpL3PyG6ymKEu00dNyHWgR7"
]

# Default to first working PK
STRIPE_PK = STRIPE_PUBLIC_KEYS[0]

# ============================================================================
# Gateway Test Amounts (in USD)
# ============================================================================
GATEWAY_AMOUNTS = {
    # PayPal variants
    'paypal_charge': float(os.getenv('PAYPAL_CHARGE_AMOUNT', '5.00')),
    'paypal_charge2': float(os.getenv('PAYPAL_CHARGE2_AMOUNT', '0.01')),
    'paypal_charge3': float(os.getenv('PAYPAL_CHARGE3_AMOUNT', '1.00')),
    
    # Shopify
    'shopify_nano': float(os.getenv('SHOPIFY_NANO_AMOUNT', '0.01')),
    
    # Braintree
    'braintree': float(os.getenv('BRAINTREE_AMOUNT', '1.00')),
    
    # Site-specific gateways
    'blemart': float(os.getenv('BLEMART_AMOUNT', '0.01')),
    'districtpeople': float(os.getenv('DISTRICTPEOPLE_AMOUNT', '0.99')),
    'bgddesigns': float(os.getenv('BGDDESIGNS_AMOUNT', '1.99')),
    'saintvinson_givewp': float(os.getenv('SAINTVINSON_GIVEWP_AMOUNT', '0.25')),
    'staleks_florida': float(os.getenv('STALEKS_FLORIDA_AMOUNT', '5.99')),
    'ccfoundation': float(os.getenv('CCFOUNDATION_AMOUNT', '0.00')),  # Auth - CVV validation only
    
    # Stripe variants - amounts reflect actual donation/charge amounts used
    # NOTE: Some gates have multiple functions with different amounts - values below are defaults
    'madystripe': float(os.getenv('MADYSTRIPE_AMOUNT', '1.00')),  # $1.00 donation form
    'checkout': float(os.getenv('CHECKOUT_AMOUNT', '4.00')),  # Invoice-based (variable)
    'woostripe': float(os.getenv('WOOSTRIPE_AMOUNT', '1.00')),  # Default charge mode
    'woostripe_auth': float(os.getenv('WOOSTRIPE_AUTH_AMOUNT', '0.00')),  # Auth only - $0
    'woostripe_charge': float(os.getenv('WOOSTRIPE_CHARGE_AMOUNT', '5.00')),  # Higher charge mode
    'woostripe_browser': float(os.getenv('WOOSTRIPE_BROWSER_AMOUNT', '1.00')),  # $1-$5 depending on function
    'stripe_auth': float(os.getenv('STRIPE_AUTH_AMOUNT', '0.00')),  # Auth only - $0
    'stripe_20': float(os.getenv('STRIPE_20_AMOUNT', '1.00')),  # $1.00 donation
    'stripe_js': float(os.getenv('STRIPE_JS_AMOUNT', '1.00')),  # $1.00 donation
    'stripe_payment_intent': float(os.getenv('STRIPE_PAYMENT_INTENT_AMOUNT', '1.00')),  # $1.00 donation form
    'stripe': float(os.getenv('STRIPE_AMOUNT', '1.00')),  # $1.00 donation
    'stripe_charge': float(os.getenv('STRIPE_CHARGE_AMOUNT', '1.00')),  # $1.00 donation
    'lions_club': float(os.getenv('LIONS_CLUB_AMOUNT', '5.00')),  # $5.00 donation
    'bellalliance': float(os.getenv('BELLALLIANCE_AMOUNT', '5.00')),  # $5.00 CAD charge
    'stripe_charity': float(os.getenv('STRIPE_CHARITY_AMOUNT', '1.00')),  # $1.00 donation
    'braintree_auth': float(os.getenv('BRAINTREE_AUTH_AMOUNT', '0.00')),  # Auth only - $0
    'stripe_ccn': float(os.getenv('STRIPE_CCN_AMOUNT', '20.00')),  # $20 WHMCS deposit
    'stripe_sk_1': float(os.getenv('STRIPE_SK_1_AMOUNT', '1.00')),  # $1.00 SK charge
    'stripe_sk_5': float(os.getenv('STRIPE_SK_5_AMOUNT', '5.00')),  # $5.00 SK charge
}

def get_gateway_amount(gateway_name: str, default: float = 0.01) -> float:
    """Get the test amount for a specific gateway."""
    return GATEWAY_AMOUNTS.get(gateway_name, default)

# Export proxy helper for gateway imports
__all__ = ['BOT_TOKEN', 'PROXY', 'RESIDENTIAL_PROXY', 'STRIPE_SK', 'GATEWAY_AMOUNTS', 
           'get_gateway_amount', 'get_proxy_for_gateway']

# ============================================================================
# Phase 9: Merchant Gateway URLs (Merchant Integration)
# ============================================================================
BGDDESIGNS_URL = os.getenv('BGDDESIGNS_URL', 'https://bgddesigns.com')
STALEKS_FLORIDA_URL = os.getenv('STALEKS_FLORIDA_URL', 'https://www.staleks-florida.com')
CCFOUNDATION_URL = os.getenv('CCFOUNDATION_URL', 'https://ccfoundationorg.com')
SHOPIFY_STORES = os.getenv('SHOPIFY_STORES', 'https://shopzone.nz,https://balliante.com,https://epicalarc.com').split(',')
SHOPIFY_STORES = [store.strip() for store in SHOPIFY_STORES if store.strip()]

# ============================================================================
# Stripe Configuration (Phase 9: Live Keys)
# ============================================================================
STRIPE_KEY_FILE = os.getenv('STRIPE_KEY_FILE', 'stripe_sk_live_keys.txt')
STRIPE_KEY_ATTEMPTS = int(os.getenv('STRIPE_KEY_ATTEMPTS', '3'))

# ============================================================================
# Network Configuration
# ============================================================================
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '15'))  # seconds
RETRY_ATTEMPTS = int(os.getenv('RETRY_ATTEMPTS', '3'))

# ============================================================================
# Gateway-Specific Timeout Configuration
# ============================================================================
# Per-gateway timeout overrides (in seconds)
GATEWAY_TIMEOUTS = {
    # Default timeout for all gateways not specified below
    'default': int(os.getenv('GATEWAY_TIMEOUT_DEFAULT', '22')),
    
    # Stripe variants (typically need more time)
    'stripe': int(os.getenv('GATEWAY_TIMEOUT_STRIPE', '25')),
    'stripe_auth': int(os.getenv('GATEWAY_TIMEOUT_STRIPE_AUTH', '25')),
    'stripe_20': int(os.getenv('GATEWAY_TIMEOUT_STRIPE_20', '25')),
    'stripe_js': int(os.getenv('GATEWAY_TIMEOUT_STRIPE_JS', '25')),
    'stripe_payment_intent': int(os.getenv('GATEWAY_TIMEOUT_STRIPE_PAYMENT_INTENT', '25')),
    
    # PayPal variants (GraphQL can be slow)
    'paypal': int(os.getenv('GATEWAY_TIMEOUT_PAYPAL', '30')),
    'paypal_charge': int(os.getenv('GATEWAY_TIMEOUT_PAYPAL_CHARGE', '30')),
    'check_card': int(os.getenv('GATEWAY_TIMEOUT_CHECK_CARD', '30')),
    
    # Shopify (checkout process can take time)
    'shopify': int(os.getenv('GATEWAY_TIMEOUT_SHOPIFY', '20')),
    'shopify_nano': int(os.getenv('GATEWAY_TIMEOUT_SHOPIFY_NANO', '20')),
    
    # Braintree
    'braintree': int(os.getenv('GATEWAY_TIMEOUT_BRAINTREE', '20')),
    
    # WooCommerce variants
    'woocommerce': int(os.getenv('GATEWAY_TIMEOUT_WOOCOMMERCE', '25')),
    'woostripe': int(os.getenv('GATEWAY_TIMEOUT_WOOSTRIPE', '25')),
    'woostripe_auth': int(os.getenv('GATEWAY_TIMEOUT_WOOSTRIPE_AUTH', '25')),
    'woostripe_charge': int(os.getenv('GATEWAY_TIMEOUT_WOOSTRIPE_CHARGE', '25')),
    
    # Other gateways
    'madystripe': int(os.getenv('GATEWAY_TIMEOUT_MADYSTRIPE', '25')),
    'checkout': int(os.getenv('GATEWAY_TIMEOUT_CHECKOUT', '20')),
    'ccfoundation': int(os.getenv('GATEWAY_TIMEOUT_CCFOUNDATION', '20')),
    'blemart': int(os.getenv('GATEWAY_TIMEOUT_BLEMART', '15')),
    'districtpeople': int(os.getenv('GATEWAY_TIMEOUT_DISTRICTPEOPLE', '15')),
    'bgddesigns': int(os.getenv('GATEWAY_TIMEOUT_BGDDESIGNS', '20')),
    'saintvinson_givewp': int(os.getenv('GATEWAY_TIMEOUT_SAINTVINSON_GIVEWP', '15')),
    'staleks_florida': int(os.getenv('GATEWAY_TIMEOUT_STALEKS_FLORIDA', '20')),
}

def get_gateway_timeout(gateway_name: str) -> int:
    """
    Get the timeout (in seconds) for a specific gateway.
    
    Args:
        gateway_name: Name of the gateway (e.g., 'stripe', 'paypal', 'shopify')
    
    Returns:
        Timeout in seconds, or default timeout if gateway not configured
    """
    return GATEWAY_TIMEOUTS.get(gateway_name.lower(), GATEWAY_TIMEOUTS['default'])

# ============================================================================
# AI Configuration (Blackbox)
# ============================================================================
BLACKBOX_API_KEY = os.getenv('BLACKBOX_API_KEY', '')

# ============================================================================
# Database Configuration
# ============================================================================
DATABASE_URL = os.getenv('DATABASE_URL', '')
PGHOST = os.getenv('PGHOST', '')
PGPORT = os.getenv('PGPORT', '5432')
PGUSER = os.getenv('PGUSER', '')
PGPASSWORD = os.getenv('PGPASSWORD', '')
PGDATABASE = os.getenv('PGDATABASE', '')

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/bot.log')
METRICS_FILE = os.getenv('METRICS_FILE', 'logs/metrics.json')

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(LOG_FILE) if LOG_FILE else 'logs', exist_ok=True)

# ============================================================================
# Feature Flags
# ============================================================================
ENABLE_PROXY = os.getenv('ENABLE_PROXY', 'true').lower() == 'true'
ENABLE_MASS_CHECK = os.getenv('ENABLE_MASS_CHECK', 'true').lower() == 'true'
ENABLE_SMOKE_TESTS = os.getenv('ENABLE_SMOKE_TESTS', 'true').lower() == 'true'

# ============================================================================
# Console Colors (for logging)
# ============================================================================
COLOR_RED = '\033[1;31m'
COLOR_GREEN = '\033[2;32m'
COLOR_GRAY = '\033[1;30m'
COLOR_ORANGE = '\033[38;5;208m'
COLOR_RESET = '\033[0m'

def validate_config():
    """Validate critical configuration settings."""
    errors = []
    
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN is not set")
    if not PROXY_HTTP or not PROXY_HTTPS:
        errors.append("Proxy configuration is incomplete")
    
    if errors:
        print(f"{COLOR_RED}[ERROR] Configuration validation failed:{COLOR_RESET}")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print(f"{COLOR_GREEN}[✓] Configuration validated successfully{COLOR_RESET}")
    return True

# ============================================================================
# Export all configuration as a dictionary
# ============================================================================
CONFIG = {
    'bot_token': BOT_TOKEN,
    'proxy': PROXY,
    'gateway_amounts': GATEWAY_AMOUNTS,
    'request_timeout': REQUEST_TIMEOUT,
    'retry_attempts': RETRY_ATTEMPTS,
    'log_level': LOG_LEVEL,
    'log_file': LOG_FILE,
    'metrics_file': METRICS_FILE,
    'enable_proxy': ENABLE_PROXY,
    'enable_mass_check': ENABLE_MASS_CHECK,
    'enable_smoke_tests': ENABLE_SMOKE_TESTS,
    'bgddesigns_url': BGDDESIGNS_URL,
    'staleks_florida_url': STALEKS_FLORIDA_URL,
    'ccfoundation_url': CCFOUNDATION_URL,
    'shopify_stores': SHOPIFY_STORES,
    'stripe_key_file': STRIPE_KEY_FILE,
    'stripe_key_attempts': STRIPE_KEY_ATTEMPTS,
    'database_url': DATABASE_URL,
}

if __name__ == '__main__':
    # Print configuration summary when run directly
    print("Phase 6 Bot Configuration")
    print("=" * 50)
    print(f"Bot Token: {'***' + BOT_TOKEN[-10:] if BOT_TOKEN else 'NOT SET'}")
    print(f"Proxy: {PROXY['http'][:30]}..." if PROXY['http'] else 'NOT SET')
    print(f"Request Timeout: {REQUEST_TIMEOUT}s")
    print(f"Retry Attempts: {RETRY_ATTEMPTS}")
    print(f"Log Level: {LOG_LEVEL}")
    print(f"Gateway Amounts: {GATEWAY_AMOUNTS}")
    print("=" * 50)
    validate_config()
