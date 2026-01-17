"""
Utility Handlers Module

Contains utility commands: gen, fake, chatgpt, blackbox.
"""

import os
import asyncio
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from tools.card_generator import generate_cards, lookup_bin, format_gen_response
from tools.fake_identity import generate_fake_identity, format_fake_response
from tools.bin_extrapolator import (
    start_session, stop_session, get_session, resume_session,
    has_saved_session, extrapolate_bin_v2, export_results_to_file,
    format_extrap_progress_v2, format_extrap_results_v2, get_available_gates
)
from gates.stripe_auth_real import stripe_real_auth_check

__all__ = [
    'create_gen_handler',
    'create_fake_handler',
    'create_chatgpt_handler',
    'create_blackbox_handler',
    'create_extrap_handler',
    'create_stopextrap_handler',
]


def create_gen_handler():
    """Factory to create gen command handler."""
    async def gen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /gen command - Generate Luhn-valid cards from BIN"""
        if not context.args:
            await update.message.reply_text(
                "<b>Card Generator</b>\n\n"
                "Usage: <code>/gen BIN [amount]</code>\n\n"
                "Examples:\n"
                "<code>/gen 414720</code> - Generate 25 cards\n"
                "<code>/gen 414720xxxxxxxxxx 50</code> - Generate 50 cards\n"
                "<code>/gen 414720|12|xx|xxx 10</code> - With month fixed",
                parse_mode='HTML'
            )
            return
        
        bin_input = context.args[0]
        amount = 25
        if len(context.args) > 1 and context.args[1].isdigit():
            amount = min(int(context.args[1]), 100)
        
        parts = bin_input.split('|')
        bin_pattern = parts[0].replace("-", "").replace(" ", "").ljust(16, 'x')
        mes = parts[1] if len(parts) > 1 else None
        ano = parts[2] if len(parts) > 2 else None
        cvv = parts[3] if len(parts) > 3 else None
        
        processing = await update.message.reply_text("Generating cards...")
        
        bin_info = await asyncio.to_thread(lookup_bin, bin_pattern[:6])
        brand = bin_info['brand'] if bin_info else ""
        
        cards = generate_cards(bin_pattern, mes, ano, cvv, amount, brand)
        
        regen_data = bin_input
        if len(regen_data) > 58:
            regen_data = regen_data[:58]
        regen_button = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Regen 25", callback_data=f"regen_{regen_data}")]
        ])
        
        if amount > 25:
            cards_text = '\n'.join(cards)
            filename = f"/tmp/gen_{update.message.from_user.id}_{amount}.txt"
            with open(filename, 'w') as f:
                f.write(cards_text)
            
            await processing.delete()
            await update.message.reply_document(
                document=open(filename, 'rb'),
                filename=f"{bin_pattern[:6]}_{amount}_cards.txt",
                caption=format_gen_response(cards, bin_info, bin_pattern, amount),
                parse_mode='HTML',
                reply_markup=regen_button
            )
            os.remove(filename)
        else:
            response = format_gen_response(cards, bin_info, bin_pattern, amount)
            await processing.edit_text(response, parse_mode='HTML', reply_markup=regen_button)
    
    return gen_command


def create_fake_handler():
    """Factory to create fake command handler."""
    async def fake_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /fake command - Generate fake identity"""
        country_code = context.args[0].lower() if context.args else "us"
        
        processing = await update.message.reply_text("Generating fake identity...")
        
        identity = await asyncio.to_thread(generate_fake_identity, country_code)
        response = format_fake_response(identity, country_code)
        
        await processing.edit_text(response, parse_mode='HTML')
    
    return fake_command


