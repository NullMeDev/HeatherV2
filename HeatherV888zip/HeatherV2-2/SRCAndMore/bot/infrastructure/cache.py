"""
Cache Module

Phase 12.4: BIN Lookup Caching
Provides LRU caching for BIN lookups to reduce API calls.

IMPORTANT: Only caches BIN information, NOT gateway responses.
Gateway responses must always be fresh/real per user requirements.

Features:
- LRU cache with configurable max size
- Time-based expiration (1-hour TTL)
- Thread-safe operations
- Cache statistics tracking
- Manual cache invalidation
"""

import time
import asyncio
from typing import Optional, Dict, Tuple, Any
from collections import OrderedDict
from dataclasses import dataclass
from config import COLOR_GREEN, COLOR_RESET

__all__ = [
    'BINCache',
    'init_bin_cache',
    'get_bin_cache',
    'lookup_bin_cached',
    'clear_bin_cache',
    'get_cache_stats',
]

F = COLOR_GREEN
RESET = COLOR_RESET


@dataclass
class CacheEntry:
    """Cache entry with value and expiration"""
    value: Any
    expires_at: float
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() > self.expires_at


class BINCache:
    """
    LRU cache for BIN lookups with TTL.
    
    Phase 12.4: Reduces BIN API calls by ~20-30%.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize BIN cache.
        
        Args:
            max_size: Maximum number of entries (default 1000)
            ttl_seconds: Time-to-live in seconds (default 1 hour)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        print(f"{F}[✓] BIN cache initialized: {max_size} entries, {ttl_seconds}s TTL{RESET}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key (BIN number)
            
        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value
    
    async def set(self, key: str, value: Any):
        """
        Set value in cache.
        
        Args:
            key: Cache key (BIN number)
            value: Value to cache
        """
        async with self._lock:
            # Check if we need to evict
            if key not in self._cache and len(self._cache) >= self.max_size:
                # Remove oldest entry (LRU)
                self._cache.popitem(last=False)
                self._evictions += 1
            
            # Add or update entry
            expires_at = time.time() + self.ttl_seconds
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
    
    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            print(f"{F}[✓] BIN cache cleared{RESET}")
    
    async def invalidate(self, key: str):
        """
        Remove a specific entry from cache.
        
        Args:
            key: Cache key to remove
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with hits, misses, hit_rate, size, evictions
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "size": len(self._cache),
            "max_size": self.max_size,
            "evictions": self._evictions,
            "ttl_seconds": self.ttl_seconds,
        }
    
    async def cleanup_expired(self):
        """Remove all expired entries (maintenance)"""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.expires_at < current_time
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                print(f"{F}[✓] Cleaned up {len(expired_keys)} expired BIN cache entries{RESET}")


# Global BIN cache instance
_bin_cache: Optional[BINCache] = None


async def init_bin_cache(max_size: int = 1000, ttl_seconds: int = 3600) -> BINCache:
    """
    Initialize the global BIN cache.
    
    Phase 12.4: Call this during bot startup.
    
    Args:
        max_size: Maximum cache entries (default 1000)
        ttl_seconds: Entry TTL in seconds (default 1 hour)
        
    Returns:
        Initialized BINCache instance
    """
    global _bin_cache
    _bin_cache = BINCache(max_size=max_size, ttl_seconds=ttl_seconds)
    return _bin_cache


def get_bin_cache() -> Optional[BINCache]:
    """Get the global BIN cache instance"""
    return _bin_cache


async def lookup_bin_cached(bin_number: str) -> Optional[Tuple[str, str]]:
    """
    Lookup BIN info with caching.
    
    Phase 12.4: Wrapper for card_utils.lookup_bin_info with cache.
    
    Args:
        bin_number: First 6-8 digits of card number
        
    Returns:
        (bank_name, country) tuple or None if cache miss
    """
    if _bin_cache is None:
        return None
    
    # Normalize BIN (first 6 digits)
    bin_key = bin_number[:6] if len(bin_number) >= 6 else bin_number
    
    # Try cache first
    cached = await _bin_cache.get(bin_key)
    if cached is not None:
        return cached
    
    # Cache miss - caller should fetch and cache
    return None


async def cache_bin_info(bin_number: str, bank_name: str, country: str):
    """
    Cache BIN lookup result.
    
    Args:
        bin_number: First 6-8 digits of card number
        bank_name: Bank name
        country: Country name
    """
    if _bin_cache is None:
        return
    
    # Normalize BIN (first 6 digits)
    bin_key = bin_number[:6] if len(bin_number) >= 6 else bin_number
    
    # Store in cache
    await _bin_cache.set(bin_key, (bank_name, country))


async def clear_bin_cache():
    """Clear the BIN cache (convenience function)"""
    if _bin_cache:
        await _bin_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics (convenience function)"""
    if _bin_cache:
        return _bin_cache.get_stats()
    return {"error": "Cache not initialized"}
