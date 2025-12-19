# New provider-based architecture
from .providers import LLMProvider, OpenAIProvider, AzureOpenAIProvider
from .factory import LLMProviderFactory

# Legacy Tavily client (unchanged)
from .tavily_client import search_web

# Legacy exports for backward compatibility (deprecated)
# These will be removed in a future version
from .openai_client import (
    get_client,
    get_model_name,
    get_agent_decision,
    rewrite_module_content,
    generate_conversational_response,
)

__all__ = [
    # New architecture
    "LLMProvider",
    "LLMProviderFactory",
    "OpenAIProvider",
    "AzureOpenAIProvider",
    # External services
    "search_web",
    # Legacy (deprecated)
    "get_client",
    "get_model_name",
    "get_agent_decision",
    "rewrite_module_content",
    "generate_conversational_response",
]

