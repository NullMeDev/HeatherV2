"""
Gateway Executor Module

Phase 11.2: Core Function Extraction
Phase 12.3: Batch Processing Optimization with Concurrency Control
Provides timeout-guarded gateway calls, card processing, and response formatting.
Extracted from transferto.py to reduce monolithic file size.
"""

import asyncio
import time
from typing import Tuple, Optional, List, Dict, Any
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
    'process_batch_cards_concurrent',  # Phase 12.3
]


# Phase 12.3: Global concurrency limiter for batch operations
_batch_semaphore: Optional[asyncio.Semaphore] = None
_batch_error_rate: Dict[str, float] = {}  # Track error rates by gateway


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


# =============================================================================
# Phase 12.3: Concurrent Batch Processing with Adaptive Rate Limiting
# =============================================================================

def init_batch_semaphore(max_concurrent: int = 12):
    """
    Initialize the global batch processing semaphore.
    
    Phase 12.3: Controls maximum concurrent gateway requests.
    
    Args:
        max_concurrent: Maximum number of concurrent requests (default 12)
    """
    global _batch_semaphore
    _batch_semaphore = asyncio.Semaphore(max_concurrent)
    print(f"[✓] Batch semaphore initialized: {max_concurrent} concurrent requests")


def get_adaptive_concurrency(gateway_name: str, default: int = 12) -> int:
    """
    Get adaptive concurrency limit based on error rate.
    
    Phase 12.3: Reduces concurrency when error rate is high.
    
    Args:
        gateway_name: Name of the gateway
        default: Default concurrency limit
        
    Returns:
        Adjusted concurrency limit (6-15)
    """
    error_rate = _batch_error_rate.get(gateway_name, 0.0)
    
    if error_rate > 0.5:  # >50% errors
        return max(6, default // 2)
    elif error_rate > 0.3:  # >30% errors
        return max(8, int(default * 0.7))
    elif error_rate < 0.1:  # <10% errors, increase
        return min(15, default + 3)
    else:
        return default


async def _process_single_card_task(
    card_input: str,
    card_idx: int,
    total_cards: int,
    gateway_fn,
    gateway_name: str,
    gateway_amount: float,
    proxy: str,
    update: Update,
    stats: Dict[str, Any],
    results_lock: asyncio.Lock
) -> Dict[str, Any]:
    """
    Process a single card with concurrency control.
    
    Phase 12.3: Internal task for concurrent processing.
    """
    global _batch_semaphore
    
    parts = card_input.split('|')
    if len(parts) != 4:
        async with results_lock:
            stats["declined"] += 1
        return {"status": "INVALID", "card_input": card_input}
    
    card_num, card_mon, card_yer, card_cvc = parts[0], parts[1], parts[2], parts[3]
    
    # Acquire semaphore to limit concurrency
    if _batch_semaphore is None:
        init_batch_semaphore()
    
    async with _batch_semaphore:
        start_time = time.time()
        result, proxy_ok = await call_gateway_with_timeout(
            gateway_fn, card_num, card_mon, card_yer, card_cvc,
            timeout=22, proxy=proxy
        )
        elapsed_sec = round(time.time() - start_time, 2)
    
    print(f"[GATE] {gateway_name} Batch {card_idx}/{total_cards} | Card: {card_num[-4:]} | Result: {result}")
    
    # Determine status
    status = ApprovalStatus.DECLINED
    is_error = False
    
    if result and "Error" not in result and "TIMEOUT" not in result:
        result_lower = result.lower()
        if any(keyword in result_lower for keyword in ["charged", "approved", "success", "accesstoken", "cartid", "ccn", "live"]):
            status = ApprovalStatus.APPROVED
        elif "cvv" in result_lower:
            status = ApprovalStatus.CVV_ISSUE
        elif "3ds" in result_lower or "authentication" in result_lower:
            pass  # Declined with 3DS
        elif "insufficient" in result_lower:
            status = ApprovalStatus.INSUFFICIENT_FUNDS
    else:
        is_error = True
    
    # Update stats
    async with results_lock:
        if status == ApprovalStatus.APPROVED:
            stats["approved"] += 1
        elif status == ApprovalStatus.CVV_ISSUE:
            stats["cvv"] += 1
        elif status == ApprovalStatus.INSUFFICIENT_FUNDS:
            stats["nsf"] += 1
        else:
            stats["declined"] += 1
        
        if "3ds" in result.lower() or "authentication" in result.lower():
            stats["three_ds"] += 1
        
        # Update error rate
        if is_error:
            _batch_error_rate[gateway_name] = _batch_error_rate.get(gateway_name, 0.0) * 0.9 + 0.1
        else:
            _batch_error_rate[gateway_name] = _batch_error_rate.get(gateway_name, 0.0) * 0.9
    
    # Lookup card info
    bank_name, country = lookup_bin_info(card_num)
    card_brand = get_card_brand(card_num)
    card_type = get_card_type_from_bin(card_num)
    
    status_str = "APPROVED" if status == ApprovalStatus.APPROVED else \
                 "CVV" if status == ApprovalStatus.CVV_ISSUE else \
                 "NSF" if status == ApprovalStatus.INSUFFICIENT_FUNDS else "DECLINED"
    
    cvv_match = status != ApprovalStatus.CVV_ISSUE
    ccn_live = status in [ApprovalStatus.APPROVED, ApprovalStatus.CVV_ISSUE, ApprovalStatus.INSUFFICIENT_FUNDS]
    
    result_data = {
        "card_input": card_input,
        "status": status_str,
        "bank": bank_name,
        "country": country,
        "cvv_match": cvv_match,
        "ccn_live": ccn_live,
        "elapsed_sec": elapsed_sec
    }
    
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
            progress=f"{card_idx}/{total_cards}"
        )
        
        if update:
            try:
                await update.message.reply_text(hit_msg, parse_mode='HTML')
            except:
                pass
    
    return result_data


