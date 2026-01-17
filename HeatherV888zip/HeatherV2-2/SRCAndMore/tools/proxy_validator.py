"""
Proxy Quality Validator
Validates proxy quality by checking:
- Connection success
- IP rotation (rotating vs static)
- Response time
- Geographic location
"""

import re
import time
import asyncio
from typing import Tuple, Optional, Dict
from dataclasses import dataclass

import requests
import aiohttp

IP_CHECK_URLS = [
    "https://ipinfo.io/json",
    "https://api.ipify.org?format=json",
    "https://httpbin.org/ip",
]

PROXY_TIMEOUT = 10


@dataclass
class ProxyValidationResult:
    """Result of proxy validation."""
    is_valid: bool
    is_rotating: bool
    ip1: Optional[str]
    ip2: Optional[str]
    response_time: float
    country: Optional[str]
    error: Optional[str]
    quality_score: int
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "is_rotating": self.is_rotating,
            "ip1": self.ip1,
            "ip2": self.ip2,
            "response_time_ms": round(self.response_time * 1000),
            "country": self.country,
            "error": self.error,
            "quality_score": self.quality_score,
        }


def normalize_proxy(proxy_raw: str) -> Optional[str]:
    """
    Normalize proxy string to standard HTTP URL format.
    
    Supports formats:
    - http://user:pass@host:port
    - https://user:pass@host:port
    - user:pass@host:port
    - host:port:user:pass
    - host:port
    
    Returns:
        Normalized proxy URL or None if invalid
    """
    if not proxy_raw:
        return None
    
    proxy_raw = proxy_raw.strip()
    
    if proxy_raw.startswith("http://") or proxy_raw.startswith("https://"):
        return proxy_raw
    
    match_at = re.fullmatch(r"(.+?):(.+?)@([a-zA-Z0-9.\-]+):(\d+)", proxy_raw)
    if match_at:
        user, pwd, host, port = match_at.groups()
        return f"http://{user}:{pwd}@{host}:{port}"
    
    match_colon = re.fullmatch(r"([a-zA-Z0-9.\-]+):(\d+):(.+?):(.+)", proxy_raw)
    if match_colon:
        host, port, user, pwd = match_colon.groups()
        return f"http://{user}:{pwd}@{host}:{port}"
    
    match_simple = re.fullmatch(r"([a-zA-Z0-9.\-]+):(\d+)", proxy_raw)
    if match_simple:
        host, port = match_simple.groups()
        return f"http://{host}:{port}"
    
    return None


def get_proxy_dict(proxy_url: str) -> Dict[str, str]:
    """
    Convert proxy URL to requests-compatible proxy dict.
    """
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def _get_ip_sync(proxy_url: str, timeout: int = PROXY_TIMEOUT) -> Tuple[Optional[str], Optional[str], float]:
    """
    Get IP address through proxy (synchronous).
    
    Returns:
        Tuple of (ip, country, response_time) or (None, None, 0) on failure
    """
    proxies = get_proxy_dict(proxy_url)
    
    for check_url in IP_CHECK_URLS:
        try:
            start = time.time()
            resp = requests.get(
                check_url,
                proxies=proxies,
                timeout=timeout,
                verify=False
            )
            elapsed = time.time() - start
            
            if resp.status_code == 200:
                data = resp.json()
                ip = data.get("ip") or data.get("origin")
                country = data.get("country")
                return ip, country, elapsed
        except Exception:
            continue
    
    return None, None, 0


async def _get_ip_async(proxy_url: str, timeout: int = PROXY_TIMEOUT) -> Tuple[Optional[str], Optional[str], float]:
    """
    Get IP address through proxy (asynchronous).
    
    Returns:
        Tuple of (ip, country, response_time) or (None, None, 0) on failure
    """
    connector = aiohttp.TCPConnector(ssl=False)
    
    for check_url in IP_CHECK_URLS:
        try:
            start = time.time()
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    check_url,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    elapsed = time.time() - start
                    
                    if resp.status == 200:
                        data = await resp.json()
                        ip = data.get("ip") or data.get("origin")
                        country = data.get("country")
                        return ip, country, elapsed
        except Exception:
            continue
    
    return None, None, 0


