"""
Management Handler Module

Phase 11: Complete Gateway Handler Extraction
Handles administrative commands for card management, VBV lookup, SK validation.
"""

from telegram import Update
from telegram.ext import ContextTypes

__all__ = [
    'create_vbv_handler',
    'create_sk_handler',
    'create_cards_handler',
    'create_addcard_handler',
    'create_delcard_handler',
]


async def vbv_lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    VBV Lookup command - Check VBV/3DS status for a card.
    Usage: /vbv 4111111111111111|05|26|123
    """
    from tools.vbv_api import get_vbv_for_card
    from bot.domain.card_utils import normalize_card_input
    
    raw_text = ' '.join(context.args) if context.args else update.message.text.replace('/vbv', '').strip()
    
    if not raw_text:
        await update.message.reply_text(
            "❌ <b>VBV Lookup</b>\n\n"
            "Usage: <code>/vbv 4111111111111111|05|26|123</code>\n\n"
            "Check VBV (Verified by Visa) and 3DS status for a card.",
            parse_mode='HTML'
        )
        return
    
    cards = normalize_card_input(raw_text)
    
    if not cards:
        await update.message.reply_text("❌ No valid card found. Use format: CARD|MM|YY|CVV", parse_mode='HTML')
        return
    
    card_input = cards[0]  # Only check first card
    parts = card_input.split('|')
    card_num, card_mon, card_yer, card_cvv = parts[0], parts[1], parts[2], parts[3]
    
    processing_msg = await update.message.reply_text("🔍 Looking up VBV status...", parse_mode='HTML')
    
    vbv_info = await get_vbv_for_card(card_num, card_mon, card_yer, card_cvv)
    
    # Format response
    card_brand = vbv_info.get('card_brand', 'Unknown')
    card_type = vbv_info.get('card_type', 'Unknown')
    bank = vbv_info.get('bank', 'Unknown')
    country = vbv_info.get('country', 'Unknown')
    country_emoji = vbv_info.get('country_emoji', '')
    vbv_status = vbv_info.get('vbv_status', 'Unknown')
    
    response = (
        f"🔐 <b>VBV Lookup Result</b>\n\n"
        f"🃏 <b>Card:</b> <code>{card_num[:6]}******{card_num[-4:]}</code>\n"
        f"💳 <b>Brand:</b> {card_brand} ({card_type})\n"
        f"🏦 <b>Bank:</b> {bank}\n"
        f"{country_emoji} <b>Country:</b> {country}\n"
        f"🔒 <b>VBV Status:</b> {vbv_status}\n"
    )
    
    await processing_msg.edit_text(response, parse_mode='HTML')


async def sk_validation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    SK Validation command - Validate a Stripe secret key.
    Usage: /sk sk_live_xxxxx
    """
    from gates.sk_validator import validate_sk
    
    raw_text = ' '.join(context.args) if context.args else update.message.text.replace('/sk', '').strip()
    
    if not raw_text or not raw_text.startswith('sk_'):
        await update.message.reply_text(
            "❌ <b>SK Validation</b>\n\n"
            "Usage: <code>/sk sk_live_xxxxxxxx</code>\n\n"
            "Validate a Stripe secret key (sk_live or sk_test).",
            parse_mode='HTML'
        )
        return
    
    sk_key = raw_text.strip()
    
    processing_msg = await update.message.reply_text("🔍 Validating Stripe key...", parse_mode='HTML')
    
    result = validate_sk(sk_key)
    
    if result.get('valid'):
        response = (
            f"✅ <b>Valid Stripe Key</b>\n\n"
            f"🔑 <b>Key:</b> <code>{sk_key[:20]}...{sk_key[-8:]}</code>\n"
            f"🏢 <b>Account:</b> {result.get('account_name', 'Unknown')}\n"
            f"💰 <b>Balance:</b> {result.get('balance', 'Unknown')}\n"
            f"🌍 <b>Country:</b> {result.get('country', 'Unknown')}\n"
        )
    else:
        error_msg = result.get('error', 'Invalid key')
        response = (
            f"❌ <b>Invalid Stripe Key</b>\n\n"
            f"🔑 <b>Key:</b> <code>{sk_key[:20]}...{sk_key[-8:]}</code>\n"
            f"⚠️ <b>Error:</b> {error_msg}\n"
        )
    
    await processing_msg.edit_text(response, parse_mode='HTML')


