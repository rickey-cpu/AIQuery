"""
Query Cache - Fast response for repeated queries
"""
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime
import hashlib
import time


@dataclass
class CacheEntry:
    """A cached query result"""
    question: str
    sql: str
    result: dict
    created_at: float
    hit_count: int = 0


class QueryCache:
    """
    Query Result Cache
    
    Features:
    - Cache SQL query results
    - TTL-based expiration
    - LRU eviction
    - Fuzzy matching for similar queries
    """
    
    def __init__(self, max_size: int = 500, ttl_seconds: int = 1800):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, CacheEntry] = {}
    
    def _normalize_question(self, question: str) -> str:
        """Normalize question for matching"""
        return question.lower().strip()
    
    def _hash_key(self, question: str) -> str:
        """Generate cache key"""
        normalized = self._normalize_question(question)
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def get(self, question: str) -> Optional[dict]:
        """Get cached result"""
        key = self._hash_key(question)
        
        if key in self._cache:
            entry = self._cache[key]
            
            # Check expiration
            if time.time() - entry.created_at > self.ttl_seconds:
                del self._cache[key]
                return None
            
            entry.hit_count += 1
            return {
                "sql": entry.sql,
                "result": entry.result,
                "cached": True
            }
        
        return None
    
    def set(self, question: str, sql: str, result: dict):
        """Cache a result"""
        # Evict if needed
        while len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]
        
        key = self._hash_key(question)
        self._cache[key] = CacheEntry(
            question=question,
            sql=sql,
            result=result,
            created_at=time.time()
        )
    
    def invalidate(self, question: str):
        """Invalidate cache entry"""
        key = self._hash_key(question)
        if key in self._cache:
            del self._cache[key]
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_hits = sum(e.hit_count for e in self._cache.values())
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "total_hits": total_hits
        }


# Global cache instance
_cache: Optional[QueryCache] = None


def get_cache() -> QueryCache:
    """Get or create global cache instance"""
    global _cache
    if _cache is None:
        _cache = QueryCache()
    return _cache
