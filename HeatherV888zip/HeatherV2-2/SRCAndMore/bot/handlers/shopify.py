"""
Shopify-related command handlers using factory pattern.
Handles store management, scanning, and Shopify gateway commands.
"""
import asyncio
import os
import time
from telegram import Update
from telegram.ext import ContextTypes
from typing import Callable, Dict, Any, Optional

__all__ = [
    'create_shopify_charge_handler',
    'create_shopify_auto_handler',
    'create_shopify_health_handler',
    'create_addstore_handler',
    'create_scanstores_handler',
    'create_addstores_handler',
    'create_handle_store_file',
]


def create_shopify_charge_handler(
    shopify_check_from_file: Callable,
    shopify_nano_check: Callable,
    process_cards_fn: Callable
):
    """
    Factory for /shc (shopify_charge) command handler.
    
    Args:
        shopify_check_from_file: Function to get shopify site from file
        shopify_nano_check: Shopify nano check function
        process_cards_fn: The process_cards_with_gateway function
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        raw_text = update.message.text
        for prefix in ['/shc ', '/shopify_charge ']:
            if raw_text.lower().startswith(prefix):
                raw_text = raw_text[len(prefix):].strip()
                break
        else:
            if '\n' in raw_text:
                raw_text = raw_text.split('\n', 1)[1].strip()
            elif context.args:
                raw_text = ' '.join(context.args)
            else:
                raw_text = ''
        
        def shopify_charge_wrapper(n, m, y, c, proxy=None):
            site = shopify_check_from_file()
            return shopify_nano_check(n, m, y, c, site, proxy)
        
        await process_cards_fn(update, raw_text, shopify_charge_wrapper, "Shopify Charge", "shopify_charge")
    
    return handler


def create_shopify_auto_handler(
    shopify_auto_check: Callable,
    format_and_cache_response: Callable,
    lookup_bin_info: Callable,
    detect_security_type: Callable,
    get_proxy_status_emoji: Callable,
    approval_status_class,
    proxy: str
):
    """
    Factory for /sho (shopify_auto) command handler.
    
    Args:
        shopify_auto_check: The shopify auto check function
        format_and_cache_response: Response formatter function
        lookup_bin_info: BIN lookup function
        detect_security_type: Security type detection function
        get_proxy_status_emoji: Proxy status emoji function
        approval_status_class: ApprovalStatus enum class
        proxy: Proxy string
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "<b>Auto Shopify Gate</b>\n\n"
                "Usage: <code>/sho URL CARD|MM|YY|CVV</code>\n\n"
                "Example:\n<code>/sho mystore.com 4242424242424242|12|25|123</code>",
                parse_mode='HTML'
            )
            return
        
        shopify_url = context.args[0]
        card_input = context.args[1]
        parts = card_input.split('|')
        if len(parts) != 4:
            await update.message.reply_text("Invalid card format! Use CARD|MM|YY|CVV", parse_mode='HTML')
            return
        
        card_num = parts[0].strip()
        card_mon = parts[1].strip()
        card_yer = parts[2].strip()
        card_cvc = parts[3].strip()
        
        processing = await update.message.reply_text(f"Checking on {shopify_url}...\n{get_proxy_status_emoji()}")
        
        result, proxy_ok = await shopify_auto_check(shopify_url, card_num, card_mon, card_yer, card_cvc, proxy=proxy)
        
        status = approval_status_class.DECLINED
        if result:
            if "charged" in result.lower():
                status = approval_status_class.APPROVED
            elif "ccn live" in result.lower() or "cvv" in result.lower() or "insufficient" in result.lower():
                status = approval_status_class.CVV_ISSUE
            elif "approved" in result.lower():
                status = approval_status_class.APPROVED
        
        bank_name, country = lookup_bin_info(card_num)
        formatted_response = await format_and_cache_response(
            gateway_name=f"Shopify Auto ({shopify_url[:20]}...)" if len(shopify_url) > 20 else f"Shopify Auto ({shopify_url})",
            card_input=card_input,
            status=status,
            message=result,
            elapsed_sec=1.0,
            security_type=detect_security_type(result),
            vbv_status="Unknown",
            proxy_alive=proxy_ok == "Yes",
            bank_name=bank_name,
            country=country
        )
        await processing.edit_text(formatted_response, parse_mode='HTML')
    
    return handler


