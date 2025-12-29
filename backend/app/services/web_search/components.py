"""
Web Search Component Classes

This module contains reusable component classes for web search operations:
- SearchResultEvaluator: Evaluates result quality
- SearchResultSummarizer: Summarizes search results
- QueryGenerator: Generates alternative search queries
- RetryStrategy: Determines retry logic

These components can be used independently or together via WebSearchService.
"""
from typing import List, Optional
from ..llm_service import LLMService
from ...config.agent_settings import agent_settings
from .models import WebSearchAttempt
import logging

logger = logging.getLogger(__name__)


class SearchResultEvaluator:
    """
    Evaluates the quality of web search results.
    
    This class is reusable and can be used independently of WebSearchService.
    """
    
    def __init__(self, llm_service: LLMService):
        """
        Initialize evaluator
        
        Args:
            llm_service: LLM service for quality evaluation
        """
        self.llm_service = llm_service
    
    async def evaluate(
        self,
        results: str,
        query: str,
        user_message: str,
        context: Optional[str] = None
    ) -> Optional[float]:
        """
        Evaluate the quality of web search results.
        
        Args:
            results: Web search results to evaluate
            query: Search query used
            user_message: Original user message
            context: Optional additional context
        
        Returns:
            Quality score between 0.0 and 1.0, or None if evaluation fails
        """
        if not results or len(results.strip()) < 50:
            return 0.0
        
        try:
            prompt = f"""Evaluate the quality of these web search results.

Search Query: "{query}"
User Request: "{user_message}"
{f"Context: {context}" if context else ""}

Search Results:
{results[:2000]}

Rate the quality on a scale of 0.0 to 1.0 where:
- 1.0 = Results are highly relevant, comprehensive, and directly answer the user's request
- 0.7-0.9 = Results are relevant but may be missing some details or slightly off-topic
- 0.4-0.6 = Results are somewhat relevant but generic or missing key information
- 0.0-0.3 = Results are irrelevant, too generic, or don't address the request

Respond with ONLY a number between 0.0 and 1.0 (e.g., 0.75)."""
            
            provider = self.llm_service.provider
            response = await provider.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a quality evaluator. Respond with only a number."},
                    {"role": "user", "content": prompt}
                ],
                model=provider.get_default_model(),
                temperature=agent_settings.evaluation_temperature
            )
            
            # Parse the score
            score = float(response.strip())
            return max(0.0, min(1.0, score))  # Clamp between 0.0 and 1.0
            
        except Exception as e:
            logger.warning(f"Failed to evaluate search results: {e}")
            return None


class SearchResultSummarizer:
    """
    Summarizes web search results.
    
    This class is reusable and can be used independently of WebSearchService.
    """
    
    def __init__(self, llm_service: LLMService):
        """
        Initialize summarizer
        
        Args:
            llm_service: LLM service for summarization
        """
        self.llm_service = llm_service
    
    async def summarize(self, results: str) -> Optional[str]:
        """
        Generate a concise summary of web search results.
        
        Args:
            results: Web search results to summarize
        
        Returns:
            Summary string, or None if summarization fails
        """
        if not results or len(results.strip()) < 50:
            return "No significant results found."
        
        try:
            prompt = f"""Summarize these web search results in 2-3 sentences.
Focus on the most relevant and useful information.

Search Results:
{results[:2000]}

Provide a concise summary that highlights key findings."""
            
            provider = self.llm_service.provider
            response = await provider.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a summarizer. Provide concise summaries."},
                    {"role": "user", "content": prompt}
                ],
                model=provider.get_default_model(),
                temperature=agent_settings.summarization_temperature
            )
            
            return response.strip()
            
        except Exception as e:
            logger.warning(f"Failed to summarize search results: {e}")
            return None


