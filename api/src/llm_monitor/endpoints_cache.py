"""Endpoints cache manager for storing and retrieving LLM endpoint data"""
import asyncio
from typing import Dict, Any
from loguru import logger


class EndpointsCache:
    """
    Thread-safe cache for storing LLM endpoints data.
    
    This cache is populated by a background task and read by the /llmm endpoint
    to avoid redundant queries to Ollama hosts when multiple clients are polling.
    """
    
    def __init__(self):
        """Initialize the cache with empty data and an async lock"""
        self._cache: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        logger.info("EndpointsCache initialized")
    
    async def get_endpoints(self) -> Dict[str, Any]:
        """
        Get cached endpoints data.
        
        Returns:
            Dictionary of cached endpoint data (empty dict if not yet populated)
        """
        async with self._lock:
            return self._cache.copy()
    
    async def update_endpoints(self, endpoints: Dict[str, Any]) -> None:
        """
        Update the cache with new endpoint data.
        
        Args:
            endpoints: Dictionary of endpoint data to cache
        """
        async with self._lock:
            self._cache = endpoints
            logger.debug(f"Cache updated with {len(endpoints)} endpoint(s)")


# Global cache instance
_endpoints_cache: EndpointsCache | None = None


def get_endpoints_cache() -> EndpointsCache:
    """
    Get or create the global endpoints cache instance.
    
    Returns:
        Global EndpointsCache instance
    """
    global _endpoints_cache
    if _endpoints_cache is None:
        _endpoints_cache = EndpointsCache()
    return _endpoints_cache