def create_shopify_health_handler(
    get_next_shopify_site: Callable,
    advanced_shopify_health: Callable,
    mark_store_working: Callable,
    mark_store_failure: Callable
):
    """
    Factory for /shopify_health command handler.
    
    Args:
        get_next_shopify_site: Function to get next shopify site
        advanced_shopify_health: Health check function
        mark_store_working: Mark store as working
        mark_store_failure: Mark store as failed
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        site = context.args[0].strip() if context.args else get_next_shopify_site()
        await update.message.reply_text(f"Checking Shopify store health...\n{site}")

        stats = advanced_shopify_health(site)
        html_ok = stats.get('html_ok')
        products_ok = stats.get('products_ok')
        status_code = stats.get('status_code')

        if html_ok and products_ok:
            mark_store_working(site)
            verdict = "✅ Store looks healthy (HTML + products)"
        elif html_ok:
            mark_store_failure(site)
            verdict = "⚠️ HTML OK but products missing"
        else:
            mark_store_failure(site)
            verdict = "❌ Store not responding correctly"

        msg = (
            f"🏪 <b>Store:</b> {site}\n"
            f"📄 HTML reachable: {'Yes' if html_ok else 'No'} (status {status_code})\n"
            f"🛒 products.json: {'Yes' if products_ok else 'No'}\n"
            f"📊 Verdict: {verdict}"
        )
        await update.message.reply_text(msg, parse_mode='HTML')
    
    return handler


def create_addstore_handler(add_store: Callable):
    """
    Factory for /addstore command handler.
    
    Args:
        add_store: Function to add a store to database
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "<b>Add Shopify Store</b>\n\n"
                "Usage: <code>/addstore URL</code>\n\n"
                "Example: <code>/addstore mystore.myshopify.com</code>",
                parse_mode='HTML'
            )
            return
        
        url = context.args[0]
        processing = await update.message.reply_text("Adding store...")
        
        try:
            success, message = await asyncio.to_thread(add_store, url)
            
            if success:
                await processing.edit_text(f"Added: {message}\n\nUse /scanstores to discover products.", parse_mode='HTML')
            else:
                error_detail = message
                if "Database not configured" in message:
                    error_detail = "Database connection failed. Please check DATABASE_URL is set correctly."
                elif "already exists" in message:
                    error_detail = f"Store already exists in database: {url}"
                await processing.edit_text(f"<b>Failed to add store</b>\n\n<b>Reason:</b> {error_detail}", parse_mode='HTML')
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower():
                error_detail = f"Database connection error: {error_msg[:100]}"
            elif "permission" in error_msg.lower():
                error_detail = f"Permission error: {error_msg[:100]}"
            else:
                error_detail = f"Unexpected error: {error_msg[:150]}"
            await processing.edit_text(f"<b>Error adding store</b>\n\n<b>Details:</b> {error_detail}", parse_mode='HTML')
    
    return handler


