"""
Web Search Client Interfaces and Implementations

This module contains:
- SearchClient: Protocol for web search client implementations
- DefaultSearchClient: Default implementation using Tavily
"""
from typing import Protocol
from ...clients import search_web


class SearchClient(Protocol):
    """Protocol for web search client implementations"""
    
    def search(self, query: str) -> str:
        """
        Perform a web search
        
        Args:
            query: Search query string
            
        Returns:
            Formatted search results as string
        """
        ...


class DefaultSearchClient:
    """Default implementation of SearchClient using Tavily"""
    
    def search(self, query: str) -> str:
        """Perform web search using Tavily"""
        return search_web(query)

