from pydantic_settings import BaseSettings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str = "sqlite:///./canon.db"
    # Azure OpenAI settings
    azure_openai_api_key: Optional[str] = None
    azure_openai_base_url: Optional[str] = None
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_chat_model: str = "gpt-4o-mini"
    # Legacy OpenAI (for backward compatibility)
    openai_api_key: Optional[str] = None
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def validate_settings(settings: Settings) -> None:
    """Validate required settings"""
    errors = []
    
    if not settings.azure_openai_api_key and not settings.openai_api_key:
        errors.append("Either AZURE_OPENAI_API_KEY or OPENAI_API_KEY is required")
    
    if settings.azure_openai_api_key and not settings.azure_openai_base_url:
        errors.append("AZURE_OPENAI_BASE_URL is required when using Azure OpenAI")
    
    if not settings.tavily_api_key:
        errors.append("TAVILY_API_KEY is required")
    
    if not settings.jwt_secret_key:
        errors.append("JWT_SECRET_KEY is required")
    
    if errors:
        error_message = "Configuration errors:\n" + "\n".join(f"  - {error}" for error in errors)
        raise ValueError(error_message)


settings = Settings()
validate_settings(settings)
logger.info("Settings loaded and validated successfully")