def validate_proxy_sync(proxy_raw: str, check_rotation: bool = True) -> ProxyValidationResult:
    """
    Validate proxy quality (synchronous).
    
    Args:
        proxy_raw: Proxy string in any supported format
        check_rotation: Whether to check if proxy is rotating (makes 2 requests)
    
    Returns:
        ProxyValidationResult with validation details
    """
    proxy_url = normalize_proxy(proxy_raw)
    
    if not proxy_url:
        return ProxyValidationResult(
            is_valid=False,
            is_rotating=False,
            ip1=None,
            ip2=None,
            response_time=0,
            country=None,
            error="Invalid proxy format",
            quality_score=0
        )
    
    ip1, country, time1 = _get_ip_sync(proxy_url)
    
    if not ip1:
        return ProxyValidationResult(
            is_valid=False,
            is_rotating=False,
            ip1=None,
            ip2=None,
            response_time=0,
            country=None,
            error="Failed to connect through proxy",
            quality_score=0
        )
    
    ip2 = ip1
    is_rotating = False
    
    if check_rotation:
        time.sleep(1)
        ip2, _, time2 = _get_ip_sync(proxy_url)
        
        if ip2 and ip1 != ip2:
            is_rotating = True
    
    quality_score = 50
    if is_rotating:
        quality_score += 30
    if time1 < 2.0:
        quality_score += 10
    if time1 < 1.0:
        quality_score += 10
    
    return ProxyValidationResult(
        is_valid=True,
        is_rotating=is_rotating,
        ip1=ip1,
        ip2=ip2,
        response_time=time1,
        country=country,
        error=None,
        quality_score=quality_score
    )


async def validate_proxy_async(proxy_raw: str, check_rotation: bool = True) -> ProxyValidationResult:
    """
    Validate proxy quality (asynchronous).
    
    Args:
        proxy_raw: Proxy string in any supported format
        check_rotation: Whether to check if proxy is rotating (makes 2 requests)
    
    Returns:
        ProxyValidationResult with validation details
    """
    proxy_url = normalize_proxy(proxy_raw)
    
    if not proxy_url:
        return ProxyValidationResult(
            is_valid=False,
            is_rotating=False,
            ip1=None,
            ip2=None,
            response_time=0,
            country=None,
            error="Invalid proxy format",
            quality_score=0
        )
    
    ip1, country, time1 = await _get_ip_async(proxy_url)
    
    if not ip1:
        return ProxyValidationResult(
            is_valid=False,
            is_rotating=False,
            ip1=None,
            ip2=None,
            response_time=0,
            country=None,
            error="Failed to connect through proxy",
            quality_score=0
        )
    
    ip2 = ip1
    is_rotating = False
    
    if check_rotation:
        await asyncio.sleep(1)
        ip2, _, time2 = await _get_ip_async(proxy_url)
        
        if ip2 and ip1 != ip2:
            is_rotating = True
    
    quality_score = 50
    if is_rotating:
        quality_score += 30
    if time1 < 2.0:
        quality_score += 10
    if time1 < 1.0:
        quality_score += 10
    
    return ProxyValidationResult(
        is_valid=True,
        is_rotating=is_rotating,
        ip1=ip1,
        ip2=ip2,
        response_time=time1,
        country=country,
        error=None,
        quality_score=quality_score
    )


def quick_proxy_check(proxy_raw: str) -> Tuple[bool, Optional[str]]:
    """
    Quick proxy validation without rotation check.
    
    Args:
        proxy_raw: Proxy string
    
    Returns:
        Tuple of (is_working, error_message)
    """
    proxy_url = normalize_proxy(proxy_raw)
    
    if not proxy_url:
        return False, "Invalid proxy format"
    
    ip, _, _ = _get_ip_sync(proxy_url, timeout=5)
    
    if ip:
        return True, None
    else:
        return False, "Connection failed"


def is_residential_proxy(proxy_result: ProxyValidationResult) -> bool:
    """
    Estimate if proxy is likely residential based on characteristics.
    Note: This is a heuristic, not definitive.
    """
    if not proxy_result.is_valid:
        return False
    
    if proxy_result.is_rotating:
        return True
    
    if proxy_result.response_time < 0.5:
        return False
    
    return False
