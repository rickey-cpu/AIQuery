"""
Feedback Service - Learn from User Corrections
Enables self-improving SQL generation like Uber FINCH
"""
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


@dataclass
class FeedbackRecord:
    """A feedback record for learning"""
    question: str
    original_sql: str
    corrected_sql: Optional[str] = None
    rating: int = 0  # 1-5 stars, 0 = not rated
    feedback_text: Optional[str] = None
    was_executed: bool = False
    execution_success: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: str = "anonymous"
    
    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "original_sql": self.original_sql,
            "corrected_sql": self.corrected_sql,
            "rating": self.rating,
            "feedback_text": self.feedback_text,
            "was_executed": self.was_executed,
            "execution_success": self.execution_success,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FeedbackRecord":
        data = data.copy()
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class FeedbackService:
    """
    Feedback Service - Self-Improving System
    
    Features (inspired by FINCH):
    - Capture SQL corrections from users
    - Store successful queries for few-shot learning
    - Track query quality metrics
    - Export corrections to vector store
    - A/B test SQL generation strategies
    
    Usage:
        feedback = FeedbackService()
        
        # Record a query
        feedback.record_query(question, sql, user_id)
        
        # User provides correction
        feedback.add_correction(question, correct_sql, user_id)
        
        # User rates the response
        feedback.add_rating(question, 5, user_id)
    """
    
    def __init__(self, storage_path: str = "data/feedback"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._records: list[FeedbackRecord] = []
        self._corrections_cache: dict[str, str] = {}
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Load feedback records from disk"""
        feedback_file = self.storage_path / "feedback.json"
        if feedback_file.exists():
            try:
                with open(feedback_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._records = [FeedbackRecord.from_dict(r) for r in data]
            except Exception:
                self._records = []
    
    def _save_to_disk(self):
        """Save feedback records to disk"""
        feedback_file = self.storage_path / "feedback.json"
        with open(feedback_file, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self._records], f, indent=2, ensure_ascii=False)
    
    def record_query(
        self,
        question: str,
        sql: str,
        user_id: str = "anonymous",
        was_executed: bool = False,
        execution_success: bool = False
    ):
        """Record a query for feedback tracking"""
        record = FeedbackRecord(
            question=question,
            original_sql=sql,
            user_id=user_id,
            was_executed=was_executed,
            execution_success=execution_success
        )
        self._records.append(record)
        self._save_to_disk()
        return record
    
    def add_correction(
        self,
        question: str,
        corrected_sql: str,
        user_id: str = "anonymous"
    ):
        """Add user correction to a query"""
        # Find matching record
        for record in reversed(self._records):
            if record.question == question and record.user_id == user_id:
                record.corrected_sql = corrected_sql
                self._save_to_disk()
                
                # Cache for quick lookup
                self._corrections_cache[question.lower()] = corrected_sql
                return True
        
        # No matching record, create new one
        record = FeedbackRecord(
            question=question,
            original_sql="",
            corrected_sql=corrected_sql,
            user_id=user_id,
            rating=5  # User-provided SQL gets high rating
        )
        self._records.append(record)
        self._save_to_disk()
        return True
    
    def add_rating(
        self,
        question: str,
        rating: int,
        user_id: str = "anonymous",
        feedback_text: Optional[str] = None
    ):
        """Add user rating to a query"""
        for record in reversed(self._records):
            if record.question == question and record.user_id == user_id:
                record.rating = max(1, min(5, rating))  # Clamp 1-5
                if feedback_text:
                    record.feedback_text = feedback_text
                self._save_to_disk()
                return True
        return False
    
    def get_correction(self, question: str) -> Optional[str]:
        """Get cached correction for similar question"""
        return self._corrections_cache.get(question.lower())
    
    def get_high_rated_examples(self, min_rating: int = 4, limit: int = 10) -> list[dict]:
        """Get high-rated examples for few-shot learning"""
        good_records = [
            r for r in self._records 
            if r.rating >= min_rating or (r.corrected_sql and r.execution_success)
        ]
        
        # Sort by rating and recency
        good_records.sort(key=lambda r: (r.rating, r.timestamp), reverse=True)
        
        examples = []
        for r in good_records[:limit]:
            sql = r.corrected_sql or r.original_sql
            if sql:
                examples.append({
                    "question": r.question,
                    "sql": sql
                })
        
        return examples
    
    def get_stats(self) -> dict:
        """Get feedback statistics"""
        total = len(self._records)
        if total == 0:
            return {"total": 0}
        
        rated = [r for r in self._records if r.rating > 0]
        corrected = [r for r in self._records if r.corrected_sql]
        executed = [r for r in self._records if r.was_executed]
        successful = [r for r in executed if r.execution_success]
        
        return {
            "total_queries": total,
            "rated_queries": len(rated),
            "average_rating": sum(r.rating for r in rated) / len(rated) if rated else 0,
            "correction_rate": len(corrected) / total if total else 0,
            "execution_rate": len(executed) / total if total else 0,
            "success_rate": len(successful) / len(executed) if executed else 0
        }
    
    def export_to_vector_store(self, vector_store) -> int:
        """Export high-quality examples to vector store"""
        examples = self.get_high_rated_examples(min_rating=4, limit=50)
        added = 0
        
        for ex in examples:
            try:
                vector_store.add_example(ex["question"], ex["sql"])
                added += 1
            except Exception:
                pass
        
        return added
    
    def get_improvement_suggestions(self) -> list[str]:
        """Analyze feedback to suggest improvements"""
        suggestions = []
        
        stats = self.get_stats()
        
        if stats.get("average_rating", 5) < 3.5:
            suggestions.append("Consider improving SQL generation prompts")
        
        if stats.get("correction_rate", 0) > 0.3:
            suggestions.append("High correction rate - review semantic layer mappings")
        
        if stats.get("success_rate", 1) < 0.8:
            suggestions.append("Low execution success - check SQL syntax validation")
        
        # Find common correction patterns
        corrections = [r for r in self._records if r.corrected_sql]
        if len(corrections) > 5:
            # Could analyze patterns here
            suggestions.append(f"Found {len(corrections)} corrections to learn from")
        
        return suggestions


# Global feedback instance
_feedback: Optional[FeedbackService] = None


def get_feedback() -> FeedbackService:
    """Get or create global feedback instance"""
    global _feedback
    if _feedback is None:
        _feedback = FeedbackService()
    return _feedback
