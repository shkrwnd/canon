from typing import List, Dict, Any
from tavily import TavilyClient
from .config import settings

_client = None

def get_client() -> TavilyClient:
    """Get or create Tavily client (lazy initialization)"""
    global _client
    if _client is None:
        if not settings.tavily_api_key:
            raise ValueError("TAVILY_API_KEY is not set. Please configure it in your .env file.")
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


def search_web(query: str, max_results: int = 5) -> str:
    """Perform web search and return formatted results"""
    try:
        client = get_client()
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced"
        )
        
        results = response.get("results", [])
        if not results:
            return "No search results found."
        
        formatted_results = []
        for result in results:
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")
            formatted_results.append(f"Title: {title}\nURL: {url}\nContent: {content}\n")
        
        return "\n---\n".join(formatted_results)
    except Exception as e:
        return f"Error performing web search: {str(e)}"



