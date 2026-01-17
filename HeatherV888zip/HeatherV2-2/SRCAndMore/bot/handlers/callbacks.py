"""
Callback query handlers for menu buttons and batch control.
"""
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Callable, Dict, Any

from ..core.keyboards import (
    create_main_menu, create_single_gates_menu, create_batch_menu,
    create_tools_menu, create_ai_menu, create_settings_menu,
    create_back_button, create_paired_menu, create_help_menu
)
from tools.card_generator import generate_cards, lookup_bin, format_gen_response

__all__ = ['create_button_callback_handler']


def create_button_callback_handler(
    batch_sessions: Dict[str, Dict[str, Any]],
    gateway_amounts: Dict[str, float],
    get_proxy_status: Callable[[], Dict[str, Any]],
    check_proxy_func: Callable[[], bool],
    get_metrics_summary: Callable[[], str]
) -> Callable:
    """
    Factory to create the button callback handler with injected dependencies.
    
    Args:
        batch_sessions: Dictionary tracking batch check sessions
        gateway_amounts: Gateway charge amounts
        get_proxy_status: Function that returns proxy status dict
        check_proxy_func: Function to check if proxy is alive
        get_metrics_summary: Function to get metrics summary
    
    Returns:
        Async callback handler function
    """
    async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle menu button clicks and card copy actions"""
        query = update.callback_query
        await query.answer()
        
        category = query.data
        proxy_status = get_proxy_status()
        
        if category.startswith("copy_"):
            card_input = category.replace("copy_", "")
            await query.answer(f"Card copied: {card_input}", show_alert=True)
            return
        
        if category.startswith("batch_stop_"):
            session_id = category.replace("batch_stop_", "")
            if session_id in batch_sessions:
                batch_sessions[session_id]["stopped"] = True
                batch_sessions[session_id]["paused"] = False
                await query.answer("Stopping batch check...", show_alert=True)
            return
        
        if category.startswith("batch_pause_"):
            session_id = category.replace("batch_pause_", "")
            if session_id in batch_sessions:
                batch_sessions[session_id]["paused"] = True
                await query.answer("Paused. Click Resume to continue.", show_alert=True)
            return
        
        if category.startswith("batch_resume_"):
            session_id = category.replace("batch_resume_", "")
            if session_id in batch_sessions:
                batch_sessions[session_id]["paused"] = False
                await query.answer("Resumed!", show_alert=True)
            return
        
        if category.startswith("regen_"):
            bin_input = category.replace("regen_", "")
            await query.answer("Regenerating 25 cards...")
            
            parts = bin_input.split('|')
            bin_pattern = parts[0].replace("-", "").replace(" ", "").ljust(16, 'x')
            mes = parts[1] if len(parts) > 1 else None
            ano = parts[2] if len(parts) > 2 else None
            cvv = parts[3] if len(parts) > 3 else None
            
            bin_info = await asyncio.to_thread(lookup_bin, bin_pattern[:6])
            brand = bin_info['brand'] if bin_info else ""
            
            cards = generate_cards(bin_pattern, mes, ano, cvv, 25, brand)
            response = format_gen_response(cards, bin_info, bin_pattern, 25)
            
            regen_data = bin_input
            if len(regen_data) > 58:
                regen_data = regen_data[:58]
            regen_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Regen 25", callback_data=f"regen_{regen_data}")]
            ])
            
            await query.edit_message_text(response, parse_mode='HTML', reply_markup=regen_button)
            return
        
        if category == "cat_single":
            msg = """<b>💳 SINGLE CARD CHECK</b>

Select gateway category:"""
            reply_markup = create_single_gates_menu()
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "single_auth":
            msg = """<b>🔐 REAL AUTH GATES ($0 Bank Verified)</b>

<code>/auth</code> - Stripe Real $0 Auth
└─ <code>/auth CARD|MM|YY|CVV</code>

<code>/ppauth</code> - PayPal $0 Auth
└─ <code>/ppauth CARD|MM|YY|CVV</code>

<code>/b3</code> - Braintree $0 Auth
└─ <code>/b3 CARD|MM|YY|CVV</code>

<code>/epi</code> - Stripe Epicalarc
└─ <code>/epi CARD|MM|YY|CVV</code>

<code>/sn</code> - Shopify Checkout
└─ <code>/sn CARD|MM|YY|CVV</code>"""
            reply_markup = create_back_button("cat_single")
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "all_auth":
            msg = """<b>🔄 ALL AUTH GATES ($0 Bank Verified)</b>

