"""
Gateway Executor Module

Phase 11.2: Core Function Extraction
Provides timeout-guarded gateway calls, card processing, and response formatting.
Extracted from transferto.py to reduce monolithic file size.
"""

import asyncio
import time
from typing import Tuple, Optional
from telegram import Update
from telegram.ext import ContextTypes
from response_formatter import ApprovalStatus
from bot.core.response_templates import (
    format_single_card_result,
    format_batch_dashboard,
    format_batch_hit,
    format_batch_complete,
    get_card_brand,
)
from bot.domain.card_utils import (
    normalize_card_input,
    get_card_type_from_bin,
    lookup_bin_info,
)
from bot.infrastructure.proxy_pool import (
    proxy_status, get_next_proxy_from_pool
)
from bot.services.logging_utils import log_gateway_error, log_error_metric
from tools.vbv_api import get_vbv_for_card

__all__ = [
    'call_gateway_with_timeout',
    'validate_proxy_before_request',
    'format_and_cache_response',
    'process_single_card',
    'process_batch_cards',
]


async def call_gateway_with_timeout(gateway_fn, *args, timeout=22, retry_on_timeout=True, **kwargs):
    """
    Call a gateway function with a timeout to prevent Telegram timeout.
    Auto-retries once on timeout with different proxy.
    
    Args:
        gateway_fn: The gateway check function to call
        timeout: Maximum seconds to wait (default 22s)
        retry_on_timeout: If True, retry once on timeout (default True)
        *args, **kwargs: Arguments to pass to gateway function
    
    Returns:
        (result_string, proxy_live_bool) tuple
    """
    max_attempts = 2 if retry_on_timeout else 1
    
    for attempt in range(max_attempts):
        try:
            # Use different proxy on retry
            if attempt > 0:
                new_proxy = get_next_proxy_from_pool()
                if new_proxy and 'proxy' in kwargs:
                    kwargs['proxy'] = new_proxy
            
            # Run the blocking gateway call in a thread pool
            result = await asyncio.wait_for(
                asyncio.to_thread(gateway_fn, *args, **kwargs),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            card_bin = args[0][:6] if args else "unknown"
            gateway_name = kwargs.get('gateway_name', gateway_fn.__name__)
            
            if attempt < max_attempts - 1:
                print(f"[RETRY] Timeout on {gateway_name}, retrying with different proxy...")
                continue
            
            log_gateway_error(gateway_name, card_bin, 'timeout', f'Gateway exceeded {timeout}s timeout')
            log_error_metric(gateway_name, 'timeout', card_bin)
            return ("TIMEOUT ⏱️ Gateway took too long (>22s)", False)
        except Exception as e:
            card_bin = args[0][:6] if args else "unknown"
            gateway_name = kwargs.get('gateway_name', gateway_fn.__name__)
            error_type = type(e).__name__
            error_msg = str(e)[:100]
            log_gateway_error(gateway_name, card_bin, error_type, error_msg)
            log_error_metric(gateway_name, error_type, card_bin)
            error_str = str(e)[:50]
            return (f"ERROR ❌ {error_str}", False)
    
    return ("ERROR ❌ Gateway call failed", False)


def validate_proxy_before_request(proxy_url=None, timeout=5):
    """
    Test proxy connectivity before making gateway requests.
    
    Returns:
        bool: True if proxy is reachable, False otherwise
    """
    from gates.utilities import check_proxy_health, get_proxy, get_proxy_status, mark_proxy_failure
    
    if proxy_url is None:
        proxy_dict = get_proxy(force_check=True)
        status = get_proxy_status()
        
        if status['is_alive']:
            proxy_status["live"] = True
            proxy_status["checked"] = True
            proxy_status["ip"] = status.get('last_ip', 'Unknown')
            return True
        else:
            print("[!] Proxy appears dead, attempting reconnection...")
            is_alive, ip = check_proxy_health(proxy_dict, timeout=timeout)
            
            if is_alive:
                proxy_status["live"] = True
                proxy_status["checked"] = True
                proxy_status["ip"] = ip
                return True
            else:
                mark_proxy_failure()
                proxy_status["live"] = False
                proxy_status["checked"] = True
                return False
    
    # Test specific proxy URL
    try:
        import requests
        proxy_dict = {'http': proxy_url, 'https': proxy_url}
        response = requests.get('https://api.ipify.org?format=json', proxies=proxy_dict, timeout=timeout)
        return response.status_code == 200
    except:
        return False


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
    
    Phase 11.2: Extracted from transferto.py for reusability.
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
    
    # Note: Auto-caching disabled for PCI-DSS compliance
    # Storing plaintext PAN/CVV data is a security violation
    
    return formatted


async def process_single_card(
    card_input: str,
    gateway_fn,
    gateway_name: str,
    gateway_amount: float = 0.00,
    proxy: str = None,
    timeout: int = 25
) -> Tuple[str, bool]:
    """
    Process a single card through a gateway with full VBV lookup and formatting.
    
    Phase 11.2: Extracted from transferto.py for reusability.
    
    Args:
        card_input: Card in format CARD|MM|YY|CVV
        gateway_fn: Gateway function to call
        gateway_name: Display name of gateway
        gateway_amount: Transaction amount in USD
        proxy: Proxy URL to use
        timeout: Timeout in seconds
        
    Returns:
        (formatted_response, proxy_ok) tuple
    """
    parts = card_input.split('|')
    if len(parts) != 4:
        return ("❌ Invalid card format. Use: CARD|MM|YY|CVV", False)
    
    card_num, card_mon, card_yer, card_cvc = parts[0], parts[1], parts[2], parts[3]
    
    # Call gateway with timeout
    result, proxy_ok = await call_gateway_with_timeout(
        gateway_fn, card_num, card_mon, card_yer, card_cvc, 
        timeout=timeout, proxy=proxy
    )
    
    # Log gateway response for debugging
    print(f"[GATE] {gateway_name} | Card: {card_num[-4:]} | Result: {result} | Proxy: {proxy_ok}")
    
    # Determine status from result
    status = ApprovalStatus.DECLINED
    if result and "Error" not in result:
        result_lower = result.lower()
        if any(keyword in result_lower for keyword in ["charged", "approved", "success", "accesstoken", "cartid", "ccn", "live"]):
            status = ApprovalStatus.APPROVED
        elif "cvv" in result_lower:
            status = ApprovalStatus.CVV_ISSUE
        elif "insufficient" in result_lower:
            status = ApprovalStatus.INSUFFICIENT_FUNDS
    
    # Lookup BIN and VBV info
    bank_name, country = lookup_bin_info(card_num)
    card_brand = get_card_brand(card_num)
    card_type = get_card_type_from_bin(card_num)
    
    vbv_info = await get_vbv_for_card(card_num, card_mon, card_yer, card_cvc)
    vbv_status = vbv_info.get("vbv_status", "Unknown")
    vbv_bank = vbv_info.get("bank", bank_name)
    vbv_country = vbv_info.get("country", country)
    vbv_country_emoji = vbv_info.get("country_emoji", "")
    vbv_card_type = vbv_info.get("card_type", card_type)
    
    # Format response
    status_str = "APPROVED" if status == ApprovalStatus.APPROVED else \
                 "CVV" if status == ApprovalStatus.CVV_ISSUE else \
                 "NSF" if status == ApprovalStatus.INSUFFICIENT_FUNDS else "DECLINED"
    
    cvv_match = status != ApprovalStatus.CVV_ISSUE
    ccn_live = status in [ApprovalStatus.APPROVED, ApprovalStatus.CVV_ISSUE, ApprovalStatus.INSUFFICIENT_FUNDS]
    
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
    
    return formatted_response, proxy_ok


async def process_batch_cards(
    cards: list,
    gateway_fn,
    gateway_name: str,
    gateway_amount: float = 0.00,
    proxy: str = None,
    update: Update = None,
    progress_callback = None
) -> dict:
    """
    Process a batch of cards (2-25) through a gateway with progress tracking.
    
    Phase 11.2: Extracted from transferto.py for reusability.
    
    Args:
        cards: List of card strings in format CARD|MM|YY|CVV
        gateway_fn: Gateway function to call
        gateway_name: Display name of gateway
        gateway_amount: Transaction amount in USD
        proxy: Proxy URL to use
        update: Telegram Update object (optional, for progress updates)
        progress_callback: Optional callback function for progress updates
        
    Returns:
        dict with stats: {"approved": int, "declined": int, "cvv": int, "nsf": int, "three_ds": int, "results": list}
    """
    stats = {"approved": 0, "declined": 0, "cvv": 0, "nsf": 0, "three_ds": 0, "results": []}
    
    for idx, card_input in enumerate(cards, 1):
        parts = card_input.split('|')
        if len(parts) != 4:
            stats["declined"] += 1
            continue
            
        card_num, card_mon, card_yer, card_cvc = parts[0], parts[1], parts[2], parts[3]
        
        start_time = time.time()
        result, proxy_ok = await call_gateway_with_timeout(
            gateway_fn, card_num, card_mon, card_yer, card_cvc, 
            timeout=22, proxy=proxy
        )
        elapsed_sec = round(time.time() - start_time, 2)
        
        print(f"[GATE] {gateway_name} Batch {idx}/{len(cards)} | Card: {card_num[-4:]} | Result: {result}")
        
        # Determine status
        status = ApprovalStatus.DECLINED
        if result and "Error" not in result:
            result_lower = result.lower()
            if any(keyword in result_lower for keyword in ["charged", "approved", "success", "accesstoken", "cartid", "ccn", "live"]):
                status = ApprovalStatus.APPROVED
                stats["approved"] += 1
            elif "cvv" in result_lower:
                status = ApprovalStatus.CVV_ISSUE
                stats["cvv"] += 1
            elif "3ds" in result_lower or "authentication" in result_lower:
                stats["three_ds"] += 1
                stats["declined"] += 1
            elif "insufficient" in result_lower:
                status = ApprovalStatus.INSUFFICIENT_FUNDS
                stats["nsf"] += 1
            else:
                stats["declined"] += 1
        else:
            stats["declined"] += 1
        
        # Lookup card info
        bank_name, country = lookup_bin_info(card_num)
        card_brand = get_card_brand(card_num)
        card_type = get_card_type_from_bin(card_num)
        
        status_str = "APPROVED" if status == ApprovalStatus.APPROVED else \
                     "CVV" if status == ApprovalStatus.CVV_ISSUE else \
                     "NSF" if status == ApprovalStatus.INSUFFICIENT_FUNDS else "DECLINED"
        
        cvv_match = status != ApprovalStatus.CVV_ISSUE
        ccn_live = status in [ApprovalStatus.APPROVED, ApprovalStatus.CVV_ISSUE, ApprovalStatus.INSUFFICIENT_FUNDS]
        
        # Store result
        result_data = {
            "card_input": card_input,
            "status": status_str,
            "bank": bank_name,
            "country": country,
            "cvv_match": cvv_match,
            "ccn_live": ccn_live,
            "elapsed_sec": elapsed_sec
        }
        stats["results"].append(result_data)
        
        # Send hit notification for live cards
        if status in [ApprovalStatus.APPROVED, ApprovalStatus.CVV_ISSUE, ApprovalStatus.INSUFFICIENT_FUNDS]:
            hit_msg = format_batch_hit(
                card_input=card_input,
                status=status_str,
                card_brand=card_brand,
                card_type=card_type,
                bank_name=bank_name,
                country=country,
                gateway=gateway_name,
                progress=f"{idx}/{len(cards)}"
            )
            
            if update:
                try:
                    await update.message.reply_text(hit_msg, parse_mode='HTML')
                except:
                    pass
        
        # Progress callback
        if progress_callback:
            await progress_callback(idx, len(cards), stats)
    
    return stats
