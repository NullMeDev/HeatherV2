"""
Gateway command handlers using factory pattern.
All gateway commands follow the same pattern of extracting card input
and calling process_cards_with_gateway().

Phase 7: Handler Registry & Extraction
Phase 11.3: Standardized Gateway Handlers with Service Layer
This module provides factory functions and extracted gateway handlers
to reduce the monolithic size of transferto.py.
"""
from telegram import Update
from telegram.ext import ContextTypes
from typing import Callable, Tuple, List, Optional
from bot.services.gateway_executor import process_single_card, process_batch_cards
from bot.core.response_templates import format_batch_complete

__all__ = [
    'create_gateway_handler',
    'create_mass_handler',
    'extract_card_input',
    'GatewayConfig',
    'GATEWAY_CONFIGS',
    'create_all_gateway_handlers',
    'create_single_gateway_handler',
    'create_batch_gateway_handler',
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


def create_single_gateway_handler(
    gateway_fn: Callable,
    gateway_name: str,
    amount: float = 0.00,
    timeout: int = 25
):
    """
    Phase 11.3 Factory: Create standardized single-card gateway handler using service layer.
    
    Args:
        gateway_fn: Gateway check function (e.g., stripe_check, paypal_check)
        gateway_name: Display name for the gateway (e.g., "Stripe $0.50")
        amount: Transaction amount in USD
        timeout: Gateway timeout in seconds
        
    Returns:
        Async handler function compatible with python-telegram-bot
        
    Example:
        stripe_command = create_single_gateway_handler(
            stripe_check, "Stripe $0.50", 0.50
        )
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Extract card input from message
        raw_text = update.message.text
        
        # Remove command prefix
        command_parts = raw_text.split(None, 1)
        if len(command_parts) > 1:
            raw_text = command_parts[1].strip()
        elif context.args:
            raw_text = ' '.join(context.args)
        else:
            raw_text = ''
        
        if not raw_text:
            cmd_name = command_parts[0][1:] if command_parts else 'cmd'
            await update.message.reply_text(
                f"❌ <b>Usage:</b> <code>/{cmd_name} CARD|MM|YY|CVV</code>\n\n"
                f"<b>Examples:</b>\n"
                f"• Single: <code>/{cmd_name} 4532123456789012|12|2025|123</code>\n"
                f"• Batch (2-25): Send multiple cards separated by newlines",
                parse_mode='HTML'
            )
            return
        
        # Split into individual cards
        cards = [c.strip() for c in raw_text.split('\n') if c.strip()]
        
        # Single card
        if len(cards) == 1:
            formatted, proxy_ok = await process_single_card(
                cards[0],
                gateway_fn,
                gateway_name,
                amount,
                timeout=timeout
            )
            await update.message.reply_text(formatted, parse_mode='HTML')
        
        # Batch (2-25 cards)
        elif 2 <= len(cards) <= 25:
            stats = await process_batch_cards(
                cards,
                gateway_fn,
                gateway_name,
                amount,
                update=update
            )
            formatted = format_batch_complete(
                total=stats['approved'] + stats['declined'] + stats['cvv'] + stats['nsf'],
                approved=stats['approved'],
                declined=stats['declined'],
                cvv=stats['cvv'],
                nsf=stats['nsf'],
                three_ds=stats['three_ds'],
                gateway=gateway_name
            )
            await update.message.reply_text(formatted, parse_mode='HTML')
        
        # Too many cards
        else:
            cmd_name = command_parts[0][1:] if command_parts else 'cmd'
            await update.message.reply_text(
                f"❌ <b>Batch Limit Exceeded</b>\n\n"
                f"• Received: {len(cards)} cards\n"
                f"• Limit: 2-25 cards\n\n"
                f"<b>For larger files:</b>\n"
                f"1️⃣ Upload a .txt file\n"
                f"2️⃣ Use <code>/mass_{cmd_name}</code>",
                parse_mode='HTML'
            )
    
    return handler


def create_batch_gateway_handler(
    gateway_fn: Callable,
    gateway_name: str,
    amount: float = 0.00,
    max_batch: int = 25
):
    """
    Phase 11.3 Factory: Create batch-only gateway handler using service layer.
    
    Args:
        gateway_fn: Gateway check function
        gateway_name: Display name for the gateway
        amount: Transaction amount in USD
        max_batch: Maximum number of cards per batch
        
    Returns:
        Async handler function for batch processing
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        raw_text = update.message.text
        
        # Extract cards from message
        command_parts = raw_text.split(None, 1)
        if len(command_parts) > 1:
            raw_text = command_parts[1].strip()
        elif context.args:
            raw_text = ' '.join(context.args)
        else:
            raw_text = ''
        
        if not raw_text:
            await update.message.reply_text(
                f"❌ <b>No cards provided!</b>\n\n"
                f"Send 2-{max_batch} cards separated by newlines",
                parse_mode='HTML'
            )
            return
        
        cards = [c.strip() for c in raw_text.split('\n') if c.strip()]
        
        if len(cards) < 2:
            await update.message.reply_text(
                f"❌ Batch requires at least 2 cards\nYou sent {len(cards)} card(s)",
                parse_mode='HTML'
            )
            return
        
        if len(cards) > max_batch:
            await update.message.reply_text(
                f"❌ Too many cards!\n\nMax: {max_batch} cards\nReceived: {len(cards)} cards",
                parse_mode='HTML'
            )
            return
        
        stats = await process_batch_cards(
            cards,
            gateway_fn,
            gateway_name,
            amount,
            update=update
        )
        
        formatted = format_batch_complete(
            total=stats['approved'] + stats['declined'] + stats['cvv'] + stats['nsf'],
            approved=stats['approved'],
            declined=stats['declined'],
            cvv=stats['cvv'],
            nsf=stats['nsf'],
            three_ds=stats['three_ds'],
            gateway=gateway_name
        )
        
        await update.message.reply_text(formatted, parse_mode='HTML')
    
    return handler
