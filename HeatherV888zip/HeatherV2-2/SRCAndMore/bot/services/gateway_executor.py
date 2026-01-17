"""
Gateway Executor Module

Provides timeout-guarded gateway calls with retry logic and proxy rotation.
"""

import asyncio
from bot.infrastructure.proxy_pool import (
    proxy_status, get_next_proxy_from_pool
)
from bot.services.logging_utils import log_gateway_error, log_error_metric

__all__ = [
    'call_gateway_with_timeout',
    'validate_proxy_before_request',
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
