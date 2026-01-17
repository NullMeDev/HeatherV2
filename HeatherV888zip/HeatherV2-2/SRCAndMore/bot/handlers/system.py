"""
System Handlers Module

Contains core system commands: start, cmds, menu, proxy, setproxy, metrics.
"""

import requests
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

__all__ = [
    'create_start_handler',
    'create_cmds_handler', 
    'create_menu_handler',
    'create_proxy_handler',
    'create_setproxy_handler',
    'create_metrics_handler',
]


def create_start_handler(check_proxy_fn, get_proxy_status_fn, colors):
    """
    Factory to create start command handler.
    
    Args:
        check_proxy_fn: Function to check proxy status
        get_proxy_status_fn: Function returning proxy status dict
        colors: Dict with Z, ORANGE, RESET color codes
    """
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            check_proxy_fn()
            proxy_status = get_proxy_status_fn()
            proxy_status_text = "🟢 Alive" if proxy_status["live"] else "🔴 Dead"
            
            msg = f"""<b>Hi! My name's Mady</b>
<i>Codename: Heather | v6.3.0</i>

A <b>Multi-Auth, Multi-Charge bot</b> for card verification.

<b>Proxy:</b> {proxy_status_text}

Type <code>/cmds</code> for commands or <code>/menu</code> for dashboard!

<i>Built by @MissNullMe</i>"""
            await update.message.reply_text(msg, parse_mode='HTML')
        except telegram.error.Forbidden:
            print(f"{colors['ORANGE']}[!] Cannot send /start message - bot was blocked/kicked{colors['RESET']}")
        except Exception as e:
            print(f"{colors['Z']}[!] Error in start command: {e}{colors['RESET']}")
            raise
    
    return start_command


def create_cmds_handler(colors):
    """Factory to create cmds command handler."""
    async def cmds_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cmds command - Show full command list"""
        try:
            cmds_msg = """<b>🎯 QUICK COMMANDS:</b>
/menu - Show tab menu
/cmds - Show this list
/proxy - Proxy status
/metrics - Analytics

<b>═══════════════════════════════════</b>

<b>🔄 ALL GATES (Parallel Check):</b>
🟣 <code>/aa</code> - All Auth Gates
🟣 <code>/ac</code> - All Charge Gates

<b>💰 CHARGE GATES (Real Bank Charge):</b>
🟢 <code>/cf</code> - Stripe Corrigan $0.50
🟢 <code>/tsa</code> - Stripe Texas $0.50
🟢 <code>/sc2</code> - Stripe Charity $1.00
🟢 <code>/lc5</code> - Stripe Lions Club $5.00
🟢 <code>/pp</code> - PayPal $5.00
🟢 <code>/btc</code> - Braintree Charge
🟢 <code>/ba</code> - Bell Alliance $5 CAD

<b>🛒 SHOPIFY:</b>
🟢 <code>/sn</code> - Shopify Checkout
🟢 <code>/shop</code> - Shopify Full Flow

<b>🔐 REAL AUTH GATES ($0 Bank Verified):</b>
🟢 <code>/auth</code> - Stripe Real $0 Auth
🟢 <code>/ppauth</code> - PayPal $0 Auth
🟢 <code>/b3</code> - Braintree $0 Auth
🟢 <code>/epi</code> - Stripe Epicalarc

<b>📦 MASS (File Upload):</b>
🟢 <code>/mcf</code> - Mass Corrigan
🟢 <code>/mtsa</code> - Mass Texas
🟢 <code>/mauth</code> - Mass Stripe Auth
🟢 <code>/mppauth</code> - Mass PayPal Auth
🟢 <code>/mpp</code> - Mass PayPal Charge
🟢 <code>/mbtc</code> - Mass Braintree Charge
🟢 <code>/msn</code> - Mass Shopify

<b>🔧 TOOLS:</b>
🟢 <code>/bin</code> - BIN Lookup
🟢 <code>/vbv</code> - VBV/3DS Check
🟢 <code>/sk</code> - SK Key Validator

<b>═══════════════════════════════════</b>
<b>📝 FORMAT:</b> <code>CARD|MM|YY|CVV</code>
<b>📦 BATCH:</b> Paste up to 25 cards on new lines
🟢 = Working"""
            await update.message.reply_text(cmds_msg, parse_mode='HTML')
        except Exception as e:
            print(f"{colors['Z']}[!] Error in cmds command: {e}{colors['RESET']}")
    
    return cmds_command


def create_menu_handler(get_proxy_status_fn):
    """Factory to create menu command handler."""
    async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command - Show organized dashboard"""
        proxy_status = get_proxy_status_fn()
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
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    
    return menu_command


