"""
Gateway command handlers using factory pattern.
All gateway commands follow the same pattern of extracting card input
and calling process_cards_with_gateway().

Phase 7: Handler Registry & Extraction
This module provides factory functions and extracted gateway handlers
to reduce the monolithic size of transferto.py.
"""
from telegram import Update
from telegram.ext import ContextTypes
from typing import Callable, Tuple, List, Optional

__all__ = [
    'create_gateway_handler',
    'create_mass_handler',
    'extract_card_input',
    'GatewayConfig',
    'GATEWAY_CONFIGS',
    'create_all_gateway_handlers',
]


class GatewayConfig:
    """Configuration for a gateway handler."""
    
    def __init__(
        self,
        name: str,
        gateway_type: str,
        command: str,
        prefixes: List[str],
        mass_command: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        description: str = ""
    ):
        self.name = name
        self.gateway_type = gateway_type
        self.command = command
        self.prefixes = prefixes
        self.mass_command = mass_command or f"mass_{command}"
        self.aliases = aliases or []
        self.description = description


GATEWAY_CONFIGS = {
    'stripe_charity': GatewayConfig(
        name="Stripe Charity",
        gateway_type="stripe",
        command="stripe_charity",
        prefixes=['/sc2 ', '/stripe_charity '],
        aliases=['sc2'],
        description="$1 Stripe donation charge"
    ),
    'braintree_laguna': GatewayConfig(
        name="Braintree Laguna",
        gateway_type="braintree",
        command="braintree_laguna",
        prefixes=['/b3 ', '/braintree_laguna '],
        aliases=['b3'],
        description="$0 Braintree add payment method"
    ),
    'stripe_auth': GatewayConfig(
        name="Stripe Auth",
        gateway_type="stripe",
        command="auth",
        prefixes=['/auth '],
        aliases=[],
        description="$0 Stripe SetupIntent auth"
    ),
    'paypal_charge': GatewayConfig(
        name="PayPal Charge",
        gateway_type="paypal",
        command="pp",
        prefixes=['/pp ', '/paypal '],
        mass_command="mpp",
        aliases=['paypal'],
        description="$5 PayPal GraphQL charge"
    ),
    'paypal_auth': GatewayConfig(
        name="PayPal Auth",
        gateway_type="paypal",
        command="ppauth",
        prefixes=['/ppauth '],
        mass_command="mppauth",
        aliases=[],
        description="$0 PayPal auth"
    ),
    'corrigan_charge': GatewayConfig(
        name="Corrigan Funerals",
        gateway_type="stripe",
        command="cf",
        prefixes=['/cf '],
        mass_command="mcf",
        aliases=[],
        description="$0.50 WP Full Stripe donation"
    ),
    'texas_charge': GatewayConfig(
        name="Texas Southern",
        gateway_type="stripe",
        command="tsa",
        prefixes=['/tsa '],
        mass_command="mtsa",
        aliases=[],
        description="$0.50 WP Full Stripe donation"
    ),
    'lions_club': GatewayConfig(
        name="Lions Club",
        gateway_type="stripe",
        command="lions_club",
        prefixes=['/lions ', '/lc5 ', '/lions_club '],
        mass_command="mlions",
        aliases=['lions', 'lc5'],
        description="$5 Lions Club charge"
    ),
    'braintree_charge': GatewayConfig(
        name="Braintree Charge",
        gateway_type="braintree",
        command="btc",
        prefixes=['/btc '],
        mass_command="mbtc",
        aliases=[],
        description="Braintree full charge"
    ),
    'shopify_checkout': GatewayConfig(
        name="Shopify Checkout",
        gateway_type="shopify",
        command="sn",
        prefixes=['/sn ', '/shop ', '/shopify '],
        mass_command="msn",
        aliases=['shop', 'shopify'],
        description="Full Shopify checkout flow"
    ),
    'bellalliance_charge': GatewayConfig(
        name="Bell Alliance",
        gateway_type="stripe",
        command="ba",
        prefixes=['/ba '],
        aliases=[],
        description="$5 CAD Bell Alliance charge"
    ),
}


def extract_card_input(update: Update, context: ContextTypes.DEFAULT_TYPE, prefixes: List[str]) -> str:
    """
    Extract card input from message text.
    Handles command prefixes, multiline input, and edited messages.
    
    Args:
        update: Telegram update object
        context: Command context
        prefixes: List of command prefixes to strip (e.g., ['/c1 ', '/charge1 '])
    
    Returns:
        Raw card input text
    """
    message = update.message or update.edited_message
    if not message or not message.text:
        return ''
    
    raw_text = message.text
    
    for prefix in prefixes:
        if raw_text.lower().startswith(prefix):
            return raw_text[len(prefix):].strip()
    
    if '\n' in raw_text:
        return raw_text.split('\n', 1)[1].strip()
    elif context.args:
        return ' '.join(context.args)
    
    return ''


def create_gateway_handler(
    gateway_fn: Callable,
    gateway_name: str,
    gateway_type: str,
    prefixes: List[str],
    process_cards_fn: Callable
):
    """
    Factory function to create gateway command handlers.
    
    Args:
        gateway_fn: The gateway check function
        gateway_name: Display name for the gateway
        gateway_type: Gateway type (stripe, paypal, braintree, etc.)
        prefixes: Command prefixes to strip
        process_cards_fn: The process_cards_with_gateway function
    
    Returns:
        Async handler function
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        raw_text = extract_card_input(update, context, prefixes)
        await process_cards_fn(update, raw_text, gateway_fn, gateway_name, gateway_type)
    
    return handler


def create_mass_handler(
    gateway_fn: Callable,
    gateway_name: str,
    mass_with_gateway_fn: Callable
):
    """
    Factory function to create mass check command handlers.
    
    Args:
        gateway_fn: The gateway check function (possibly with proxy argument handling)
        gateway_name: Display name for the gateway
        mass_with_gateway_fn: The mass_with_gateway function
    
    Returns:
        Async handler function
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await mass_with_gateway_fn(update, context, gateway_fn=gateway_fn, gateway_name=gateway_name)
    
    return handler


def create_all_gateway_handlers(
    gateway_functions: dict,
    process_cards_fn: Callable,
    mass_with_gateway_fn: Callable
) -> dict:
    """
    Create all gateway handlers from configuration.
    
    Args:
        gateway_functions: Dict mapping gateway key to (check_fn, name, type)
        process_cards_fn: The process_cards_with_gateway function
        mass_with_gateway_fn: The mass_with_gateway function
    
    Returns:
        Dict mapping command names to handler functions
    """
    handlers = {}
    
    for key, config in GATEWAY_CONFIGS.items():
        if key not in gateway_functions:
            continue
        
        check_fn = gateway_functions[key]
        
        handler = create_gateway_handler(
            check_fn,
            config.name,
            config.gateway_type,
            config.prefixes,
            process_cards_fn
        )
        handlers[f"{config.command}_command"] = handler
        
        mass_handler = create_mass_handler(
            check_fn,
            config.name,
            mass_with_gateway_fn
        )
        handlers[f"{config.mass_command}_command"] = mass_handler
    
    return handlers
