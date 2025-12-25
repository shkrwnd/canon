"""
Web Search Service

This service orchestrates web search operations with retry logic, result evaluation,
and summarization. It is decoupled from the main agent service and can be
configured via agent settings.

The service uses dependency injection to compose reusable components:
- SearchClient: Interface for web search operations
- SearchResultEvaluator: Evaluates result quality
- SearchResultSummarizer: Summarizes search results
- QueryGenerator: Generates alternative search queries
- RetryStrategy: Determines retry logic
"""
from typing import Optional
from ..llm_service import LLMService
from ...config.agent_settings import agent_settings
from ...core.telemetry import get_tracer
from .models import WebSearchAttempt, WebSearchResult
from .components import (
    SearchResultEvaluator,
    SearchResultSummarizer,
    QueryGenerator,
    RetryStrategy
)
from .clients import SearchClient, DefaultSearchClient
import logging

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class WebSearchService:
    """
    Service for performing web searches with retry logic and result evaluation.
    
    This service orchestrates all components and is decoupled from the agent service.
    All components can be injected for better testability and flexibility.
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        search_client: Optional[SearchClient] = None,
        evaluator: Optional[SearchResultEvaluator] = None,
        summarizer: Optional[SearchResultSummarizer] = None,
        query_generator: Optional[QueryGenerator] = None,
        retry_strategy: Optional[RetryStrategy] = None
    ):
        """
        Initialize web search service
        
        Args:
            llm_service: LLM service (required for evaluator/summarizer/generator)
            search_client: Search client implementation (defaults to Tavily)
            evaluator: Result evaluator (defaults to SearchResultEvaluator)
            summarizer: Result summarizer (defaults to SearchResultSummarizer)
            query_generator: Query generator (defaults to QueryGenerator)
            retry_strategy: Retry strategy (defaults to RetryStrategy)
        """
        self.llm_service = llm_service
        self.search_client = search_client or DefaultSearchClient()
        self.evaluator = evaluator or SearchResultEvaluator(llm_service)
        self.summarizer = summarizer or SearchResultSummarizer(llm_service)
        self.query_generator = query_generator or QueryGenerator(llm_service)
        self.retry_strategy = retry_strategy or RetryStrategy(
            min_quality_score=agent_settings.web_search_min_quality_score,
            min_result_length=100
        )
    
    async def search_with_retry(
        self,
        initial_query: str,
        user_message: str,
        context: Optional[str] = None
    ) -> WebSearchResult:
        """
        Perform web search with retry logic if results are unsatisfactory.
        
        Args:
            initial_query: Initial search query from agent decision
            user_message: Original user message for context
            context: Optional additional context for evaluation
        
        Returns:
            WebSearchResult containing all search attempts and final results
        """
        result = WebSearchResult()
        
        # Perform initial search
        with tracer.start_as_current_span("web_search.initial_search") as span:
            span.set_attribute("web_search.query", initial_query)
            initial_results = self.search_client.search(initial_query)
            
            # Summarize initial results if enabled
            summary = None
            if agent_settings.web_search_summarize_results:
                summary = await self.summarizer.summarize(initial_results)
            
            # Evaluate quality if enabled
            quality_score = None
            if agent_settings.web_search_evaluate_results:
                quality_score = await self.evaluator.evaluate(
                    initial_results, initial_query, user_message, context
                )
            
            attempt = WebSearchAttempt(
                query=initial_query,
                results=initial_results,
                attempt_number=1,
                summary=summary,
                quality_score=quality_score
            )
            result.add_attempt(attempt)
            
            span.set_attribute("web_search.results_length", len(initial_results) if initial_results else 0)
            span.set_attribute("web_search.quality_score", quality_score or 0.0)
        
        # Check if retry is needed and enabled
        if not agent_settings.web_search_retry_enabled:
            logger.debug("Web search retry is disabled")
            return result
        
        # Determine if retry is needed
        should_retry = self.retry_strategy.should_retry(
            attempt,
            evaluation_enabled=agent_settings.web_search_evaluate_results
        )
        
        if not should_retry:
            logger.debug(f"Initial search results are satisfactory (score: {quality_score})")
            return result
        
        # Perform retries
        max_retries = agent_settings.web_search_max_retries
        for retry_num in range(1, max_retries + 1):
            with tracer.start_as_current_span("web_search.retry") as span:
                span.set_attribute("web_search.retry_number", retry_num)
                
                # Generate alternative query
                alternative_query = await self.query_generator.generate_alternative(
                    initial_query,
                    user_message,
                    result.attempts,
                    context
                )
                
                if not alternative_query:
                    logger.warning(f"Could not generate alternative query for retry {retry_num}")
                    break
                
                span.set_attribute("web_search.query", alternative_query)
                
                # Perform retry search
                retry_results = self.search_client.search(alternative_query)
                
                # Summarize retry results
                retry_summary = None
                if agent_settings.web_search_summarize_results:
                    retry_summary = await self.summarizer.summarize(retry_results)
                
                # Evaluate retry results
                retry_quality = None
                if agent_settings.web_search_evaluate_results:
                    retry_quality = await self.evaluator.evaluate(
                        retry_results, alternative_query, user_message, context
                    )
                
                # Determine retry reason
                retry_reason = self.retry_strategy.get_retry_reason(attempt, retry_quality)
                
                retry_attempt = WebSearchAttempt(
                    query=alternative_query,
                    results=retry_results,
                    attempt_number=retry_num + 1,
                    summary=retry_summary,
                    quality_score=retry_quality,
                    retry_reason=retry_reason
                )
                result.add_attempt(retry_attempt)
                
                span.set_attribute("web_search.results_length", len(retry_results) if retry_results else 0)
                span.set_attribute("web_search.quality_score", retry_quality or 0.0)
                
                logger.info(
                    f"Web search retry {retry_num}: query='{alternative_query}', "
                    f"quality={retry_quality}, reason='{retry_reason}'"
                )
                
                # If retry results are satisfactory, stop retrying
                if retry_quality and retry_quality >= agent_settings.web_search_min_quality_score:
                    logger.debug(f"Retry {retry_num} results are satisfactory, stopping retries")
                    break
        
        return result
