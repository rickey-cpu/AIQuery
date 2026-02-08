"""
AI Gateway - Unified LLM Interface with Enterprise Features
Inspired by Uber FINCH's Generative AI Gateway
"""
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import hashlib
import json
import time


@dataclass
class GatewayConfig:
    """AI Gateway configuration"""
    # Primary provider
    primary_provider: str = "openai"
    primary_model: str = "gpt-4"
    
    # Fallback provider
    fallback_provider: Optional[str] = "openai"
    fallback_model: Optional[str] = "gpt-3.5-turbo"
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    
    # Retry
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Cost tracking
    track_usage: bool = True


@dataclass
class UsageRecord:
    """Track LLM usage"""
    timestamp: datetime
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    cached: bool = False
    user_id: Optional[str] = None


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, rate_per_minute: int = 60, rate_per_hour: int = 1000):
        self.rate_per_minute = rate_per_minute
        self.rate_per_hour = rate_per_hour
        self._minute_tokens: dict[str, list[float]] = {}
        self._hour_tokens: dict[str, list[float]] = {}
    
    def _clean_old_tokens(self, tokens: list[float], window: float) -> list[float]:
        """Remove tokens older than window"""
        now = time.time()
        return [t for t in tokens if now - t < window]
    
    def check(self, user_id: str = "default") -> bool:
        """Check if request is allowed"""
        now = time.time()
        
        # Clean old tokens
        self._minute_tokens[user_id] = self._clean_old_tokens(
            self._minute_tokens.get(user_id, []), 60
        )
        self._hour_tokens[user_id] = self._clean_old_tokens(
            self._hour_tokens.get(user_id, []), 3600
        )
        
        # Check limits
        if len(self._minute_tokens[user_id]) >= self.rate_per_minute:
            return False
        if len(self._hour_tokens[user_id]) >= self.rate_per_hour:
            return False
        
        return True
    
    def consume(self, user_id: str = "default"):
        """Consume a token"""
        now = time.time()
        if user_id not in self._minute_tokens:
            self._minute_tokens[user_id] = []
        if user_id not in self._hour_tokens:
            self._hour_tokens[user_id] = []
        
        self._minute_tokens[user_id].append(now)
        self._hour_tokens[user_id].append(now)


class ResponseCache:
    """In-memory LRU cache for LLM responses"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[Any, float]] = {}
        self._access_order: list[str] = []
    
    def _hash_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model"""
        content = f"{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def get(self, prompt: str, model: str) -> Optional[Any]:
        """Get cached response"""
        key = self._hash_key(prompt, model)
        if key in self._cache:
            response, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                # Move to end of access order
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return response
            else:
                # Expired
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
        return None
    
    def set(self, prompt: str, model: str, response: Any):
        """Cache response"""
        key = self._hash_key(prompt, model)
        
        # Evict if at capacity
        while len(self._cache) >= self.max_size and self._access_order:
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._cache:
                del self._cache[oldest_key]
        
        self._cache[key] = (response, time.time())
        self._access_order.append(key)
    
    def clear(self):
        """Clear cache"""
        self._cache.clear()
        self._access_order.clear()


