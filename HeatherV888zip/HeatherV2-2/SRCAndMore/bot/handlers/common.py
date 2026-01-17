from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import telegram

from bot.services.session_manager import batch_sessions

__all__ = ['reply_html']


async def reply_html(update: Update, text: str, reply_markup=None):
    """Reply with HTML parsing, handling common errors"""
    try:
        if reply_markup:
            return await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)
        return await update.message.reply_text(text, parse_mode='HTML')
    except telegram.error.Forbidden:
        print("[!] Cannot send message - bot was blocked/kicked")
        return None
    except Exception as e:
        print(f"[!] Error sending message: {e}")
        raise