async def process_batch_cards_concurrent(
    cards: List[str],
    gateway_fn,
    gateway_name: str,
    gateway_amount: float = 0.00,
    proxy: str = None,
    update: Update = None,
    progress_callback = None,
    max_concurrent: int = 12
) -> Dict[str, Any]:
    """
    Process a batch of cards with controlled concurrency.
    
    Phase 12.3: Processes multiple cards in parallel with:
    - Concurrency limiting (default 12 concurrent requests)
    - Adaptive rate limiting based on error rate
    - Thread-safe statistics tracking
    - Progress callbacks with proper locking
    
    Args:
        cards: List of card strings in format CARD|MM|YY|CVV
        gateway_fn: Gateway function to call
        gateway_name: Display name of gateway
        gateway_amount: Transaction amount in USD
        proxy: Proxy URL to use
        update: Telegram Update object (optional, for progress updates)
        progress_callback: Optional callback function for progress updates
        max_concurrent: Maximum concurrent requests (default 12)
        
    Returns:
        dict with stats: {"approved": int, "declined": int, "cvv": int, "nsf": int, "three_ds": int, "results": list}
    """
    global _batch_semaphore
    
    # Initialize semaphore if needed
    if _batch_semaphore is None:
        init_batch_semaphore(max_concurrent)
    
    # Adaptive concurrency
    adaptive_limit = get_adaptive_concurrency(gateway_name, max_concurrent)
    if adaptive_limit != max_concurrent:
        print(f"[*] Adaptive concurrency for {gateway_name}: {adaptive_limit} (was {max_concurrent})")
        _batch_semaphore = asyncio.Semaphore(adaptive_limit)
    
    # Thread-safe stats
    stats = {"approved": 0, "declined": 0, "cvv": 0, "nsf": 0, "three_ds": 0, "results": []}
    results_lock = asyncio.Lock()
    
    # Create tasks for all cards
    tasks = [
        _process_single_card_task(
            card_input=card,
            card_idx=idx,
            total_cards=len(cards),
            gateway_fn=gateway_fn,
            gateway_name=gateway_name,
            gateway_amount=gateway_amount,
            proxy=proxy,
            update=update,
            stats=stats,
            results_lock=results_lock
        )
        for idx, card in enumerate(cards, 1)
    ]
    
    # Process all cards concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    for result in results:
        if isinstance(result, dict) and result.get("status") != "INVALID":
            stats["results"].append(result)
    
    # Final progress callback
    if progress_callback:
        await progress_callback(len(cards), len(cards), stats)
    
    return stats
        
        # Progress callback
        if progress_callback:
            await progress_callback(idx, len(cards), stats)
    
    return stats
