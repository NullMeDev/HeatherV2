"""
Enhanced Connection Retry Logic
Handles connection errors, disconnects, and rate limits with intelligent retry.
"""

import time
import random
import asyncio
from functools import wraps
from typing import Callable, Any, Optional, Tuple

CONNECTION_ERROR_PATTERNS = [
    "server disconnected without sending a response",
    "peer closed connection without sending complete message body",
    "incomplete chunked read",
    "connection error",
    "connection reset",
    "connection refused",
    "connection timed out",
    "read timeout",
    "write timeout",
    "ssl handshake failed",
    "certificate verify failed",
    "name resolution failed",
    "no route to host",
    "network is unreachable",
    "temporary failure in name resolution",
    "getaddrinfo failed",
]

RATE_LIMIT_PATTERNS = [
    "rate limit",
    "too many requests",
    "429",
    "throttled",
    "slow down",
    "try again later",
]

RETRY_STATUS_CODES = [429, 500, 502, 503, 504, 520, 521, 522, 523, 524]


def is_connection_error(error_text: str) -> bool:
    """
    Check if error is a connection-related error that should trigger retry.
    """
    if not error_text:
        return False
    
    error_lower = str(error_text).lower()
    return any(pattern in error_lower for pattern in CONNECTION_ERROR_PATTERNS)


def is_rate_limit_error(error_text: str) -> bool:
    """
    Check if error indicates rate limiting.
    """
    if not error_text:
        return False
    
    error_lower = str(error_text).lower()
    return any(pattern in error_lower for pattern in RATE_LIMIT_PATTERNS)


def should_retry_status_code(status_code: int) -> bool:
    """
    Check if HTTP status code should trigger retry.
    """
    return status_code in RETRY_STATUS_CODES


def get_retry_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 10.0) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: Current attempt number (1-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    
    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    jitter = random.uniform(0, delay * 0.3)
    return delay + jitter


def sync_retry_request(
    func: Callable,
    max_retries: int = 3,
    retry_on_status: bool = True,
    on_retry: Optional[Callable[[int, str], None]] = None
) -> Callable:
    """
    Decorator for synchronous functions with retry logic.
    
    Args:
        func: Function to wrap
        max_retries: Maximum number of retries
        retry_on_status: Whether to retry on certain HTTP status codes
        on_retry: Optional callback called on each retry with (attempt, error_message)
    
    Returns:
        Wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                if retry_on_status and hasattr(result, 'status_code'):
                    if should_retry_status_code(result.status_code):
                        error_msg = f"HTTP {result.status_code}"
                        if attempt < max_retries:
                            delay = get_retry_delay(attempt)
                            if on_retry:
                                on_retry(attempt, error_msg)
                            time.sleep(delay)
                            continue
                
                return result
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                if is_connection_error(error_str) or is_rate_limit_error(error_str):
                    if attempt < max_retries:
                        delay = get_retry_delay(attempt)
                        if on_retry:
                            on_retry(attempt, error_str[:100])
                        time.sleep(delay)
                        continue
                
                raise
        
        if last_error:
            raise last_error
        return None
    
    return wrapper


async def async_retry_request(
    coro_func: Callable,
    *args,
    max_retries: int = 3,
    retry_on_status: bool = True,
    on_retry: Optional[Callable[[int, str], None]] = None,
    **kwargs
) -> Any:
    """
    Execute an async function with retry logic.
    
    Args:
        coro_func: Async function to call
        *args: Arguments to pass to function
        max_retries: Maximum number of retries
        retry_on_status: Whether to retry on certain HTTP status codes
        on_retry: Optional callback called on each retry
        **kwargs: Keyword arguments to pass to function
    
    Returns:
        Result of the function call
    """
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            result = await coro_func(*args, **kwargs)
            
            if retry_on_status and hasattr(result, 'status_code'):
                if should_retry_status_code(result.status_code):
                    error_msg = f"HTTP {result.status_code}"
                    if attempt < max_retries:
                        delay = get_retry_delay(attempt)
                        if on_retry:
                            on_retry(attempt, error_msg)
                        await asyncio.sleep(delay)
                        continue
            
            return result
            
        except Exception as e:
            last_error = e
            error_str = str(e)
            
            if is_connection_error(error_str) or is_rate_limit_error(error_str):
                if attempt < max_retries:
                    delay = get_retry_delay(attempt)
                    if on_retry:
                        on_retry(attempt, error_str[:100])
                    await asyncio.sleep(delay)
                    continue
            
            raise
    
    if last_error:
        raise last_error
    return None


class RetrySession:
    """
    Wrapper for requests.Session with automatic retry on connection errors.
    """
    
    def __init__(self, session, max_retries: int = 3):
        self.session = session
        self.max_retries = max_retries
        self.retry_count = 0
    
    def _make_request(self, method: str, url: str, **kwargs) -> Any:
        """
        Make request with retry logic.
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                self.retry_count = attempt - 1
                
                if method.lower() == "get":
                    resp = self.session.get(url, **kwargs)
                elif method.lower() == "post":
                    resp = self.session.post(url, **kwargs)
                elif method.lower() == "put":
                    resp = self.session.put(url, **kwargs)
                elif method.lower() == "delete":
                    resp = self.session.delete(url, **kwargs)
                else:
                    resp = self.session.request(method, url, **kwargs)
                
                if should_retry_status_code(resp.status_code):
                    if attempt < self.max_retries:
                        delay = get_retry_delay(attempt)
                        time.sleep(delay)
                        continue
                
                return resp
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                if is_connection_error(error_str) or is_rate_limit_error(error_str):
                    if attempt < self.max_retries:
                        delay = get_retry_delay(attempt)
                        time.sleep(delay)
                        continue
                
                raise
        
        if last_error:
            raise last_error
        return None
    
    def get(self, url: str, **kwargs):
        return self._make_request("get", url, **kwargs)
    
    def post(self, url: str, **kwargs):
        return self._make_request("post", url, **kwargs)
    
    def put(self, url: str, **kwargs):
        return self._make_request("put", url, **kwargs)
    
    def delete(self, url: str, **kwargs):
        return self._make_request("delete", url, **kwargs)
    
    @property
    def cookies(self):
        return self.session.cookies
    
    @property
    def headers(self):
        return self.session.headers
    
    @property
    def proxies(self):
        return self.session.proxies
    
    def close(self):
        self.session.close()


def with_retry(max_retries: int = 3):
    """
    Decorator factory for adding retry logic to functions.
    
    Usage:
        @with_retry(max_retries=3)
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    
                    if is_connection_error(error_str) or is_rate_limit_error(error_str):
                        if attempt < max_retries:
                            delay = get_retry_delay(attempt)
                            time.sleep(delay)
                            continue
                    
                    raise
            
            if last_error:
                raise last_error
            return None
        
        return wrapper
    return decorator
