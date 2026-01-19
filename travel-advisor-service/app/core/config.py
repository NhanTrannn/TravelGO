"""
Core configuration using pydantic-settings
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Info
    SERVICE_NAME: str = "travel-advisor-service"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # MongoDB
    SPOTS_MONGODB_URI: str = "mongodb://localhost:27017"
    SPOTS_DB_NAME: str = "spots_db"
    
    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    
    # LLM API
    FPT_API_KEY: str
    FPT_BASE_URL: str = "https://mkp-api.fptcloud.com"
    FPT_MODEL_NAME: str = "SaoLa3.1-medium"
    FPT_TEMPERATURE: float = 0.7
    FPT_MAX_TOKENS: int = 10240
    
    # Embedding
    EMBEDDING_MODEL: str = "keepitreal/vietnamese-sbert"
    EMBEDDING_DEVICE: str = "cpu"
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    
    # JWT / Auth Settings
    SECRET_KEY: str = "change-this-secret-key-in-production-use-long-random-string"
    
    # Extra fields from .env that we also support
    MONGODB_URI: Optional[str] = None  # Legacy key
    MONGODB_URI_KNOWLEDGE: Optional[str] = None  # Legacy key
    FPT_DEFAULT_TEMPERATURE: Optional[str] = None  # Legacy key
    ENABLE_PROMPT_TIMING: Optional[str] = None  # Legacy key
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


# Global settings instance
settings = Settings()