Check one card against ALL auth gateways simultaneously:

<code>/allauth CARD|MM|YY|CVV</code>
or
<code>/aa CARD|MM|YY|CVV</code>

<b>Gates:</b> Stripe Auth, PayPal Auth, Braintree Auth, Shopify, Epicalarc

Runs all gates in parallel and shows which approve/decline."""
            reply_markup = create_back_button("cat_single")
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "all_charge":
            msg = """<b>🔄 ALL CHARGE GATES (Real Bank Charge)</b>

Check one card against ALL charge gateways simultaneously:

<code>/allcharge CARD|MM|YY|CVV</code>
or
<code>/ac CARD|MM|YY|CVV</code>

<b>Gates:</b> Corrigan, Texas, Charity, Lions, PayPal $5, Braintree, Bell Alliance

Runs all gates in parallel and shows which approve/decline."""
            reply_markup = create_back_button("cat_single")
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "single_charge":
            msg = """<b>💰 CHARGE GATES (Real Bank Charge)</b>

<code>/cf</code> - Stripe Corrigan $0.50
└─ <code>/cf CARD|MM|YY|CVV</code>

<code>/tsa</code> - Stripe Texas $0.50
└─ <code>/tsa CARD|MM|YY|CVV</code>

<code>/sc2</code> - Stripe Charity $1.00
└─ <code>/sc2 CARD|MM|YY|CVV</code>

<code>/lc5</code> - Stripe Lions Club $5.00
└─ <code>/lc5 CARD|MM|YY|CVV</code>

<code>/pp</code> - PayPal $5.00
└─ <code>/pp CARD|MM|YY|CVV</code>

<code>/btc</code> - Braintree Charge
└─ <code>/btc CARD|MM|YY|CVV</code>

<code>/ba</code> - Bell Alliance $5 CAD
└─ <code>/ba CARD|MM|YY|CVV</code>"""
            reply_markup = create_back_button("cat_single")
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "cat_batch":
            msg = """<b>📦 BATCH CHECK</b>

1️⃣ Upload a .txt file (one card per line)
2️⃣ Select a gateway below
3️⃣ Reply to file with chosen command

Select gateway category:"""
            reply_markup = create_batch_menu()
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "batch_auth":
            msg = """<b>🔐 AUTH BATCH ($0 Bank Verified)</b>

<code>/mauth</code> - Mass Stripe $0 Auth
└─ Reply to file with <code>/mauth</code>

<code>/mppauth</code> - Mass PayPal $0 Auth
└─ Reply to file with <code>/mppauth</code>

<code>/msn</code> - Mass Shopify Checkout
└─ Reply to file with <code>/msn</code>"""
            reply_markup = create_back_button("cat_batch")
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "batch_charge":
            msg = """<b>💰 CHARGE BATCH (Real Bank Charge)</b>

<code>/mcf</code> - Stripe Corrigan $0.50
└─ Reply to file with <code>/mcf</code>

<code>/mtsa</code> - Stripe Texas $0.50
└─ Reply to file with <code>/mtsa</code>

<code>/mlions</code> - Stripe Lions Club $5.00
└─ Reply to file with <code>/mlions</code>

<code>/mpp</code> - PayPal $5.00
└─ Reply to file with <code>/mpp</code>

<code>/mbtc</code> - Braintree Charge
└─ Reply to file with <code>/mbtc</code>"""
            reply_markup = create_back_button("cat_batch")
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "cat_paired":
            paypal_amt = gateway_amounts.get('paypal_charge', 5.00)
            shopify_amt = gateway_amounts.get('shopify_nano', 0.00)
            
            msg = f"""<b>🔗 PAIRED CHECK (Working)</b>

Check one file against two gateways simultaneously!

<b>✅ Shopify + PayPal</b> <code>/paired_sp</code>
├─ Shopify Auth: ${shopify_amt:.2f} (no proxy)
├─ PayPal Charge: ${paypal_amt:.2f} (with proxy)
├─ Combined: Auth + Charge verification
└─ Command: <code>/paired_sp</code> → upload file

<b>═══════════════════════════════════</b>
<i>Other paired combinations are unavailable
because Stripe/Braintree gates are blocked.</i>

<i>💡 Tip: Both gateways run concurrently for faster results</i>"""
            reply_markup = create_paired_menu()
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "cat_tools":
            msg = """<b>🔧 TOOLS</b>

<b>LOOKUPS</b>
<code>/bin</code> - BIN Lookup
<code>/vbv</code> - 3DS/VBV Lookup
<code>/sk</code> - SK Key Validator