def create_chatgpt_handler():
    """Factory to create chatgpt command handler."""
    async def chatgpt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cg command - Chat with ChatGPT"""
        if not context.args:
            await update.message.reply_text(
                "<b>ChatGPT</b>\n\n"
                "Usage: <code>/cg your question here</code>\n\n"
                "Example: <code>/cg What is the capital of France?</code>",
                parse_mode='HTML'
            )
            return
        
        prompt = ' '.join(context.args)
        processing = await update.message.reply_text("Thinking...")
        
        try:
            import urllib.parse
            encoded_prompt = urllib.parse.quote(prompt)
            api_url = f"https://api-chatgpt4.eternalowner06.workers.dev/?prompt={encoded_prompt}"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(api_url)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            answer = data.get('response', data.get('answer', data.get('message', str(data))))
                        else:
                            answer = str(data)
                    except:
                        answer = response.text
                    
                    if len(answer) > 4000:
                        answer = answer[:4000] + "..."
                    
                    await processing.edit_text(
                        f"<b>ChatGPT</b>\n\n"
                        f"<b>Q:</b> <i>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</i>\n\n"
                        f"<b>A:</b> {answer}",
                        parse_mode='HTML'
                    )
                else:
                    await processing.edit_text(
                        f"API Error: {response.status_code}\n\nTry again later.",
                        parse_mode='HTML'
                    )
        except httpx.TimeoutException:
            await processing.edit_text("Request timed out. Please try again.", parse_mode='HTML')
        except Exception as e:
            await processing.edit_text(f"Error: {str(e)[:200]}", parse_mode='HTML')
    
    return chatgpt_command


def create_blackbox_handler():
    """Factory to create blackbox command handler."""
    async def blackbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /bb command - Chat with Blackbox AI"""
        if not context.args:
            await update.message.reply_text(
                "<b>Blackbox AI</b>\n\n"
                "Usage: <code>/bb your question here</code>\n\n"
                "Example: <code>/bb How do I fix this Python error?</code>",
                parse_mode='HTML'
            )
            return
        
        prompt = ' '.join(context.args)
        processing = await update.message.reply_text("Thinking...")
        
        try:
            blackbox_api_key = os.environ.get('BLACKBOX_API_KEY', '')
            if not blackbox_api_key:
                await processing.edit_text("Blackbox API key not configured.", parse_mode='HTML')
                return
            
            headers = {
                'Authorization': f'Bearer {blackbox_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'messages': [{'role': 'user', 'content': prompt}],
                'model': 'blackboxai/openai/gpt-4',
                'temperature': 0.7,
                'max_tokens': 2048,
                'stream': False
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    'https://api.blackbox.ai/chat/completions',
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            choices = data.get('choices', [])
                            if choices:
                                answer = choices[0].get('message', {}).get('content', str(data))
                            else:
                                answer = data.get('response', str(data))
                        else:
                            answer = str(data)
                    except:
                        answer = response.text
                    
                    if len(answer) > 4000:
                        answer = answer[:4000] + "..."
                    
                    await processing.edit_text(
                        f"<b>Blackbox AI</b>\n\n"
                        f"<b>Q:</b> <i>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</i>\n\n"
                        f"<b>A:</b> {answer}",
                        parse_mode='HTML'
                    )
                else:
                    await processing.edit_text(
                        f"API Error: {response.status_code}\n\nTry again later.",
                        parse_mode='HTML'
                    )
        except httpx.TimeoutException:
            await processing.edit_text("Request timed out. Please try again.", parse_mode='HTML')
        except Exception as e:
            await processing.edit_text(f"Error: {str(e)[:200]}", parse_mode='HTML')
    
    return blackbox_command


def create_extrap_handler(get_proxy=None, gate_functions=None):
    """Factory to create extrap command handler with multi-gate support."""
    
    gates = {
        'stripe': stripe_real_auth_check,
    }
    if gate_functions:
        gates.update(gate_functions)
    
    async def extrap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /extrap command - Advanced BIN Extrapolation v2.0
        
        Usage: /extrap BIN [depth] [cards] [gate]
        - BIN: Base BIN to extrapolate (6+ digits)
        - depth: How many levels deep to drill (default 4, max 10)
        - cards: Cards per pattern to test (default 10, max 100)
        - gate: Gate to use (stripe, paypal, braintree)
        
        Features:
        - Parallel testing (5x faster)
        - Configurable depth and cards per pattern
        - Multi-gate support
        - Auto-generates cards from hit patterns
        - Exports results to file
        - Resume capability for interrupted runs
        """
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        
        if not context.args:
            has_resume = has_saved_session(user_id)
            resume_text = "\n<b>Resume:</b> <code>/extrap resume</code> - Continue last run\n" if has_resume else ""
            
            await update.message.reply_text(
                "<b>🔍 BIN EXTRAPOLATOR v2.0</b>\n\n"
                "Systematically discover active card patterns within a BIN.\n\n"
                "<b>Usage:</b>\n"
                "<code>/extrap BIN [depth] [cards] [gate]</code>\n\n"
                "<b>Parameters:</b>\n"
                "• <b>BIN</b> - Base BIN (6+ digits)\n"
                "• <b>depth</b> - Levels to drill (1-10, default 4)\n"
                "• <b>cards</b> - Cards per pattern (1-100, default 10)\n"
                "• <b>gate</b> - Gate: stripe, paypal, braintree\n\n"
                "<b>Examples:</b>\n"
                "<code>/extrap 414720</code> - Default settings\n"
                "<code>/extrap 414720 6 25</code> - 6 deep, 25 cards each\n"
                "<code>/extrap 414720 4 50 paypal</code> - Use PayPal gate\n"
                f"{resume_text}\n"
                "<b>Features:</b>\n"
                "✅ Parallel testing (5x faster)\n"
                "✅ Auto-generates cards from hits\n"
                "✅ Exports results to file\n"
                "✅ Resume interrupted runs\n\n"
                "<i>Stop with /stopextrap</i>",
                parse_mode='HTML'
            )
            return
        
        if context.args[0].lower() == 'resume':
            session = resume_session(user_id)
            if not session:
                await update.message.reply_text("❌ No saved session to resume.")
                return
            base_bin = session.base_bin
            await update.message.reply_text(
                f"✅ Resuming extrapolation for <code>{base_bin}</code>\n"
                f"Progress: {session.total_tested} tested, {session.total_hits} hits",
                parse_mode='HTML'
            )
        else:
            existing = get_session(user_id)
            if existing and existing.is_running:
                await update.message.reply_text(
                    "⚠️ You already have an extrapolation running!\n"
                    "Use /stopextrap to cancel it first.",
                    parse_mode='HTML'
                )
                return
            
            base_bin = context.args[0].replace("-", "").replace(" ", "")
            if not base_bin.isdigit() or len(base_bin) < 6:
                await update.message.reply_text("❌ Invalid BIN. Must be at least 6 digits.")
                return
            
            max_depth = 4
            cards_per_pattern = 10
            gate = 'stripe'
            
            if len(context.args) > 1 and context.args[1].isdigit():
                max_depth = min(int(context.args[1]), 10)
            
            if len(context.args) > 2 and context.args[2].isdigit():
                cards_per_pattern = min(int(context.args[2]), 100)
            
            if len(context.args) > 3:
                gate = context.args[3].lower()
                if gate not in gates:
                    await update.message.reply_text(
                        f"❌ Unknown gate: {gate}\n"
                        f"Available: {', '.join(gates.keys())}",
                        parse_mode='HTML'
                    )
                    return
            
            estimated_cards = 10 * cards_per_pattern * max_depth
            estimated_time = estimated_cards // 10
            
            session = start_session(
                user_id, chat_id, base_bin,
                max_depth=max_depth,
                cards_per_pattern=cards_per_pattern,
                concurrency=5,
                gate=gate
            )
        
        check_func = gates.get(session.config.gate, stripe_real_auth_check)
        
        estimated_cards = 10 * session.config.cards_per_pattern * session.config.max_depth
        estimated_time = max(estimated_cards // 10, 1)
        
        status_msg = await update.message.reply_text(
            f"<b>🔍 BIN EXTRAPOLATION STARTING</b>\n\n"
            f"<b>Base BIN:</b> <code>{session.base_bin}</code>\n"
            f"<b>Depth:</b> {session.config.max_depth} levels\n"
            f"<b>Cards/pattern:</b> {session.config.cards_per_pattern}\n"
            f"<b>Gate:</b> {session.config.gate}\n"
            f"<b>Concurrency:</b> {session.config.concurrency}x parallel\n\n"
            f"⏳ Estimated: ~{estimated_cards} cards, ~{estimated_time}s\n\n"
            f"Testing patterns...",
            parse_mode='HTML'
        )
        
        proxy = None
        if get_proxy:
            try:
                proxy = get_proxy()
            except:
                pass
        
        async def progress_callback(message: str):
            try:
                formatted = format_extrap_progress_v2(session, message)
                await status_msg.edit_text(formatted, parse_mode='HTML')
            except Exception:
                pass
        
        try:
            await extrapolate_bin_v2(
                session,
                check_func,
                progress_callback,
                proxy
            )
            
            result_file = export_results_to_file(session)
            final_result = format_extrap_results_v2(session)
            
            buttons = [[InlineKeyboardButton("🔄 Run Again", callback_data=f"extrap_{session.base_bin}")]]
            
            await status_msg.edit_text(final_result, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))
            
            if result_file and session.total_hits > 0:
                await update.message.reply_document(
                    document=open(result_file, 'rb'),
                    filename=f"extrap_{session.base_bin}_results.txt",
                    caption=f"📁 Full results: {session.total_hits} hits from {session.total_tested} cards"
                )
                os.remove(result_file)
            
        except Exception as e:
            await status_msg.edit_text(
                f"❌ Extrapolation error: {str(e)[:100]}",
                parse_mode='HTML'
            )
        
        session.clear_saved_state()
        stop_session(user_id)
    
    return extrap_command


def create_stopextrap_handler():
    """Factory to create stopextrap command handler."""
    async def stopextrap_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stopextrap command - Stop extrapolation and save progress"""
        user_id = update.message.from_user.id
        
        session = get_session(user_id)
        if session:
            session.save_state()
            stop_session(user_id)
            await update.message.reply_text(
                "✅ Extrapolation stopped.\n"
                f"Progress saved: {session.total_tested} tested, {session.total_hits} hits\n\n"
                "<i>Use /extrap resume to continue later</i>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ No active extrapolation to stop.")
    
    return stopextrap_command
