from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class LLMProvider(ABC):
    """Abstract interface for LLM providers"""
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Make a chat completion request
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name (uses default if None)
            temperature: Sampling temperature
            response_format: Optional response format (e.g., {"type": "json_object"})
        
        Returns:
            Response text content
        """
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider"""
        pass
    
    @abstractmethod
    def supports_json_mode(self) -> bool:
        """Check if provider supports JSON response format"""
        pass