<b>SHOPIFY STORES</b>
<code>/addstores</code> - Bulk add (file/list)
<code>/stores</code> - List cached stores
<code>/scanstores</code> - Scan ALL pending

<b>AUTO CHECKOUT</b>
<code>/autoco</code> - Try cached cards on store
<code>/cards</code> - List cached cards"""
            reply_markup = create_tools_menu()
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "cat_settings":
            proxy_emoji = "🟢" if proxy_status["live"] else "🔴"
            keyboard = [
                [InlineKeyboardButton("📡 Check Proxy", callback_data="set_proxy"),
                 InlineKeyboardButton("📊 View Metrics", callback_data="set_metrics")],
                [InlineKeyboardButton("🔙 BACK", callback_data="back_main")],
            ]
            msg = f"""<b>⚙️ SETTINGS</b>

<b>System Status:</b>
└─ Proxy: {proxy_emoji} {'ALIVE' if proxy_status["live"] else 'DEAD'}

Select an option:"""
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "cat_metrics":
            summary = get_metrics_summary()
            keyboard = [
                [InlineKeyboardButton("🔙 BACK", callback_data="back_main")],
            ]
            msg = f"""<b>📊 METRICS</b>

<pre>{summary}</pre>"""
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "cat_ai":
            msg = """<b>🤖 AI ASSISTANTS</b>

<b>Blackbox AI</b>
<code>/bb</code> - Ask Blackbox AI anything
└─ <code>/bb How do I fix this error?</code>
└─ <code>/bb Write a Python script for...</code>

<b>ChatGPT</b>
<code>/cg</code> - Ask ChatGPT anything
└─ <code>/cg What is the capital of France?</code>
└─ <code>/cg Explain how Stripe payments work</code>

<b>Usage:</b>
Just type the command followed by your question!"""
            reply_markup = create_ai_menu()
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "cat_help":
            msg = """<b>❓ QUICK HELP</b>

<b>Single Card Format:</b>
<code>/command CARD|MM|YY|CVV</code>

<b>Examples:</b>
<code>/sa 4111111111111111|12|25|123</code>
<code>/c1 4222222222222222|06|26|456</code>

<b>Mass Check:</b>
1️⃣ Upload .txt file
2️⃣ Reply with command
3️⃣ View results

<b>Card Status:</b>
✅ APPROVED - Gate accepted
❌ DECLINED - Card rejected
🟢 Proxy ALIVE
🔴 Proxy DEAD"""
            reply_markup = create_help_menu()
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "set_proxy":
            is_live = check_proxy_func()
            proxy_emoji = "🟢" if is_live else "🔴"
            keyboard = [
                [InlineKeyboardButton("🔙 BACK", callback_data="cat_settings")],
            ]
            msg = f"""<b>📡 PROXY STATUS</b>

Status: {proxy_emoji} {'ALIVE' if is_live else 'DEAD'}

Checking... Please wait."""
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "set_metrics":
            summary = get_metrics_summary()
            keyboard = [
                [InlineKeyboardButton("🔙 BACK", callback_data="cat_settings")],
            ]
            msg = f"""<b>📊 GATEWAY METRICS</b>

<pre>{summary}</pre>"""
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        
        elif category == "back_main":
            proxy_status_emoji = "🟢" if proxy_status["live"] else "🔴"
            msg = f"""<b>═══════════════════════════════════</b>
<b>          MADY v6.3.0 DASHBOARD</b>
<b>       Codename: Heather</b>
<b>═══════════════════════════════════</b>

<b>📊 System Status</b>
└─ Proxy: {proxy_status_emoji} {'ALIVE' if proxy_status["live"] else 'DEAD'}

<b>Select a category below:</b>
"""
            keyboard = [
                [
                    InlineKeyboardButton("💳 SINGLE", callback_data="cat_single"),
                    InlineKeyboardButton("📦 BATCH", callback_data="cat_batch"),
                ],
                [
                    InlineKeyboardButton("🔧 TOOLS", callback_data="cat_tools"),
                    InlineKeyboardButton("🔗 PAIRED", callback_data="cat_paired"),
                ],
                [
                    InlineKeyboardButton("🤖 AI", callback_data="cat_ai"),
                    InlineKeyboardButton("⚙️ SETTINGS", callback_data="cat_settings"),
                ],
                [
                    InlineKeyboardButton("❓ HELP", callback_data="cat_help"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    
    return button_callback