def create_scanstores_handler(
    count_stores: Callable,
    scan_all_pending_stores: Callable,
    background_store_tasks: Dict,
    proxy: str
):
    """
    Factory for /scanstores command handler.
    
    Args:
        count_stores: Function to count stores
        scan_all_pending_stores: Function to scan pending stores
        background_store_tasks: Dict tracking background tasks
        proxy: Proxy string
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        
        if user_id in background_store_tasks and not background_store_tasks[user_id]["task"].done():
            elapsed = time.time() - background_store_tasks[user_id]["started"]
            await update.message.reply_text(
                f"A store operation is already running ({background_store_tasks[user_id]['type']}).\n"
                f"Elapsed: {elapsed:.0f}s\n\n"
                f"Please wait or use /stopstores to cancel.",
                parse_mode='HTML'
            )
            return
        
        stats = await asyncio.to_thread(count_stores)
        pending = stats.get("pending", 0)
        
        if pending == 0:
            await update.message.reply_text("No pending stores to scan. Add stores with /addstores first.", parse_mode='HTML')
            return
        
        concurrency = 25 if pending > 100 else 15
        
        processing = await update.message.reply_text(
            f"<b>Scanning {pending} stores in background...</b>\n\n"
            f"Concurrency: {concurrency}\n"
            f"You can continue using the bot normally.\n\n"
            f"Use /stopstores to cancel if needed.",
            parse_mode='HTML'
        )
        
        async def background_scan_task():
            last_update = [0]
            start_time = time.time()
            
            async def progress_callback(current, total, domain, success):
                if current - last_update[0] >= 10 or current == total:
                    last_update[0] = current
                    elapsed = time.time() - start_time
                    rate = current / elapsed if elapsed > 0 else 0
                    eta = (total - current) / rate if rate > 0 else 0
                    try:
                        await processing.edit_text(
                            f"<b>Scanning stores...</b>\n\n"
                            f"Progress: {current}/{total}\n"
                            f"Last: {domain} {'OK' if success else 'FAIL'}\n"
                            f"Speed: {rate:.1f}/s | ETA: {eta:.0f}s\n\n"
                            f"<i>You can use other commands!</i>",
                            parse_mode='HTML'
                        )
                    except:
                        pass
            
            try:
                result = await scan_all_pending_stores(proxy=proxy, concurrency=concurrency, progress_callback=progress_callback)
                
                total_time = time.time() - start_time
                await processing.edit_text(
                    f"<b>SCAN COMPLETE</b>\n\n"
                    f"Total: {result['total']}\n"
                    f"Success: {result['success_count']}\n"
                    f"Errors: {result['error_count']}\n"
                    f"Time: {total_time:.1f}s\n\n"
                    f"Use /stores to see results.",
                    parse_mode='HTML'
                )
            finally:
                if user_id in background_store_tasks:
                    del background_store_tasks[user_id]
        
        task = asyncio.create_task(background_scan_task())
        background_store_tasks[user_id] = {"task": task, "type": "scan", "started": time.time()}
    
    return handler


def create_addstores_handler(
    add_stores_bulk: Callable,
    add_stores_bulk_async: Callable,
    background_store_tasks: Dict,
    uploaded_files: Dict
):
    """
    Factory for /addstores command handler.
    
    Args:
        add_stores_bulk: Sync bulk add function
        add_stores_bulk_async: Async bulk add function
        background_store_tasks: Dict tracking background tasks
        uploaded_files: Dict tracking uploaded files
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        file_path = None
        
        if user_id in background_store_tasks and not background_store_tasks[user_id]["task"].done():
            elapsed = time.time() - background_store_tasks[user_id]["started"]
            await update.message.reply_text(
                f"A store operation is already running ({background_store_tasks[user_id]['type']}).\n"
                f"Elapsed: {elapsed:.0f}s\n\n"
                f"Please wait or use /stopstores to cancel.",
                parse_mode='HTML'
            )
            return
        
        if update.message.document:
            file = await context.bot.get_file(update.message.document.file_id)
            file_path = f"/tmp/stores_{user_id}.txt"
            await file.download_to_drive(file_path)
        elif update.message.reply_to_message and update.message.reply_to_message.document:
            file_obj = update.message.reply_to_message.document
            file = await file_obj.get_file()
            file_path = f"/tmp/stores_{user_id}.txt"
            await file.download_to_drive(file_path)
        elif user_id in uploaded_files and os.path.exists(uploaded_files[user_id]):
            file_path = uploaded_files[user_id]
        
        if file_path and os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().strip()
            
            urls = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
            urls = [u for u in urls if '.' in u and '|' not in u]
            
            if not urls:
                await update.message.reply_text("No valid store URLs found in file. Make sure each line contains a domain (e.g., store.myshopify.com)", parse_mode='HTML')
                return
            
            processing = await update.message.reply_text(
                f"<b>Adding {len(urls)} stores in background...</b>\n\n"
                f"You can continue using the bot normally.\n"
                f"Progress updates will appear here.",
                parse_mode='HTML'
            )
            
            async def background_add_task():
                last_update = [0]
                
                async def progress_cb(current, total, stage):
                    if current - last_update[0] >= 100 or current == total:
                        last_update[0] = current
                        try:
                            await processing.edit_text(
                                f"<b>Adding stores... ({stage})</b>\n\n"
                                f"Progress: {current}/{total}\n"
                                f"You can continue using other commands.",
                                parse_mode='HTML'
                            )
                        except:
                            pass
                
                try:
                    result = await add_stores_bulk_async(urls, progress_callback=progress_cb)
                    
                    await processing.edit_text(
                        f"<b>BULK IMPORT COMPLETE</b>\n\n"
                        f"Added: {result['added']}\n"
                        f"Skipped (duplicates): {result['skipped']}\n"
                        f"Errors: {result['errors']}\n\n"
                        f"Use /scanstores to discover products.",
                        parse_mode='HTML'
                    )
                finally:
                    if user_id in background_store_tasks:
                        del background_store_tasks[user_id]
            
            task = asyncio.create_task(background_add_task())
            background_store_tasks[user_id] = {"task": task, "type": "bulk_add", "started": time.time()}
            return
        
        if context.args:
            urls = ' '.join(context.args).replace(',', ' ').split()
            urls = [u.strip() for u in urls if u.strip() and '.' in u]
            
            if not urls:
                await update.message.reply_text("No valid URLs provided.", parse_mode='HTML')
                return
            
            if len(urls) > 50:
                processing = await update.message.reply_text(
                    f"<b>Adding {len(urls)} stores in background...</b>\n\n"
                    f"You can continue using the bot normally.",
                    parse_mode='HTML'
                )
                
                async def background_add_task():
                    try:
                        result = await add_stores_bulk_async(urls)
                        await processing.edit_text(
                            f"<b>BULK IMPORT COMPLETE</b>\n\n"
                            f"Added: {result['added']}\n"
                            f"Skipped (duplicates): {result['skipped']}\n"
                            f"Errors: {result['errors']}\n\n"
                            f"Use /scanstores to discover products.",
                            parse_mode='HTML'
                        )
                    finally:
                        if user_id in background_store_tasks:
                            del background_store_tasks[user_id]
                
                task = asyncio.create_task(background_add_task())
                background_store_tasks[user_id] = {"task": task, "type": "bulk_add", "started": time.time()}
            else:
                processing = await update.message.reply_text(f"Adding {len(urls)} stores...")
                result = await asyncio.to_thread(add_stores_bulk, urls)
                await processing.edit_text(
                    f"<b>BULK IMPORT COMPLETE</b>\n\n"
                    f"Added: {result['added']}\n"
                    f"Skipped (duplicates): {result['skipped']}\n"
                    f"Errors: {result['errors']}\n\n"
                    f"Use /scanstores to discover products.",
                    parse_mode='HTML'
                )
            return
        
        await update.message.reply_text(
            "<b>Bulk Add Stores</b>\n\n"
            "<b>Option 1:</b> Upload a .txt file, then reply to it with /addstores\n\n"
            "<b>Option 2:</b> Send URLs directly:\n"
            "<code>/addstores store1.com store2.com store3.com</code>\n\n"
            "After adding, use /scanstores to discover products.\n\n"
            "<i>Large imports run in background - you can keep using the bot!</i>",
            parse_mode='HTML'
        )
    
    return handler


def create_handle_store_file(add_stores_bulk: Callable):
    """
    Factory for store file upload handler.
    
    Args:
        add_stores_bulk: Bulk add stores function
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.document:
            return
        
        filename = update.message.document.file_name or ""
        if not filename.endswith('.txt') and not filename.endswith('.csv'):
            return
        
        file = await context.bot.get_file(update.message.document.file_id)
        file_path = f"/tmp/stores_{update.message.from_user.id}.txt"
        await file.download_to_drive(file_path)
        
        with open(file_path, 'r') as f:
            urls = f.read().strip().split('\n')
        
        os.remove(file_path)
        
        processing = await update.message.reply_text(f"Adding {len(urls)} stores from file...")
        
        result = await asyncio.to_thread(add_stores_bulk, urls)
        
        await processing.edit_text(
            f"<b>BULK IMPORT COMPLETE</b>\n\n"
            f"Added: {result['added']}\n"
            f"Skipped (duplicates): {result['skipped']}\n"
            f"Errors: {result['errors']}\n\n"
            f"Use /scanstores to discover products.",
            parse_mode='HTML'
        )
    
    return handler
