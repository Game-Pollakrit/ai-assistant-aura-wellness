"""Redis cache and rate limiting service."""
import redis.asyncio as redis
import hashlib
import json
from typing import Optional, Dict, Any, List
from config import settings


class CacheService:
    """Redis cache manager."""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis."""
        self.redis = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
    
    def _generate_cache_key(
        self,
        tenant_id: str,
        question: str,
        chunk_ids: List[str]
    ) -> str:
        """Generate cache key for LLM response."""
        content = f"{tenant_id}:{question}:{':'.join(sorted(chunk_ids))}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()
        return f"cache:llm:{hash_value}"
    
    async def get_cached_response(
        self,
        tenant_id: str,
        question: str,
        chunk_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get cached LLM response."""
        key = self._generate_cache_key(tenant_id, question, chunk_ids)
        cached = await self.redis.get(key)
        
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_response(
        self,
        tenant_id: str,
        question: str,
        chunk_ids: List[str],
        response: Dict[str, Any],
        ttl: int = None
    ):
        """Cache LLM response."""
        # Don't cache low-quality responses
        if response.get('confidence', 0) < 0.7:
            return
        
        if response.get('insufficient_context'):
            return
        
        # Don't cache time-sensitive or personal queries
        time_keywords = ['today', 'now', 'current', 'latest', 'deadline']
        personal_keywords = ['my', 'i ', 'me ', 'mine']
        
        question_lower = question.lower()
        if any(kw in question_lower for kw in time_keywords + personal_keywords):
            return
        
        key = self._generate_cache_key(tenant_id, question, chunk_ids)
        ttl = ttl or settings.cache_ttl_seconds
        
        await self.redis.setex(
            key,
            ttl,
            json.dumps(response)
        )
    
    async def check_rate_limit(
        self,
        tenant_id: str,
        operation: str = "query"
    ) -> bool:
        """Check if tenant is within rate limit."""
        import time
        current_minute = int(time.time() / 60)
        key = f"ratelimit:{tenant_id}:{operation}:{current_minute}"
        
        count = await self.redis.incr(key)
        
        if count == 1:
            await self.redis.expire(key, 60)
        
        limit = settings.queries_per_minute
        
        if count > limit:
            return False
        
        return True
    
    async def invalidate_document_cache(
        self,
        tenant_id: str,
        document_id: str
    ):
        """Invalidate cached responses for a document."""
        # In production, would track which cache keys use which documents
        # For MVP, we'll let cache expire naturally
        pass


# Global cache service instance
cache_service = CacheService()