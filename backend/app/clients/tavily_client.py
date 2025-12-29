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
        
        # Log the raw response from Tavily
        logger.info(f"[TAVILY] Raw search response received: {len(response.get('results', []))} results")
        logger.debug(f"[TAVILY] Full response: {response}")
        
        results = []
        for i, result in enumerate(response.get("results", []), 1):
            title = result.get("title", "")
            url = result.get("url", "")
            content = result.get("content", "")
            results.append(f"Title: {title}\nURL: {url}\nContent: {content}\n")
            
            # Log each result
            logger.info(f"[TAVILY] Result {i}: Title='{title}', URL='{url}', Content length={len(content)}")
            logger.debug(f"[TAVILY] Result {i} content preview: {content[:200]}...")
        
        formatted_results = "\n---\n".join(results)
        logger.info(f"[TAVILY] Web search completed, formatted {len(results)} results, total length: {len(formatted_results)}")
        logger.debug(f"[TAVILY] Formatted results preview (first 500 chars): {formatted_results[:500]}")
        return formatted_results
    except Exception as e:
        logger.error(f"[TAVILY] Web search failed: {e}")
        return ""

