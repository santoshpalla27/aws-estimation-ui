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
    
    # CORS - can be overridden with comma-separated string in env
    CORS_ORIGINS: str = "http://localhost:3000,http://54.172.142.250"
    
    # Pricing Cache
    PRICING_CACHE_TTL: int = 86400  # 24 hours
    
    # Plugin Storage
    PLUGIN_STORAGE_PATH: str = "/app/plugins"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
