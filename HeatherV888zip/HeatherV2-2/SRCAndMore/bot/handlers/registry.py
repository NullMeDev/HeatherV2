"""
Handler Registration Module

Provides a declarative configuration system for registering all command handlers.
This module serves as the central wiring point for the entire bot.

Usage in transferto.py:
    from bot.handlers.registry import register_all_handlers
    register_all_handlers(application, handlers_dict)
"""

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from typing import Dict, Callable, List, Any, Optional

__all__ = [
    'register_all_handlers',
    'get_handler_config',
    'SYSTEM_COMMANDS',
    'GATEWAY_COMMANDS',
    'UTILITY_COMMANDS',
    'ALIAS_COMMANDS',
]

SYSTEM_COMMANDS = [
    'start', 'menu', 'cmds', 'proxy', 'setproxy', 'sp', 'metrics',
]

MULTI_GATEWAY_COMMANDS = [
    'allauth', 'aa', 'allcharge', 'ac', 'mass', 'multigate',
]

GATEWAY_COMMANDS = [
    'stripe', 'mass_stripe',
    'madystripe', 'mass_madystripe',
    'checkout',
    'amex',
    'stripe_epicalarc', 'mass_stripe_epicalarc',
    'shopify_nano', 'mass_shopify_nano',
    'braintree_api', 'mass_braintree_api',
    'stripecharge', 'mass_stripecharge',
    'braintreeauth', 'mass_braintreeauth',
    'checkoutauth',
    'stripe_charity', 'mass_stripe_charity',
    'braintree_laguna', 'mass_braintree_laguna',
    'lions_club', 'mass_lions_club',
    'pariyatti_auth', 'mass_pariyatti_auth',
    'cedine_auth', 'mass_cedine_auth',
    'stripe_multi', 'mass_stripe_multi',
    'shopify_checkout', 'mass_shopify_checkout',
    'auto_detect', 'mass_auto_detect',
]

MERCHANT_COMMANDS = [
    'blemart', 'mass_blemart',
    'districtpeople', 'mass_districtpeople',
    'bgddesigns', 'mass_bgddesigns',
    'saintvinson', 'mass_saintvinson',
    'staleks', 'mass_staleks',
    'ccfoundation', 'mass_ccfoundation',
    'bellalliance_charge',
]

AUTH_GATE_COMMANDS = [
    'foe_auth', 'mass_foe_auth',
    'charitywater_auth', 'mass_charitywater_auth',
    'donorschoose_auth', 'mass_donorschoose_auth',
    'newschools_auth', 'mass_newschools_auth',
    'ywca_auth', 'mass_ywca_auth',
    'adespresso_auth',
]

CHARGE_COMMANDS = [
    'charge1', 'mass_charge1',
    'charge2', 'mass_charge2',
    'charge3', 'mass_charge3',
    'charge4', 'mass_charge4',
    'charge5', 'mass_charge5',
]

SHOPIFY_COMMANDS = [
    'shopify_health', 'importstores', 'scanstores', 'storestats',
    'addstore', 'delstore', 'stores', 'scanstores', 'addstores',
    'liststores', 'stopstores', 'autoco', 'sho', 'shof',
]

STRIPE_SCANNER_COMMANDS = [
    'importstripe', 'scanstripe', 'stripestats',
]

UTILITY_COMMANDS = [
    'gen', 'fake', 'cg', 'bb',
    'cards', 'addcard', 'delcard',
    'vbv', 'sk',
    'categorize', 'catsites',
]

QUEUE_COMMANDS = [
    'queue', 'q', 'massall', 'ma', 'clearqueue', 'cq', 'stopall', 'sa',
]

STOP_COMMANDS = [
    'stop', 'stop1', 'stop2', 'stop3', 'stop4', 'stop5',
]

PAIRED_COMMANDS = [
    'paired_ps', 'paired_bp', 'paired_ss', 'paired_bs',
]

REAL_AUTH_COMMANDS = [
    'auth', 'mauth',
    'ppauth', 'mppauth',
]

REAL_CHARGE_COMMANDS = [
    'pp', 'mpp',
    'cf', 'mcf',
    'tsa', 'mtsa',
    'btc', 'mbtc',
]

