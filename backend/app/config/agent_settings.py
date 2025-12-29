"""
Agent Behavior Settings

This module defines configurable settings for agent behavior.
All settings can be controlled via environment variables or defaults.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AgentSettings(BaseSettings):
    """
    Agent behavior configuration settings.
    
    These settings control various aspects of agent behavior:
    - Web search retry logic
    - Result evaluation
    - Summarization
    - And more...
    """
    
    # ============================================
    # Web Search Settings
    # ============================================
    
    # Enable/disable web search retry mechanism
    web_search_retry_enabled: bool = True
    
    # Maximum number of retry attempts for web search
    web_search_max_retries: int = 2
    
    # Enable result quality evaluation before retry
    web_search_evaluate_results: bool = True
    
    # Enable result summarization for user display
    web_search_summarize_results: bool = True
    
    # Minimum result quality score (0.0-1.0) to consider results satisfactory
    # If results score below this, retry will be attempted
    web_search_min_quality_score: float = 0.6
    
    # ============================================
    # Intent Classification Settings
    # ============================================
    
    # Number of recent messages to consider for intent classification
    intent_classification_history_length: int = 5
    
    # Number of recent messages to consider for detailed decision
    decision_history_length: int = 10
    
    # ============================================
    # Document Rewrite Settings
    # ============================================
    
    # Enable document validation retry
    document_validation_retry_enabled: bool = True
    
    # Maximum validation retry attempts
    document_validation_max_retries: int = 1
    
    # ============================================
    # LLM Settings
    # ============================================
    
    # Temperature for intent classification (lower = more deterministic)
    intent_classification_temperature: float = 0.3
    
    # Temperature for detailed decision making
    decision_temperature: float = 0.5
    
    # Temperature for document rewriting
    document_rewrite_temperature: float = 0.7
    
    # Temperature for result evaluation
    evaluation_temperature: float = 0.3
    
    # Temperature for result summarization
    summarization_temperature: float = 0.5
    
    class Config:
        env_file = ".env"
        env_prefix = "AGENT_"
        case_sensitive = False


# Global agent settings instance
agent_settings = AgentSettings()

logger.info(f"Agent settings loaded: web_search_retry={agent_settings.web_search_retry_enabled}, "
            f"max_retries={agent_settings.web_search_max_retries}")


