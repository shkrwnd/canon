from typing import Optional
from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .azure_openai_provider import AzureOpenAIProvider
from ...config import settings
import logging

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for creating LLM providers"""
    
    @staticmethod
    def create_provider(provider_name: Optional[str] = None) -> LLMProvider:
        """
        Create LLM provider based on configuration
        
        Args:
            provider_name: Optional provider name override. If None, uses settings.
        
        Returns:
            LLM provider instance
        
        Raises:
            ValueError: If required configuration is missing
        """
        provider_name = provider_name or getattr(settings, 'llm_provider', None)
        
        # Default behavior: check Azure first, then OpenAI
        if provider_name is None:
            if settings.azure_openai_api_key and settings.azure_openai_base_url:
                provider_name = "azure_openai"
            elif settings.openai_api_key:
                provider_name = "openai"
            else:
                raise ValueError("Either AZURE_OPENAI_API_KEY or OPENAI_API_KEY must be set")
        
        if provider_name == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
            
            default_model = getattr(settings, 'openai_model', "gpt-4o")
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                default_model=default_model
            )
        
        elif provider_name == "azure_openai":
            if not settings.azure_openai_api_key:
                raise ValueError("AZURE_OPENAI_API_KEY is required for Azure OpenAI provider")
            if not settings.azure_openai_base_url:
                raise ValueError("AZURE_OPENAI_BASE_URL is required for Azure OpenAI provider")
            
            return AzureOpenAIProvider(
                api_key=settings.azure_openai_api_key,
                endpoint=settings.azure_openai_base_url,
                api_version=settings.azure_openai_api_version,
                default_model=settings.azure_openai_chat_model
            )
        
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}. Supported providers: openai, azure_openai")
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available providers based on configuration"""
        available = []
        
        if settings.openai_api_key:
            available.append("openai")
        
        if settings.azure_openai_api_key and settings.azure_openai_base_url:
            available.append("azure_openai")
        
        return available

