import logging
from django.core.cache import cache
from typing import Any, Optional

logger = logging.getLogger(__name__)

def cache_response(key: str, value: Any, ttl: int = 3600) -> None:
    """
    Cache a response value.
    
    Args:
        key: The cache key string.
        value: The value to cache (must be serializable).
        ttl: Time to live in seconds (default 3600s / 1 hour).
    """
    try:
        cache.set(key, value, timeout=ttl)
    except Exception as e:
        logger.error(f"Failed to cache value for key {key}: {e}")

def get_cached_response(key: str) -> Optional[Any]:
    """
    Retrieve a cached response.
    
    Args:
        key: The cache key string.
        
    Returns:
        The cached value or None if not found/error.
    """
    try:
        return cache.get(key)
    except Exception as e:
        logger.error(f"Failed to retrieve cache for key {key}: {e}")
        return None

def clear_cache(key: str) -> None:
    """
    Delete a cache entry.
    
    Args:
        key: The cache key string.
    """
    try:
        cache.delete(key)
    except Exception as e:
        logger.error(f"Failed to clear cache for key {key}: {e}")
