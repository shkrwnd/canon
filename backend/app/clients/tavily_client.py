from tavily import TavilyClient
from ..config import settings
import logging

logger = logging.getLogger(__name__)

_client = None


def get_tavily_client() -> TavilyClient:
    """Get or create Tavily client"""
    global _client
    if _client is None:
        _client = TavilyClient(api_key=settings.tavily_api_key)
        logger.info("Initialized Tavily client")
    return _client


def search_web(query: str) -> str:
    """Search the web using Tavily and return formatted results"""
    try:
        logger.info(f"Performing web search for: {query}")
        client = get_tavily_client()
        response = client.search(query=query, max_results=5)
        
        results = []
        for result in response.get("results", []):
            title = result.get("title", "")
            url = result.get("url", "")
            content = result.get("content", "")
            results.append(f"Title: {title}\nURL: {url}\nContent: {content}\n")
        
        formatted_results = "\n---\n".join(results)
        logger.debug(f"Web search completed, found {len(results)} results")
        return formatted_results
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return ""