async def list_cached_cards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    List all cached approved cards for the user.
    Usage: /cards
    """
    from tools.shopify_db import get_all_cached_cards, count_cached_cards
    
    user_id = update.effective_user.id
    cards = get_all_cached_cards(user_id)
    total_count = count_cached_cards(user_id)
    
    if not cards or total_count == 0:
        await update.message.reply_text(
            "📭 <b>No Cached Cards</b>\n\n"
            "Approved cards from gate checks will be cached here automatically.\n"
            "Use any gate command to check cards.",
            parse_mode='HTML'
        )
        return
    
    response = f"💳 <b>Cached Cards ({total_count})</b>\n\n"
    
    for idx, card_data in enumerate(cards[:20], 1):  # Show max 20
        card_input = card_data.get('card_input', 'Unknown')
        gate = card_data.get('gate_name', 'Unknown')
        bank = card_data.get('bank_name', 'Unknown')
        country = card_data.get('country', 'Unknown')
        
        # Mask card number
        parts = card_input.split('|')
        if len(parts) >= 1:
            card_num = parts[0]
            masked = f"{card_num[:6]}******{card_num[-4:]}"
            response += f"{idx}. <code>{masked}</code> - {gate} ({bank}, {country})\n"
    
    if total_count > 20:
        response += f"\n... and {total_count - 20} more\n"
    
    response += "\n💡 Use /addcard or /delcard to manage cached cards"
    
    await update.message.reply_text(response, parse_mode='HTML')


async def add_cached_card_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manually add a card to cache.
    Usage: /addcard 4111111111111111|05|26|123
    """
    from tools.shopify_db import cache_card
    from bot.domain.card_utils import normalize_card_input
    
    user_id = update.effective_user.id
    raw_text = ' '.join(context.args) if context.args else update.message.text.replace('/addcard', '').strip()
    
    if not raw_text:
        await update.message.reply_text(
            "❌ <b>Add Card to Cache</b>\n\n"
            "Usage: <code>/addcard 4111111111111111|05|26|123</code>\n\n"
            "Manually add an approved card to your cache.",
            parse_mode='HTML'
        )
        return
    
    cards = normalize_card_input(raw_text)
    
    if not cards:
        await update.message.reply_text("❌ No valid card found. Use format: CARD|MM|YY|CVV", parse_mode='HTML')
        return
    
    card_input = cards[0]
    cache_card(user_id, card_input, 'Manual', 'Unknown', 'Unknown')
    
    await update.message.reply_text(
        f"✅ <b>Card Added to Cache</b>\n\n"
        f"🃏 <code>{card_input}</code>\n\n"
        f"Use /cards to view all cached cards.",
        parse_mode='HTML'
    )


async def delete_cached_card_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Remove a card from cache.
    Usage: /delcard 4111111111111111
    """
    from tools.shopify_db import remove_cached_card
    
    user_id = update.effective_user.id
    raw_text = ' '.join(context.args) if context.args else update.message.text.replace('/delcard', '').strip()
    
    if not raw_text:
        await update.message.reply_text(
            "❌ <b>Delete Cached Card</b>\n\n"
            "Usage: <code>/delcard 4111111111111111</code>\n\n"
            "Remove a card from your cache (use first 16 digits).",
            parse_mode='HTML'
        )
        return
    
    card_prefix = raw_text.replace('|', '').replace(' ', '').strip()[:16]
    
    success = remove_cached_card(user_id, card_prefix)
    
    if success:
        await update.message.reply_text(
            f"✅ <b>Card Removed</b>\n\n"
            f"Card starting with <code>{card_prefix}</code> has been removed from cache.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"❌ <b>Card Not Found</b>\n\n"
            f"No cached card found starting with <code>{card_prefix}</code>.",
            parse_mode='HTML'
        )


# Factory functions for handler registration
def create_vbv_handler():
    """Create VBV lookup handler."""
    return vbv_lookup_command


def create_sk_handler():
    """Create SK validation handler."""
    return sk_validation_command


def create_cards_handler():
    """Create list cards handler."""
    return list_cached_cards_command


def create_addcard_handler():
    """Create add card handler."""
    return add_cached_card_command


def create_delcard_handler():
    """Create delete card handler."""
    return delete_cached_card_command
