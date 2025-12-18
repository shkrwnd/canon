from pydantic_settings import BaseSettings
from typing import Optional


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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# Validate required settings at startup
# Check for Azure OpenAI or legacy OpenAI
if not settings.azure_openai_api_key and not settings.openai_api_key:
    raise ValueError("Either AZURE_OPENAI_API_KEY or OPENAI_API_KEY is required. Please set it in your .env file.")
if settings.azure_openai_api_key and not settings.azure_openai_base_url:
    raise ValueError("AZURE_OPENAI_BASE_URL is required when using Azure OpenAI. Please set it in your .env file.")
if not settings.tavily_api_key:
    raise ValueError("TAVILY_API_KEY is required. Please set it in your .env file.")
if not settings.jwt_secret_key:
    raise ValueError("JWT_SECRET_KEY is required. Please set it in your .env file.")

