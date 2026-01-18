"""
HTTP Client Module

Provides HTTP session setup with proxy support, retry logic, and randomized headers.

Phase 12.1: Updated to support both legacy requests and modern httpx with session pooling.
"""

import random
import requests
import httpx
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from faker import Faker
from user_agent import generate_user_agent
from typing import Optional, Tuple

__all__ = [
    'create_session',
    'get_random_headers',
    'create_async_client',
]


def create_session(proxy_dict=None):
    """
    Initialize HTTP session with user agent, faker, and retry logic.
    
    Args:
        proxy_dict: Optional proxy configuration dict (e.g., {"http": "...", "https": "..."})
    
    Returns:
        Tuple of (user_agent_string, requests.Session, Faker instance)
    """
    us = generate_user_agent()
    r = requests.Session()
    
    if proxy_dict:
        r.proxies = proxy_dict
    r.verify = False  # Skip SSL verification for proxy
    
    # Add retry strategy for failed requests
    retry_strategy = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    r.mount("http://", adapter)
    r.mount("https://", adapter)
    
    fake = Faker()
    return us, r, fake


def get_random_headers(user_agent):
    """Generate randomized headers for each request"""
    return {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': random.choice([
            'en-US,en;q=0.9',
            'en-GB,en;q=0.8',
            'en;q=0.7'
        ]),
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }


def create_async_client(
    proxy_url: Optional[str] = None,
    timeout: int = 22,
    max_connections: int = 50,
    max_keepalive: int = 10,
) -> httpx.AsyncClient:
    """
    Create an httpx AsyncClient with optimal settings.
    
    Phase 12.1: Provides high-performance async HTTP client.
    Use with session_pool for connection reuse.
    
    Args:
        proxy_url: Optional proxy URL
        timeout: Request timeout in seconds
        max_connections: Maximum total connections
        max_keepalive: Maximum keepalive connections
        
    Returns:
        Configured httpx.AsyncClient
    """
    limits = httpx.Limits(
        max_keepalive_connections=max_keepalive,
        max_connections=max_connections,
        keepalive_expiry=30.0,
    )
    
    timeout_config = httpx.Timeout(
        timeout=timeout,
        connect=5.0,
        read=timeout,
        write=5.0,
        pool=2.0,
    )
    
    proxies = None
    if proxy_url:
        proxies = {
            "http://": proxy_url,
            "https://": proxy_url,
        }
    
    return httpx.AsyncClient(
        limits=limits,
        timeout=timeout_config,
        proxies=proxies,
        verify=False,
        follow_redirects=True,
        http2=True,  # Enable HTTP/2 for better performance
    )