def create_proxy_handler(check_proxy_fn, get_proxy_fn, get_proxy_pool_fn):
    """
    Factory to create proxy command handler.
    
    Args:
        check_proxy_fn: Function to check proxy status
        get_proxy_fn: Function returning PROXY dict
        get_proxy_pool_fn: Function returning proxy_pool dict
    """
    async def proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /proxy command to check proxy status"""
        await update.message.reply_text("⏳ Checking proxy...")
        
        is_live = check_proxy_fn()
        PROXY = get_proxy_fn()
        proxy_pool = get_proxy_pool_fn()
        
        if is_live:
            try:
                response = requests.get('https://api.ipify.org?format=json', proxies=PROXY, timeout=10)
                ip = response.json().get('ip', 'Unknown')
                msg = f"🟢 <b>Proxy Status: LIVE</b>\n\n📍 IP: <code>{ip}</code>\n🌍 Location: US - Colorado - Denver"
            except (requests.RequestException, ValueError) as e:
                msg = "🟢 <b>Proxy Status: LIVE</b>"
        else:
            msg = "🔴 <b>Proxy Status: DEAD</b>\n\n⚠️ The proxy is not responding. Card checks may fail."
        
        pool_count = len(proxy_pool["proxies"])
        if pool_count > 0:
            msg += f"\n\n📦 <b>Proxy Pool:</b> {pool_count} proxies in rotation"
        
        await update.message.reply_text(msg, parse_mode='HTML')
    
    return proxy_command


def create_setproxy_handler(get_proxy_pool_fn, init_proxy_pool_fn):
    """
    Factory to create setproxy command handler.
    
    Args:
        get_proxy_pool_fn: Function returning proxy_pool dict
        init_proxy_pool_fn: Function to re-initialize proxy pool
    """
    async def setproxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /setproxy command to add a proxy to the rotation pool.
        Usage: /setproxy http://user:pass@host:port
        """
        proxy_pool = get_proxy_pool_fn()
        
        if not context.args:
            pool_proxies = proxy_pool["proxies"]
            
            msg = "<b>🔧 Proxy Pool Manager</b>\n\n"
            
            if pool_proxies:
                msg += f"<b>Current Pool ({len(pool_proxies)} proxies):</b>\n"
                for i, proxy_url in enumerate(pool_proxies, 1):
                    if '@' in proxy_url:
                        parts = proxy_url.split('@')
                        masked = f"***@{parts[-1]}"
                    else:
                        masked = proxy_url[:30] + "..." if len(proxy_url) > 30 else proxy_url
                    msg += f"  {i}. <code>{masked}</code>\n"
            else:
                msg += "<i>No proxies in pool</i>\n"
            
            msg += "\n<b>Commands:</b>\n"
            msg += "• <code>/setproxy http://user:pass@host:port</code> - Add proxy\n"
            msg += "• <code>/setproxy clear</code> - Clear all custom proxies\n"
            msg += "• <code>/setproxy test</code> - Test all proxies in pool"
            
            await update.message.reply_text(msg, parse_mode='HTML')
            return
        
        arg = context.args[0].lower()
        
        if arg == "clear":
            init_proxy_pool_fn()
            proxy_pool = get_proxy_pool_fn()
            await update.message.reply_text(
                f"✅ <b>Proxy pool reset!</b>\n\n"
                f"Pool now contains {len(proxy_pool['proxies'])} proxy(s) from environment.",
                parse_mode='HTML'
            )
            return
        
        if arg == "test":
            if not proxy_pool["proxies"]:
                await update.message.reply_text("❌ No proxies in pool to test.", parse_mode='HTML')
                return
            
            status_msg = await update.message.reply_text("⏳ Testing proxies...", parse_mode='HTML')
            results = []
            
            for proxy_url in proxy_pool["proxies"]:
                try:
                    proxy_dict = {'http': proxy_url, 'https': proxy_url}
                    response = requests.get('https://api.ipify.org?format=json', proxies=proxy_dict, timeout=10)
                    ip = response.json().get('ip', 'Unknown')
                    results.append(f"🟢 {ip}")
                except:
                    if '@' in proxy_url:
                        masked = f"***@{proxy_url.split('@')[-1]}"
                    else:
                        masked = proxy_url[:20] + "..."
                    results.append(f"🔴 {masked}")
            
            msg = "<b>🔍 Proxy Test Results</b>\n\n"
            for i, result in enumerate(results, 1):
                msg += f"{i}. {result}\n"
            
            await status_msg.edit_text(msg, parse_mode='HTML')
            return
        
        new_proxy = context.args[0]
        
        if not (new_proxy.startswith('http://') or new_proxy.startswith('https://') or new_proxy.startswith('socks')):
            await update.message.reply_text(
                "❌ Invalid proxy format!\n\n"
                "<b>Supported formats:</b>\n"
                "• <code>http://host:port</code>\n"
                "• <code>http://user:pass@host:port</code>\n"
                "• <code>socks5://host:port</code>",
                parse_mode='HTML'
            )
            return
        
        if new_proxy in proxy_pool["proxies"]:
            await update.message.reply_text("⚠️ This proxy is already in the pool.", parse_mode='HTML')
            return
        
        proxy_pool["proxies"].append(new_proxy)
        
        status_msg = await update.message.reply_text("⏳ Testing new proxy...", parse_mode='HTML')
        
        try:
            proxy_dict = {'http': new_proxy, 'https': new_proxy}
            response = requests.get('https://api.ipify.org?format=json', proxies=proxy_dict, timeout=10)
            ip = response.json().get('ip', 'Unknown')
            
            await status_msg.edit_text(
                f"✅ <b>Proxy added to pool!</b>\n\n"
                f"📍 <b>IP:</b> <code>{ip}</code>\n"
                f"📦 <b>Pool size:</b> {len(proxy_pool['proxies'])} proxies\n\n"
                f"Proxies will rotate automatically during checks.",
                parse_mode='HTML'
            )
        except Exception as e:
            await status_msg.edit_text(
                f"⚠️ <b>Proxy added but test failed!</b>\n\n"
                f"<b>Error:</b> {str(e)[:50]}\n"
                f"📦 <b>Pool size:</b> {len(proxy_pool['proxies'])} proxies\n\n"
                f"The proxy may still work for some gateways.",
                parse_mode='HTML'
            )
    
    return setproxy_command


def create_metrics_handler(get_summary_fn):
    """
    Factory to create metrics command handler.
    
    Args:
        get_summary_fn: Function returning metrics summary string
    """
    async def metrics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /metrics command to display gateway performance"""
        summary = get_summary_fn()
        await update.message.reply_text(f"<pre>{summary}</pre>", parse_mode='HTML')
    
    return metrics_command
