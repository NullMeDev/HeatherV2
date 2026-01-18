"""
Proxy Pool Management Module

Phase 12.2: Async Proxy Management with Health Scoring
Provides async proxy rotation, health monitoring, and smart selection.

Features:
- Async proxy health checks (non-blocking)
- Proxy scoring based on latency and success rate
- Smart proxy selection (best performing first)
- Background health monitoring
- Automatic failover
- Per-proxy statistics tracking

Extracted from transferto.py for modular architecture.
"""

import os
import time
import asyncio
import httpx
from dataclasses import dataclass
from typing import Optional, Dict, List
from config import PROXY, COLOR_RED, COLOR_GREEN, COLOR_ORANGE, COLOR_RESET

__all__ = [
    'AsyncProxyPool',
    'get_proxy_pool',
    'init_async_proxy_pool',
    'get_best_proxy',
    'mark_proxy_result',
    # Legacy sync API (backwards compatible)
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


@dataclass
class ProxyStats:
    """Statistics for a single proxy"""
    url: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    is_healthy: bool = True
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)"""
        if self.total_requests == 0:
            return 0.5  # Neutral for untested proxies
        return self.successful_requests / self.total_requests
    
    @property
    def average_latency(self) -> float:
        """Calculate average latency in seconds"""
        if self.successful_requests == 0:
            return 999.0  # High penalty for failed proxies
        return self.total_latency / self.successful_requests
    
    @property
    def score(self) -> float:
        """
        Calculate proxy score (higher is better).
        Factors: success rate (70%), latency (30%)
        """
        if not self.is_healthy:
            return 0.0
        
        # Success rate component (0-70 points)
        success_score = self.success_rate * 70
        
        # Latency component (0-30 points, inverse)
        # Good latency (<1s) = 30 points, bad latency (>5s) = 0 points
        latency = self.average_latency
        if latency < 1.0:
            latency_score = 30
        elif latency > 5.0:
            latency_score = 0
        else:
            latency_score = 30 * (1 - (latency - 1) / 4)
        
        return success_score + latency_score
    
    def mark_success(self, latency: float):
        """Mark a successful request"""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency += latency
        self.last_success = time.time()
        self.consecutive_failures = 0
        self.is_healthy = True
    
    def mark_failure(self):
        """Mark a failed request"""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_failure = time.time()
        self.consecutive_failures += 1
        
        # Mark unhealthy after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.is_healthy = False


class AsyncProxyPool:
    """
    Async proxy pool with health monitoring and smart selection.
    
    Phase 12.2: Non-blocking proxy operations with scoring.
    """
    
    def __init__(self, check_interval: int = 60):
        self.proxies: List[str] = []
        self.stats: Dict[str, ProxyStats] = {}
        self.check_interval = check_interval
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start background health monitoring"""
        self._monitor_task = asyncio.create_task(self._health_monitor())
        print(f"{F}[✓] Async proxy pool started with health monitoring{RESET}")
    
    async def stop(self):
        """Stop background monitoring"""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    def add_proxy(self, proxy_url: str):
        """Add a proxy to the pool"""
        if proxy_url and proxy_url not in self.proxies:
            self.proxies.append(proxy_url)
            self.stats[proxy_url] = ProxyStats(url=proxy_url)
    
    async def check_proxy_health(self, proxy_url: str, timeout: int = 10) -> tuple[bool, float]:
        """
        Check if proxy is healthy (async).
        
        Returns:
            (is_alive, latency_seconds)
        """
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=timeout,
                verify=False
            ) as client:
                # Test with multiple endpoints for reliability
                test_urls = [
                    "https://api.stripe.com",
                    "https://www.google.com",
                    "https://httpbin.org/ip"
                ]
                
                for url in test_urls:
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            latency = time.time() - start_time
                            return True, latency
                    except:
                        continue
                
                return False, 0.0
                
        except Exception:
            return False, 0.0
    
    async def _health_monitor(self):
        """Background task to monitor proxy health"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Check all proxies
                for proxy_url in self.proxies:
                    is_alive, latency = await self.check_proxy_health(proxy_url, timeout=5)
                    
                    stats = self.stats.get(proxy_url)
                    if stats:
                        if is_alive:
                            # Mark healthy if it was unhealthy
                            if not stats.is_healthy:
                                stats.is_healthy = True
                                stats.consecutive_failures = 0
                                print(f"{F}[✓] Proxy recovered: {proxy_url[:30]}...{RESET}")
                        else:
                            # Don't mark failure from health check, just note it
                            if stats.is_healthy and stats.consecutive_failures == 0:
                                print(f"{ORANGE}[!] Proxy may be degraded: {proxy_url[:30]}...{RESET}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"{Z}[!] Health monitor error: {e}{RESET}")
    
    async def get_best_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get the best performing proxy based on score.
        
        Returns:
            Proxy dict {'http': url, 'https': url} or None
        """
        async with self._lock:
            if not self.proxies:
                return None
            
            # Get healthy proxies sorted by score
            healthy = [
                (url, self.stats[url])
                for url in self.proxies
                if self.stats[url].is_healthy
            ]
            
            if not healthy:
                # Reset all proxies if none are healthy
                for stats in self.stats.values():
                    stats.is_healthy = True
                    stats.consecutive_failures = 0
                healthy = [(url, self.stats[url]) for url in self.proxies]
            
            if not healthy:
                return None
            
            # Sort by score (highest first)
            healthy.sort(key=lambda x: x[1].score, reverse=True)
            
            best_url = healthy[0][0]
            return {"http": best_url, "https": best_url}
    
    async def mark_result(self, proxy_url: str, success: bool, latency: float = 0.0):
        """Mark the result of a proxy request"""
        async with self._lock:
            stats = self.stats.get(proxy_url)
            if stats:
                if success:
                    stats.mark_success(latency)
                else:
                    stats.mark_failure()
    
    def get_stats_summary(self) -> Dict:
        """Get summary of all proxy statistics"""
        return {
            "total_proxies": len(self.proxies),
            "healthy_proxies": sum(1 for s in self.stats.values() if s.is_healthy),
            "proxies": [
                {
                    "url": url[:30] + "...",
                    "score": round(self.stats[url].score, 2),
                    "success_rate": round(self.stats[url].success_rate * 100, 1),
                    "avg_latency": round(self.stats[url].average_latency, 2),
                    "total_requests": self.stats[url].total_requests,
                    "healthy": self.stats[url].is_healthy,
                }
                for url in self.proxies
            ]
        }


