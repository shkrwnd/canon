from pydantic_settings import BaseSettings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str = "sqlite:///./canon.db"
    # LLM Provider settings
    llm_provider: Optional[str] = None  # "openai", "azure_openai", etc. Auto-detected if None
    # Azure OpenAI settings
    azure_openai_api_key: Optional[str] = None
    azure_openai_base_url: Optional[str] = None
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_chat_model: str = "gpt-4o-mini"
    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"  # Default OpenAI model
    # Other settings
    tavily_api_key: Optional[str] = None
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    # Logging
    log_level: str = "INFO"
    debug: bool = False
    # CORS
    cors_origins: list = ["http://localhost:3000"]
    # LLM Rate Limiting
    llm_max_concurrent_requests: int = 10  # Max concurrent API calls
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def validate_settings(settings: Settings) -> None:
    """Validate required settings"""
    errors = []
    
    # LLM provider validation
    if not settings.azure_openai_api_key and not settings.openai_api_key:
        errors.append("Either AZURE_OPENAI_API_KEY or OPENAI_API_KEY is required")
    
    if settings.azure_openai_api_key and not settings.azure_openai_base_url:
        errors.append("AZURE_OPENAI_BASE_URL is required when using Azure OpenAI")
    
    # External services
    if not settings.tavily_api_key:
        errors.append("TAVILY_API_KEY is required")
    
    # Security
    if not settings.jwt_secret_key:
        errors.append("JWT_SECRET_KEY is required")
    
    if errors:
        error_message = "Configuration errors:\n" + "\n".join(f"  - {error}" for error in errors)
        raise ValueError(error_message)


settings = Settings()
validate_settings(settings)
logger.info("Settings loaded and validated successfully")

