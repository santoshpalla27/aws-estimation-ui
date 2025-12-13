"""
Core configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost"]
    
    # Pricing Cache
    PRICING_CACHE_TTL: int = 86400  # 24 hours
    
    # Plugin Storage
    PLUGIN_STORAGE_PATH: str = "/app/plugins"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
