"""
Application configuration using Pydantic Settings.
All configuration is loaded from environment variables.
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/aws_cost_calculator",
        alias="DATABASE_URL"
    )
    database_url_sync: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/aws_cost_calculator",
        alias="DATABASE_URL_SYNC"
    )
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    # Upload settings
    max_upload_size_mb: int = Field(default=50, alias="MAX_UPLOAD_SIZE_MB")
    upload_dir: str = Field(default="./uploads", alias="UPLOAD_DIR")
    
    # Pricing settings
    pricing_update_enabled: bool = Field(default=True, alias="PRICING_UPDATE_ENABLED")
    pricing_update_schedule: str = Field(default="0 2 * * *", alias="PRICING_UPDATE_SCHEDULE")
    pricing_data_dir: str = Field(default="./pricing_data", alias="PRICING_DATA_DIR")
    
    # AWS Pricing API endpoints
    aws_pricing_api_base: str = "https://pricing.us-east-1.amazonaws.com"
    aws_bulk_pricing_base: str = "https://pricing.us-east-1.amazonaws.com"
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS"
    )
    
    # Supported AWS services for pricing ingestion
    supported_services: List[str] = [
        "AmazonEC2",
        "AmazonRDS",
        "AmazonS3",
        "AmazonEBS",
        "AWSLambda"
    ]
    
    # Terraform parsing settings
    max_module_depth: int = 5
    # CRITICAL: High limits to avoid silent truncation
    # If infrastructure has 300 instances, we MUST expand all 300
    # Lower limits cause massive cost underestimation
    max_count_expansion: int = Field(default=10000, alias="MAX_COUNT_EXPANSION")
    max_for_each_expansion: int = Field(default=10000, alias="MAX_FOR_EACH_EXPANSION")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env.lower() == "development"


# Global settings instance
settings = Settings()
