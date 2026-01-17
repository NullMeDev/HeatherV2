"""
Proxy Pool Management Module

Provides proxy rotation, failover, and pool management utilities.
Extracted from transferto.py for modular architecture.
"""

import os
import time
from config import PROXY, COLOR_RED, COLOR_GREEN, COLOR_ORANGE, COLOR_RESET

__all__ = [
    'proxy_pool',
    'proxy_status',
    'init_proxy_pool',
    'get_next_proxy_from_pool',
    'mark_proxy_failed_in_pool',
    'check_proxy',
    'get_proxy_status_emoji'
]

Z = COLOR_RED
F = COLOR_GREEN
ORANGE = COLOR_ORANGE
RESET = COLOR_RESET

# Module-level proxy pool state
proxy_pool = {
    "proxies": [],  # List of proxy URLs
    "current_index": 0,
    "failed_proxies": set(),  # Track temporarily failed proxies
    "last_rotation": 0
}

# Global proxy status
proxy_status = {"live": False, "checked": False}


def init_proxy_pool():
    """Initialize proxy pool from environment variables"""
    proxies = []
    
    # Add main proxy
    main_proxy = os.environ.get('PROXY_HTTP') or os.environ.get('PROXY_HTTPS')
    if main_proxy:
        proxies.append(main_proxy)
    
    # Add residential proxy
    residential = os.environ.get('RESIDENTIAL_PROXY')
    if residential:
        proxies.append(residential)
    
    # Add additional proxies (PROXY_1, PROXY_2, etc.)
    for i in range(1, 6):
        proxy = os.environ.get(f'PROXY_{i}')
        if proxy:
            proxies.append(proxy)
    
    proxy_pool["proxies"] = list(set(proxies))  # Remove duplicates
    print(f"[*] Proxy pool initialized with {len(proxy_pool['proxies'])} proxies")


def get_next_proxy_from_pool():
    """Get next proxy from pool with rotation and failover"""
    if not proxy_pool["proxies"]:
        return PROXY
    
    available = [p for p in proxy_pool["proxies"] if p not in proxy_pool["failed_proxies"]]
    if not available:
        # Reset failed proxies if all are marked failed
        proxy_pool["failed_proxies"].clear()
        available = proxy_pool["proxies"]
    
    if not available:
        return PROXY
    
    # Round-robin rotation
    idx = proxy_pool["current_index"] % len(available)
    proxy_pool["current_index"] += 1
    
    proxy_url = available[idx]
    return {'http': proxy_url, 'https': proxy_url}


def mark_proxy_failed_in_pool(proxy_url):
    """Mark a proxy as temporarily failed"""
    if proxy_url:
        proxy_pool["failed_proxies"].add(proxy_url)


def check_proxy():
    """Check if proxy is working with auto-reconnection support"""
    global proxy_status
    from gates.utilities import check_proxy_health, get_proxy, mark_proxy_success, mark_proxy_failure
    
    # Get proxy with auto-reconnection
    proxy_dict = get_proxy(force_check=True)
    
    # Check health
    is_alive, ip = check_proxy_health(proxy_dict, timeout=10)
    
    if is_alive:
        mark_proxy_success()
        proxy_status["live"] = True
        proxy_status["checked"] = True
        proxy_status["ip"] = ip
        print(f"{F}[✓] Proxy is LIVE - IP: {ip}{RESET}")
        return True
    else:
        # Try reconnection (wait and retry)
        print(f"{ORANGE}[!] Proxy not responding, attempting reconnection...{RESET}")
        time.sleep(2)
        is_alive, ip = check_proxy_health(proxy_dict, timeout=10)
        
        if is_alive:
            mark_proxy_success()
            proxy_status["live"] = True
            proxy_status["checked"] = True
            proxy_status["ip"] = ip
            print(f"{F}[✓] Proxy reconnected - IP: {ip}{RESET}")
            return True
        else:
            mark_proxy_failure()
            proxy_status["live"] = False
            proxy_status["checked"] = True
            print(f"{Z}[✗] Proxy is DEAD - Reconnection failed{RESET}")
            return False


def get_proxy_status_emoji():
    """Return emoji based on proxy status"""
    if not proxy_status["checked"]:
        return "⚪ Proxy: Not Checked"
    return "🟢 Proxy: Live" if proxy_status["live"] else "🔴 Proxy: Dead"
