"""
Web Search Data Models

This module contains data models for web search operations.
These are value objects used internally by the web search service.
"""
from typing import Dict, List, Optional, Any


class WebSearchAttempt:
    """Represents a single web search attempt with its results"""
    
    def __init__(
        self,
        query: str,
        results: str,
        attempt_number: int,
        summary: Optional[str] = None,
        quality_score: Optional[float] = None,
        retry_reason: Optional[str] = None
    ):
        self.query = query
        self.results = results
        self.attempt_number = attempt_number
        self.summary = summary
        self.quality_score = quality_score
        self.retry_reason = retry_reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "query": self.query,
            "results": self.results,
            "attempt": self.attempt_number,
            "summary": self.summary,
            "quality_score": self.quality_score,
            "retry_reason": self.retry_reason
        }


class WebSearchResult:
    """Container for web search results with all attempts"""
    
    def __init__(self):
        self.attempts: List[WebSearchAttempt] = []
        self.final_results: Optional[str] = None
    
    def add_attempt(self, attempt: WebSearchAttempt):
        """Add a search attempt"""
        self.attempts.append(attempt)
        # Use the latest results as final results
        self.final_results = attempt.results
    
    def get_best_results(self) -> Optional[str]:
        """Get the best quality results from all attempts"""
        if not self.attempts:
            return None
        
        # If we have quality scores, return the highest scoring attempt
        scored_attempts = [a for a in self.attempts if a.quality_score is not None]
        if scored_attempts:
            best = max(scored_attempts, key=lambda x: x.quality_score or 0.0)
            return best.results
        
        # Otherwise, return the latest results
        return self.final_results
    
    def was_retried(self) -> bool:
        """Check if search was retried"""
        return len(self.attempts) > 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "final_results": self.final_results,
            "was_retried": self.was_retried()
        }


