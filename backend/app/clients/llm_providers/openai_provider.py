from typing import List, Dict, Optional
from openai import OpenAI
from .base import LLMProvider
import logging

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, api_key: str, default_model: str = "gpt-4o"):
        """
        Initialize OpenAI provider
        
        Args:
            api_key: OpenAI API key
            default_model: Default model to use (e.g., "gpt-4o", "gpt-4o-mini")
        """
        self.client = OpenAI(api_key=api_key)
        self._default_model = default_model
        logger.info(f"Initialized OpenAI provider with model: {default_model}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """Make OpenAI chat completion request"""
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
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def get_default_model(self) -> str:
        return self._default_model
    
    def supports_json_mode(self) -> bool:
        return True

