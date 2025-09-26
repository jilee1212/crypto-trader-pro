"""
FastAPI application configuration.
"""

import os
from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # App basic info
    APP_NAME: str = "Crypto Trader Pro API"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite default port
        "http://localhost:5174",  # Vite alternative port
        "http://localhost:5175",  # Vite alternative port 2
        "http://localhost:8080",  # Alternative port
        "http://nosignup.kr",     # Production domain
        "https://nosignup.kr"     # Production HTTPS
    ]

    # JWT Settings - ENHANCED SECURITY
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE-THIS-IN-PRODUCTION-USE-STRONG-SECRET-KEY-FOR-JWT-TOKENS")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Shorter expiry for security
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day max

    # Database
    DATABASE_URL: Optional[str] = os.getenv(
        "DATABASE_URL",
        "sqlite:///./crypto_trading.db"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Binance API (for testing)
    BINANCE_TESTNET: bool = True
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"

    # Security
    BCRYPT_ROUNDS: int = 12

    # Rate limiting
    RATE_LIMIT_CALLS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # Celery
    CELERY_BROKER_URL: str = REDIS_URL
    CELERY_RESULT_BACKEND: str = REDIS_URL

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()