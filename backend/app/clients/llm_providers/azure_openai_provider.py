from typing import List, Dict, Optional
from openai import AzureOpenAI
from .base import LLMProvider
import logging

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider implementation"""
    
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        api_version: str = "2024-12-01-preview",
        default_model: str = "gpt-4o-mini"
    ):
        """
        Initialize Azure OpenAI provider
        
        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            api_version: API version
            default_model: Default model to use
        """
        endpoint = endpoint.rstrip('/')
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )
        self._default_model = default_model
        logger.info(f"Initialized Azure OpenAI provider with model: {default_model}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """Make Azure OpenAI chat completion request"""
        model = model or self._default_model
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Azure OpenAI API error: {e}")
            raise
    
    def get_default_model(self) -> str:
        return self._default_model
    
    def supports_json_mode(self) -> bool:
        return True

