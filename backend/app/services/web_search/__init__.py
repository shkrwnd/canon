"""
Web Search Service Module

This module provides web search functionality with retry logic,
result evaluation, and summarization.
"""
from .models import WebSearchAttempt, WebSearchResult
from .components import (
    SearchResultEvaluator,
    SearchResultSummarizer,
    QueryGenerator,
    RetryStrategy
)
from .clients import SearchClient, DefaultSearchClient
from .service import WebSearchService

__all__ = [
    # Data Models
    "WebSearchAttempt",
    "WebSearchResult",
    # Service
    "WebSearchService",
    # Components
    "SearchResultEvaluator",
    "SearchResultSummarizer",
    "QueryGenerator",
    "RetryStrategy",
    # Interfaces
    "SearchClient",
    # Implementations
    "DefaultSearchClient",
]

