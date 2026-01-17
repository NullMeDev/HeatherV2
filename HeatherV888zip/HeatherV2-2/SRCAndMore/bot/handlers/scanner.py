"""
Stripe/Site scanner command handlers using factory pattern.
Handles site categorization, store imports, and Stripe statistics.
"""
import asyncio
import requests
from telegram import Update
from telegram.ext import ContextTypes
from typing import Callable, Any

__all__ = [
    'create_categorize_sites_handler',
    'create_import_shopify_stores_handler',
    'create_import_stripe_sites_handler',
    'create_stripe_stats_handler',
]


def create_categorize_sites_handler(detect_platform: Callable):
    """
    Factory for /categorize command handler.
    
    Args:
        detect_platform: Function to detect platform from site URL
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        
        replied = update.message.reply_to_message
        sites = []
        
        if replied and replied.document:
            try:
                file = await replied.document.get_file()
                file_bytes = await file.download_as_bytearray()
                content = file_bytes.decode('utf-8', errors='ignore')
                sites = [line.strip() for line in content.splitlines() if line.strip()]
            except Exception as e:
                await update.message.reply_text(f"Error reading file: {str(e)[:50]}")
                return
        elif context.args:
            sites = context.args
        else:
            await update.message.reply_text(
                "Usage: /categorize site1.com site2.com\n"
                "Or reply to a .txt file with /categorize"
            )
            return
        
        if not sites:
            await update.message.reply_text("No sites provided")
            return
        
        if len(sites) > 500:
            await update.message.reply_text(f"Too many sites ({len(sites)}). Max 500 per batch.")
            return
        
        await update.message.reply_text(f"Scanning {len(sites)} sites...")
        
        session = requests.Session()
        session.verify = False
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'})
        
        results = {'shopify': [], 'woocommerce': [], 'magento': [], 'bigcommerce': [], 'unknown': [], 'error': []}
        
        for i, site in enumerate(sites):
            if not site.startswith('http'):
                site = f"https://{site}"
            
            try:
                detection = detect_platform(session, site)
                platform = detection['platform']
                processor = detection['payment_processor']
                pk = detection.get('stripe_pk', '')
                
                entry = f"{site} [{processor}]" + (f" pk:{pk[:20]}..." if pk else "")
                
                if platform in results:
                    results[platform].append(entry)
                else:
                    results['unknown'].append(entry)
                    
            except Exception as e:
                results['error'].append(f"{site} - {str(e)[:30]}")
            
            if (i + 1) % 50 == 0:
                await update.message.reply_text(f"Progress: {i+1}/{len(sites)}")
        
        summary = f"Site Scan Complete ({len(sites)} sites)\n\n"
        for platform, entries in results.items():
            if entries:
                summary += f"{platform.upper()}: {len(entries)}\n"
        
        await update.message.reply_text(summary)
        
        for platform, entries in results.items():
            if entries and len(entries) <= 50:
                content = f"{platform.upper()} Sites:\n" + "\n".join(entries[:50])
                await update.message.reply_text(content[:4000])
    
    return handler


def create_import_shopify_stores_handler(add_stores_bulk_async: Callable):
    """
    Factory for /importstores command handler.
    
    Args:
        add_stores_bulk_async: Async function to bulk add stores
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        
        replied = update.message.reply_to_message
        if not replied or not replied.document:
            await update.message.reply_text(
                "Usage: Reply to a .txt file with /importstores\n"
                "File should contain one store URL per line"
            )
            return
        
        try:
            file = await replied.document.get_file()
            file_bytes = await file.download_as_bytearray()
            content = file_bytes.decode('utf-8', errors='ignore')
            urls = [line.strip() for line in content.splitlines() if line.strip()]
        except Exception as e:
            await update.message.reply_text(f"Error reading file: {str(e)[:50]}")
            return
        
        if not urls:
            await update.message.reply_text("No URLs found in file")
            return
        
        await update.message.reply_text(f"Importing {len(urls)} stores to database...")
        
        async def progress(current, total, stage):
            if current % 500 == 0:
                await update.message.reply_text(f"Progress: {current}/{total} ({stage})")
        
        result = await add_stores_bulk_async(urls, progress_callback=progress)
        
        await update.message.reply_text(
            f"Import Complete\n\n"
            f"Added: {result['added']}\n"
            f"Skipped (duplicates): {result['skipped']}\n"
            f"Errors: {result['errors']}"
        )
    
    return handler


def create_import_stripe_sites_handler(
    add_stripe_sites_bulk: Callable,
    count_stripe_sites: Callable
):
    """
    Factory for /importstripe command handler.
    
    Args:
        add_stripe_sites_bulk: Function to bulk add stripe sites
        count_stripe_sites: Function to count stripe sites
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        
        replied = update.message.reply_to_message
        if not replied or not replied.document:
            await update.message.reply_text(
                "Reply to a .txt file with /importstripe\n"
                "File should contain one URL per line"
            )
            return
        
        try:
            file = await replied.document.get_file()
            file_bytes = await file.download_as_bytearray()
            content = file_bytes.decode('utf-8', errors='ignore')
            urls = [line.strip() for line in content.splitlines() if line.strip()]
        except Exception as e:
            await update.message.reply_text(f"Error reading file: {str(e)[:50]}")
            return
        
        if not urls:
            await update.message.reply_text("No URLs found in file")
            return
        
        await update.message.reply_text(f"Importing {len(urls)} sites to Stripe database...")
        
        result = await asyncio.to_thread(add_stripe_sites_bulk, urls)
        stats = count_stripe_sites()
        
        await update.message.reply_text(
            f"Stripe Import Complete\n\n"
            f"Added: {result['added']}\n"
            f"Skipped: {result['skipped']}\n"
            f"Errors: {result['errors']}\n\n"
            f"Total in DB: {stats['total']}\n"
            f"Ready: {stats['ready']}\n"
            f"Pending: {stats['pending']}"
        )
    
    return handler


def create_stripe_stats_handler(
    count_stripe_sites: Callable,
    get_valid_stripe_keys: Callable
):
    """
    Factory for /stripestats command handler.
    
    Args:
        count_stripe_sites: Function to count stripe sites
        get_valid_stripe_keys: Function to get valid stripe keys
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        
        stats = count_stripe_sites()
        keys = get_valid_stripe_keys(limit=5)
        
        msg = (
            f"Stripe Site Database\n\n"
            f"Total Sites: {stats['total']}\n"
            f"Ready (with valid keys): {stats['ready']}\n"
            f"Pending: {stats['pending']}\n"
            f"No Stripe/Error: {stats['error']}"
        )
        
        if keys:
            msg += "\n\nRecent Valid Keys:"
            for k in keys[:3]:
                msg += f"\n• {k['domain']}: {k['pk_key'][:25]}..."
        
        await update.message.reply_text(msg)
    
    return handler