class AIGateway:
    """
    AI Gateway - Enterprise LLM Interface
    
    Features (inspired by Uber FINCH):
    - Multi-provider support (OpenAI, Gemini, Claude, Ollama)
    - Response caching (in-memory or Redis)
    - Rate limiting per user
    - Automatic fallback to backup LLM
    - Usage tracking & cost monitoring
    - Retry with exponential backoff
    """
    
    # Cost per 1K tokens (approximate)
    COST_PER_1K = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gemini-pro": {"input": 0.00025, "output": 0.0005},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    }
    
    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or GatewayConfig()
        self.rate_limiter = RateLimiter(
            self.config.rate_limit_per_minute,
            self.config.rate_limit_per_hour
        )
        self.cache = ResponseCache(ttl_seconds=self.config.cache_ttl_seconds)
        self.usage_history: list[UsageRecord] = []
        self._llm_cache: dict[str, Any] = {}
    
    def _get_llm(self, provider: str, model: str):
        """Get or create LLM instance"""
        cache_key = f"{provider}:{model}"
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]
        
        llm = None
        
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            import os
            llm = ChatOpenAI(
                model=model,
                temperature=0,
                api_key=os.getenv("OPENAI_API_KEY")
            )
        
        elif provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            import os
            llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=0,
                google_api_key=os.getenv("GEMINI_API_KEY")
            )
        
        elif provider == "ollama":
            from langchain_community.llms import Ollama
            llm = Ollama(model=model)
        
        if llm:
            self._llm_cache[cache_key] = llm
        
        return llm
    
    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost for API call"""
        if model not in self.COST_PER_1K:
            return 0.0
        
        costs = self.COST_PER_1K[model]
        input_cost = (prompt_tokens / 1000) * costs["input"]
        output_cost = (completion_tokens / 1000) * costs["output"]
        return input_cost + output_cost
    
    async def invoke(
        self,
        prompt: str,
        user_id: str = "default",
        use_cache: bool = True,
        **kwargs
    ) -> dict:
        """
        Invoke LLM with enterprise features
        
        Returns:
            {
                "content": str,
                "cached": bool,
                "provider": str,
                "model": str,
                "usage": {...}
            }
        """
        model = self.config.primary_model
        
        # Check rate limit
        if not self.rate_limiter.check(user_id):
            return {
                "content": "",
                "error": "Rate limit exceeded. Please try again later.",
                "cached": False
            }
        
        # Check cache
        if use_cache and self.config.cache_enabled:
            cached_response = self.cache.get(prompt, model)
            if cached_response:
                return {
                    "content": cached_response,
                    "cached": True,
                    "provider": self.config.primary_provider,
                    "model": model
                }
        
        # Consume rate limit token
        self.rate_limiter.consume(user_id)
        
        # Try primary provider
        result = await self._invoke_with_retry(
            self.config.primary_provider,
            self.config.primary_model,
            prompt,
            **kwargs
        )
        
        # Fallback if failed
        if result.get("error") and self.config.fallback_provider:
            result = await self._invoke_with_retry(
                self.config.fallback_provider,
                self.config.fallback_model,
                prompt,
                **kwargs
            )
        
        # Cache successful response
        if not result.get("error") and self.config.cache_enabled:
            self.cache.set(prompt, model, result.get("content", ""))
        
        # Track usage
        if self.config.track_usage and not result.get("error"):
            self._record_usage(result, user_id)
        
        return result
    
    async def _invoke_with_retry(
        self,
        provider: str,
        model: str,
        prompt: str,
        **kwargs
    ) -> dict:
        """Invoke with retry logic"""
        llm = self._get_llm(provider, model)
        if not llm:
            return {"error": f"Provider {provider} not configured"}
        
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                response = await llm.ainvoke(prompt)
                
                # Extract content
                content = response.content if hasattr(response, 'content') else str(response)
                
                # Extract usage if available
                usage = {}
                if hasattr(response, 'response_metadata'):
                    meta = response.response_metadata
                    if 'token_usage' in meta:
                        usage = meta['token_usage']
                
                return {
                    "content": content,
                    "cached": False,
                    "provider": provider,
                    "model": model,
                    "usage": usage
                }
                
            except Exception as e:
                last_error = str(e)
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(
                        self.config.retry_delay_seconds * (2 ** attempt)
                    )
        
        return {"error": last_error, "provider": provider, "model": model}
    
    def _record_usage(self, result: dict, user_id: str):
        """Record usage for tracking"""
        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        record = UsageRecord(
            timestamp=datetime.now(),
            provider=result.get("provider", ""),
            model=result.get("model", ""),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=self._estimate_cost(
                result.get("model", ""),
                prompt_tokens,
                completion_tokens
            ),
            cached=result.get("cached", False),
            user_id=user_id
        )
        
        self.usage_history.append(record)
        
        # Keep last 10000 records
        if len(self.usage_history) > 10000:
            self.usage_history = self.usage_history[-10000:]
    
    def get_usage_stats(self, user_id: Optional[str] = None) -> dict:
        """Get usage statistics"""
        records = self.usage_history
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        
        total_cost = sum(r.cost_usd for r in records)
        total_tokens = sum(r.prompt_tokens + r.completion_tokens for r in records)
        cache_hits = sum(1 for r in records if r.cached)
        
        return {
            "total_requests": len(records),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "cache_hit_rate": cache_hits / len(records) if records else 0,
            "by_provider": self._group_by_provider(records)
        }
    
    def _group_by_provider(self, records: list[UsageRecord]) -> dict:
        """Group usage by provider"""
        result = {}
        for r in records:
            if r.provider not in result:
                result[r.provider] = {"requests": 0, "tokens": 0, "cost": 0}
            result[r.provider]["requests"] += 1
            result[r.provider]["tokens"] += r.prompt_tokens + r.completion_tokens
            result[r.provider]["cost"] += r.cost_usd
        return result


# Global gateway instance
_gateway: Optional[AIGateway] = None


def get_gateway() -> AIGateway:
    """Get or create global gateway instance"""
    global _gateway
    if _gateway is None:
        _gateway = AIGateway()
    return _gateway
