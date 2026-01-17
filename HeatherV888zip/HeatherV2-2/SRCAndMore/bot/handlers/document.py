"""
Document Queue Handler Module

Phase 11: Complete Gateway Handler Extraction
Handles document uploads and queue processing for batch card checking.
"""

from telegram import Update
from telegram.ext import ContextTypes
import time

__all__ = [
    'create_document_handler',
    'create_queue_handler',
    'create_massall_handler',
    'create_clearqueue_handler',
    'create_stopall_handler',
]


async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle uploaded text documents for batch card processing.
    Queues document for processing with /massall command.
    """
    from bot.services.session_manager import (
        queue_document, get_queued_documents, MAX_CONCURRENT_DOCS,
        count_active_sessions
    )
    
    user_id = update.effective_user.id
    doc = update.message.document
    
    if not doc or not doc.file_name.endswith(('.txt', '.csv')):
        await update.message.reply_text(
            "❌ Please upload a .txt or .csv file containing cards.\n"
            "Format: One card per line (CARD|MM|YY|CVV)",
            parse_mode='HTML'
        )
        return
    
    # Check active sessions
    active_count = count_active_sessions()
    if active_count >= MAX_CONCURRENT_DOCS:
        await update.message.reply_text(
            f"⏳ Maximum concurrent sessions reached ({MAX_CONCURRENT_DOCS}).\n"
            f"Please wait for active sessions to complete before uploading more files.",
            parse_mode='HTML'
        )
        return
    
    # Download file
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    
    try:
        content = file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        await update.message.reply_text("❌ File encoding error. Please use UTF-8 encoded text files.")
        return
    
    # Count cards in file
    lines = [line.strip() for line in content.split('\n') if line.strip() and '|' in line]
    card_count = len(lines)
    
    if card_count == 0:
        await update.message.reply_text("❌ No valid cards found in file. Use format: CARD|MM|YY|CVV")
        return
    
    # Queue document
    queue_document(user_id, doc.file_id, doc.file_name, card_count)
    
    queued = get_queued_documents(user_id)
    queue_pos = len(queued)
    
    await update.message.reply_text(
        f"✅ <b>Document Queued</b>\n\n"
        f"📄 File: <code>{doc.file_name}</code>\n"
        f"🃏 Cards: <b>{card_count}</b>\n"
        f"📊 Queue Position: <b>#{queue_pos}</b>\n\n"
        f"Use /queue to view all queued files\n"
        f"Use /massall to process all files with a gate",
        parse_mode='HTML'
    )


async def show_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all queued documents for the user."""
    from bot.services.session_manager import get_queued_documents, get_active_doc_sessions
    
    user_id = update.effective_user.id
    queued = get_queued_documents(user_id)
    active = get_active_doc_sessions(user_id)
    
    if not queued and not active:
        await update.message.reply_text(
            "📭 <b>Queue Empty</b>\n\n"
            "Upload .txt/.csv files to queue them for batch processing.\n"
            "Then use /massall <gate> to process all files.",
            parse_mode='HTML'
        )
        return
    
    response = "📊 <b>Document Queue Status</b>\n\n"
    
    if active:
        response += f"⚡ <b>Active Sessions ({len(active)}):</b>\n"
        for doc_id, session_info in active.items():
            filename = session_info.get('filename', 'Unknown')
            gateway = session_info.get('gateway', 'Unknown')
            progress = session_info.get('progress', 0)
            total = session_info.get('total', 0)
            pct = (progress / total * 100) if total > 0 else 0
            response += f"  • {filename} [{gateway}] - {progress}/{total} ({pct:.0f}%)\n"
        response += "\n"
    
    if queued:
        response += f"📋 <b>Queued Files ({len(queued)}):</b>\n"
        for idx, (doc_id, doc_info) in enumerate(queued.items(), 1):
            filename = doc_info.get('filename', 'Unknown')
            card_count = doc_info.get('card_count', 0)
            response += f"  {idx}. {filename} ({card_count} cards)\n"
        response += "\n"
        response += "Use /massall <gate> to process all queued files\n"
        response += "Use /clearqueue to remove all queued files"
    
    await update.message.reply_text(response, parse_mode='HTML')


async def clear_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all queued documents for the user."""
    from bot.services.session_manager import clear_document_queue, get_queued_documents
    
    user_id = update.effective_user.id
    queued = get_queued_documents(user_id)
    
    if not queued:
        await update.message.reply_text("📭 Queue is already empty.", parse_mode='HTML')
        return
    
    cleared_count = len(queued)
    clear_document_queue(user_id)
    
    await update.message.reply_text(
        f"🗑️ <b>Queue Cleared</b>\n\n"
        f"Removed {cleared_count} file(s) from queue.",
        parse_mode='HTML'
    )


async def stop_all_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop all active checking sessions for the user."""
    from bot.services.session_manager import request_stop, get_active_doc_sessions
    
    user_id = update.effective_user.id
    active = get_active_doc_sessions(user_id)
    
    if not active:
        await update.message.reply_text(
            "✅ No active sessions to stop.",
            parse_mode='HTML'
        )
        return
    
    # Request stop for all active sessions
    stopped_count = 0
    for doc_id in active.keys():
        request_stop(user_id, doc_id)
        stopped_count += 1
    
    await update.message.reply_text(
        f"🛑 <b>Stop Requested</b>\n\n"
        f"Stopping {stopped_count} active session(s)...\n"
        f"Current batches will complete, then processing will halt.",
        parse_mode='HTML'
    )


# Factory functions for handler registration
def create_document_handler():
    """Create document upload handler."""
    return handle_document_upload


def create_queue_handler():
    """Create queue view handler."""
    return show_queue


def create_massall_handler():
    """Create massall processing handler (stub - implemented in gateways)."""
    # This is handled by the gateway mass processor
    # Placeholder for future refactoring
    pass


def create_clearqueue_handler():
    """Create clear queue handler."""
    return clear_queue


def create_stopall_handler():
    """Create stop all handler."""
    return stop_all_sessions