# Global async proxy pool instance
_async_proxy_pool: Optional[AsyncProxyPool] = None


async def init_async_proxy_pool(check_interval: int = 60) -> AsyncProxyPool:
    """
    Initialize async proxy pool with health monitoring.
    
    Phase 12.2: Replaces sync proxy pool for better performance.
    """
    global _async_proxy_pool
    
    if _async_proxy_pool:
        await _async_proxy_pool.stop()
    
    _async_proxy_pool = AsyncProxyPool(check_interval=check_interval)
    
    # Add proxies from environment
    main_proxy = os.environ.get('PROXY_HTTP') or os.environ.get('PROXY_HTTPS')
    if main_proxy:
        _async_proxy_pool.add_proxy(main_proxy)
    
    residential = os.environ.get('RESIDENTIAL_PROXY')
    if residential:
        _async_proxy_pool.add_proxy(residential)
    
    for i in range(1, 6):
        proxy = os.environ.get(f'PROXY_{i}')
        if proxy:
            _async_proxy_pool.add_proxy(proxy)
    
    await _async_proxy_pool.start()
    
    print(f"{F}[✓] Async proxy pool initialized with {len(_async_proxy_pool.proxies)} proxies{RESET}")
    return _async_proxy_pool


def get_proxy_pool() -> Optional[AsyncProxyPool]:
    """Get the global async proxy pool"""
    return _async_proxy_pool


async def get_best_proxy() -> Optional[Dict[str, str]]:
    """Get the best performing proxy (convenience function)"""
    if _async_proxy_pool:
        return await _async_proxy_pool.get_best_proxy()
    return None


async def mark_proxy_result(proxy_url: str, success: bool, latency: float = 0.0):
    """Mark proxy request result (convenience function)"""
    if _async_proxy_pool and proxy_url:
        await _async_proxy_pool.mark_result(proxy_url, success, latency)


# ============================================================================
# LEGACY SYNC API (Backwards Compatibility)
# ============================================================================

# Module-level proxy pool state (legacy)
proxy_pool = {
    "proxies": [],  # List of proxy URLs
    "current_index": 0,
    "failed_proxies": set(),  # Track temporarily failed proxies
    "last_rotation": 0
}

# Global proxy status (legacy)
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
