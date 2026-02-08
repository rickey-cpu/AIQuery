"""
Conversation Memory - Multi-turn Context Management
Enables context-aware conversations like Uber FINCH
"""
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import json
import hashlib


@dataclass
class Message:
    """A single message in conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ConversationContext:
    """Extracted context from conversation"""
    entities: list[str] = field(default_factory=list)  # Tables, columns mentioned
    filters: list[str] = field(default_factory=list)   # WHERE clause values
    time_range: Optional[str] = None
    aggregations: list[str] = field(default_factory=list)  # SUM, COUNT, etc.
    last_sql: Optional[str] = None
    last_result_summary: Optional[str] = None


class ConversationMemory:
    """
    Conversation Memory - Multi-turn Context Manager
    
    Features (inspired by FINCH):
    - Store conversation history
    - Extract key entities across turns
    - Provide context window to LLM
    - Session management
    - Context summarization
    
    Example:
        User: "Show revenue by month"
        Bot: [Shows data]
        User: "Now break it down by region"  ← Memory knows "revenue by month"
        User: "Compare with last year"        ← Memory knows context
    """
    
    def __init__(self, max_turns: int = 20, max_tokens: int = 4000):
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self._sessions: dict[str, deque[Message]] = {}
        self._contexts: dict[str, ConversationContext] = {}
    
    def _get_session_id(self, user_id: str, session_id: Optional[str] = None) -> str:
        """Generate or use session ID"""
        if session_id:
            return f"{user_id}:{session_id}"
        return user_id
    
    def add_message(
        self,
        user_id: str,
        role: str,
        content: str,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """Add message to conversation history"""
        sid = self._get_session_id(user_id, session_id)
        
        if sid not in self._sessions:
            self._sessions[sid] = deque(maxlen=self.max_turns)
            self._contexts[sid] = ConversationContext()
        
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self._sessions[sid].append(message)
        
        # Update context
        if role == "user":
            self._extract_context(sid, content)
        elif role == "assistant" and metadata:
            if "sql" in metadata:
                self._contexts[sid].last_sql = metadata["sql"]
            if "result_summary" in metadata:
                self._contexts[sid].last_result_summary = metadata["result_summary"]
    
    def _extract_context(self, session_id: str, content: str):
        """Extract entities and context from user message"""
        content_lower = content.lower()
        ctx = self._contexts[session_id]
        
        # Detect references to previous context
        reference_words = ["it", "that", "this", "same", "those", "these", 
                          "nó", "đó", "này", "như vậy", "tương tự"]
        has_reference = any(word in content_lower.split() for word in reference_words)
        
        # Carry forward context if reference detected
        if not has_reference:
            # New topic - may reset some context
            pass
        
        # Extract entities (simple keyword extraction)
        business_terms = [
            "revenue", "doanh thu", "sales", "bán hàng",
            "customer", "khách hàng", "order", "đơn hàng",
            "product", "sản phẩm", "category", "danh mục"
        ]
        for term in business_terms:
            if term in content_lower and term not in ctx.entities:
                ctx.entities.append(term)
        
        # Extract time ranges
        time_patterns = {
            "last month": "last_month",
            "tháng trước": "last_month",
            "this year": "this_year",
            "năm nay": "this_year",
            "last year": "last_year",
            "năm trước": "last_year",
            "today": "today",
            "hôm nay": "today"
        }
        for pattern, value in time_patterns.items():
            if pattern in content_lower:
                ctx.time_range = value
        
        # Extract aggregation requests
        if any(word in content_lower for word in ["total", "tổng", "sum"]):
            if "sum" not in ctx.aggregations:
                ctx.aggregations.append("sum")
        if any(word in content_lower for word in ["count", "đếm", "how many", "bao nhiêu"]):
            if "count" not in ctx.aggregations:
                ctx.aggregations.append("count")
        if any(word in content_lower for word in ["average", "trung bình", "avg"]):
            if "avg" not in ctx.aggregations:
                ctx.aggregations.append("avg")
    
    def get_history(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        max_messages: Optional[int] = None
    ) -> list[dict]:
        """Get conversation history"""
        sid = self._get_session_id(user_id, session_id)
        
        if sid not in self._sessions:
            return []
        
        messages = list(self._sessions[sid])
        if max_messages:
            messages = messages[-max_messages:]
        
        return [m.to_dict() for m in messages]
    
    def get_context(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> ConversationContext:
        """Get extracted context"""
        sid = self._get_session_id(user_id, session_id)
        return self._contexts.get(sid, ConversationContext())
    
    def get_context_for_prompt(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> str:
        """Format context for LLM prompt"""
        ctx = self.get_context(user_id, session_id)
        history = self.get_history(user_id, session_id, max_messages=5)
        
        lines = ["## Conversation Context"]
        
        if ctx.entities:
            lines.append(f"- Topics discussed: {', '.join(ctx.entities)}")
        if ctx.time_range:
            lines.append(f"- Time range: {ctx.time_range}")
        if ctx.aggregations:
            lines.append(f"- Aggregations: {', '.join(ctx.aggregations)}")
        if ctx.last_sql:
            lines.append(f"- Last SQL: {ctx.last_sql[:200]}...")
        
        if history:
            lines.append("\n## Recent Messages")
            for msg in history[-3:]:  # Last 3 messages
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"][:200]
                lines.append(f"- {role}: {content}")
        
        return "\n".join(lines)
    
    def clear_session(self, user_id: str, session_id: Optional[str] = None):
        """Clear session history"""
        sid = self._get_session_id(user_id, session_id)
        if sid in self._sessions:
            del self._sessions[sid]
        if sid in self._contexts:
            del self._contexts[sid]
    
    def get_all_sessions(self, user_id: str) -> list[str]:
        """Get all session IDs for user"""
        prefix = f"{user_id}:"
        return [
            sid.replace(prefix, "") 
            for sid in self._sessions.keys() 
            if sid.startswith(prefix) or sid == user_id
        ]


# Global memory instance
_memory: Optional[ConversationMemory] = None


def get_memory() -> ConversationMemory:
    """Get or create global memory instance"""
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
    return _memory