ALIAS_COMMANDS = {
    's': 'stripe',
    'se': 'stripe_epicalarc',
    'c1': 'charge1',
    'c2': 'charge2',
    'c3': 'charge3',
    'c4': 'charge4',
    'c5': 'charge5',
    'ms': 'madystripe',
    'sc2': 'stripe_charity',
    'msc2': 'mass_stripe_charity',
    'co': 'checkout',
    'sc': 'stripecharge',
    'ba': 'bellalliance_charge',
    'b3': 'braintree_laguna',
    'mb3': 'mass_braintree_laguna',
    'lions': 'lions_club',
    'lc5': 'lions_club',
    'mlions': 'mass_lions_club',
    'paypal': 'pp',
    'sa1': 'foe_auth',
    'msa1': 'mass_foe_auth',
    'sa2': 'charitywater_auth',
    'msa2': 'mass_charitywater_auth',
    'sa3': 'donorschoose_auth',
    'msa3': 'mass_donorschoose_auth',
    'sa4': 'newschools_auth',
    'msa4': 'mass_newschools_auth',
    'sa5': 'ywca_auth',
    'msa5': 'mass_ywca_auth',
    'pa': 'pariyatti_auth',
    'mpa': 'mass_pariyatti_auth',
    'par': 'pariyatti_auth',
    'cedine': 'cedine_auth',
    'ced': 'cedine_auth',
    'mced': 'mass_cedine_auth',
    'sm': 'stripe_multi',
    'msm': 'mass_stripe_multi',
    'sn': 'shopify_checkout',
    'shop': 'shopify_checkout',
    'shopify': 'shopify_checkout',
    'msn': 'mass_shopify_checkout',
    'nano': 'shopify_nano',
    'mnano': 'mass_shopify_nano',
    'auto': 'auto_detect',
    'ad': 'auto_detect',
    'detect': 'auto_detect',
    'mauto': 'mass_auto_detect',
    'ade': 'adespresso_auth',
    'bac': 'bellalliance_charge',
    'coa': 'checkoutauth',
    'bl': 'blemart',
    'dp': 'districtpeople',
    'bg': 'bgddesigns',
    'sv': 'saintvinson',
    'sf': 'staleks',
    'cf': 'ccfoundation',
    'm': 'mass',
    'mc1': 'mass_charge1',
    'mc2': 'mass_charge2',
    'mc3': 'mass_charge3',
    'mc4': 'mass_charge4',
    'mc5': 'mass_charge5',
    'mse': 'mass_stripe_epicalarc',
    'mms': 'mass_madystripe',
    'mbl': 'mass_blemart',
    'mdp': 'mass_districtpeople',
    'mbg': 'mass_bgddesigns',
    'msv': 'mass_saintvinson',
    'msf': 'mass_staleks',
    'mcf': 'mass_ccfoundation',
    'aa': 'allauth',
    'ac': 'allcharge',
}


def get_handler_config() -> Dict[str, List[str]]:
    """
    Get the complete handler configuration.
    
    Returns:
        Dict mapping category names to lists of command names
    """
    return {
        'system': SYSTEM_COMMANDS,
        'multi_gateway': MULTI_GATEWAY_COMMANDS,
        'gateway': GATEWAY_COMMANDS,
        'merchant': MERCHANT_COMMANDS,
        'auth_gate': AUTH_GATE_COMMANDS,
        'charge': CHARGE_COMMANDS,
        'real_auth': REAL_AUTH_COMMANDS,
        'real_charge': REAL_CHARGE_COMMANDS,
        'shopify': SHOPIFY_COMMANDS,
        'stripe_scanner': STRIPE_SCANNER_COMMANDS,
        'utility': UTILITY_COMMANDS,
        'queue': QUEUE_COMMANDS,
        'stop': STOP_COMMANDS,
        'paired': PAIRED_COMMANDS,
    }


def register_commands(app: Application, handlers: Dict[str, Callable], commands: List[str]):
    """
    Register a list of commands with their handlers.
    
    Args:
        app: Telegram Application instance
        handlers: Dict mapping command names to handler functions
        commands: List of command names to register
    """
    for cmd in commands:
        handler_name = f"{cmd}_command"
        if handler_name in handlers:
            app.add_handler(CommandHandler(cmd, handlers[handler_name]))
        elif cmd in handlers:
            app.add_handler(CommandHandler(cmd, handlers[cmd]))


def register_aliases(app: Application, handlers: Dict[str, Callable], aliases: Dict[str, str]):
    """
    Register command aliases that point to existing handlers.
    
    Args:
        app: Telegram Application instance
        handlers: Dict mapping command names to handler functions
        aliases: Dict mapping alias command to target command
    """
    for alias, target in aliases.items():
        handler_name = f"{target}_command"
        if handler_name in handlers:
            app.add_handler(CommandHandler(alias, handlers[handler_name]))
        elif target in handlers:
            app.add_handler(CommandHandler(alias, handlers[target]))


def register_all_handlers(
    app: Application,
    handlers: Dict[str, Callable],
    callback_handler: Optional[Callable] = None,
    document_handler: Optional[Callable] = None,
    message_handler: Optional[Callable] = None,
    error_handler: Optional[Callable] = None,
):
    """
    Register all command handlers using the declarative configuration.
    
    This is the main entry point for handler registration.
    
    Args:
        app: Telegram Application instance
        handlers: Dict mapping command/handler names to handler functions
        callback_handler: Handler for button callbacks
        document_handler: Handler for document uploads
        message_handler: Handler for text messages
        error_handler: Handler for errors
    """
    config = get_handler_config()
    
    for category, commands in config.items():
        register_commands(app, handlers, commands)
    
    register_aliases(app, handlers, ALIAS_COMMANDS)
    
    if callback_handler:
        app.add_handler(CallbackQueryHandler(callback_handler))
    
    if document_handler:
        app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    
    if message_handler:
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    if error_handler:
        app.add_error_handler(error_handler)


def get_all_commands() -> List[str]:
    """
    Get a flat list of all registered commands (for documentation).
    
    Returns:
        List of all command names
    """
    all_cmds = []
    config = get_handler_config()
    for commands in config.values():
        all_cmds.extend(commands)
    all_cmds.extend(ALIAS_COMMANDS.keys())
    return sorted(set(all_cmds))
