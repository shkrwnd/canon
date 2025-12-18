from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "sqlite:///./canon.db"
    openai_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# Validate required settings at startup
if not settings.openai_api_key:
    raise ValueError("OPENAI_API_KEY is required. Please set it in your .env file.")
if not settings.tavily_api_key:
    raise ValueError("TAVILY_API_KEY is required. Please set it in your .env file.")
if not settings.jwt_secret_key:
    raise ValueError("JWT_SECRET_KEY is required. Please set it in your .env file.")