class QueryGenerator:
    """
    Generates alternative search queries based on previous attempts.
    
    This class is reusable and can be used independently of WebSearchService.
    """
    
    def __init__(self, llm_service: LLMService):
        """
        Initialize query generator
        
        Args:
            llm_service: LLM service for query generation
        """
        self.llm_service = llm_service
    
    async def generate_alternative(
        self,
        original_query: str,
        user_message: str,
        previous_attempts: List[WebSearchAttempt],
        context: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate an alternative search query based on previous attempts.
        
        Args:
            original_query: Original search query
            user_message: Original user message
            previous_attempts: List of previous search attempts
            context: Optional additional context
        
        Returns:
            Alternative query string, or None if generation fails
        """
        try:
            # Build context about previous attempts
            attempts_context = ""
            for attempt in previous_attempts:
                attempts_context += f"Query: {attempt.query}\n"
                if attempt.summary:
                    attempts_context += f"Results: {attempt.summary}\n"
                if attempt.quality_score is not None:
                    attempts_context += f"Quality: {attempt.quality_score:.2f}\n"
                attempts_context += "\n"
            
            prompt = f"""Generate an alternative, more specific search query based on the user's request and previous search attempts.

User Request: "{user_message}"
{f"Context: {context}" if context else ""}

Previous Search Attempts:
{attempts_context}

Original Query: "{original_query}"

Generate a NEW, DIFFERENT search query that:
1. Is more specific than the original
2. Addresses gaps in previous results
3. Uses different keywords or phrasing
4. Better matches the user's intent

Respond with ONLY the search query (no explanations, no quotes)."""
            
            provider = self.llm_service.provider
            response = await provider.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a search query optimizer. Respond with only the query."},
                    {"role": "user", "content": prompt}
                ],
                model=provider.get_default_model(),
                temperature=agent_settings.decision_temperature
            )
            
            return response.strip().strip('"').strip("'")
            
        except Exception as e:
            logger.warning(f"Failed to generate alternative query: {e}")
            return None


class RetryStrategy:
    """
    Determines if a retry is needed based on attempt quality.
    
    This class is reusable and can be used independently of WebSearchService.
    """
    
    def __init__(self, min_quality_score: float = 0.6, min_result_length: int = 100):
        """
        Initialize retry strategy
        
        Args:
            min_quality_score: Minimum quality score to consider results satisfactory
            min_result_length: Minimum result length to consider results valid
        """
        self.min_quality_score = min_quality_score
        self.min_result_length = min_result_length
    
    def should_retry(
        self,
        attempt: WebSearchAttempt,
        evaluation_enabled: bool = True
    ) -> bool:
        """
        Determine if a retry is needed based on attempt quality.
        
        Args:
            attempt: The search attempt to evaluate
            evaluation_enabled: Whether evaluation is enabled
        
        Returns:
            True if retry is needed, False otherwise
        """
        # If evaluation is disabled, don't retry
        if not evaluation_enabled:
            return False
        
        # If no quality score, don't retry (can't evaluate)
        if attempt.quality_score is None:
            return False
        
        # If quality is below threshold, retry
        if attempt.quality_score < self.min_quality_score:
            return True
        
        # If results are empty or too short, retry
        if not attempt.results or len(attempt.results.strip()) < self.min_result_length:
            return True
        
        return False
    
    def get_retry_reason(
        self,
        previous_attempt: WebSearchAttempt,
        current_quality: Optional[float] = None
    ) -> str:
        """
        Generate a human-readable reason for why retry was performed.
        
        Args:
            previous_attempt: The previous search attempt
            current_quality: Quality score of current attempt (optional)
        
        Returns:
            Reason string
        """
        if previous_attempt.quality_score is None:
            return "Initial results were insufficient or could not be evaluated"
        
        if previous_attempt.quality_score < 0.4:
            return "Initial results were too generic or irrelevant"
        elif previous_attempt.quality_score < 0.6:
            return "Initial results were missing key information"
        else:
            return "Initial results needed more specific information"


