"""
HTTP Client Module

Provides HTTP session setup with proxy support, retry logic, and randomized headers.
"""

import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from faker import Faker
from user_agent import generate_user_agent

__all__ = [
    'create_session',
    'get_random_headers',
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
