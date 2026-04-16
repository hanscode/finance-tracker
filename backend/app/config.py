"""
Application configuration using Pydantic Settings.

💡 CONCEPT: Pydantic Settings
   In your Techdegree projects, you probably used hardcoded variables
   or read them with os.getenv(). Pydantic Settings is better because:
   - It validates types automatically (if DATABASE_URL isn't a string, it fails clearly)
   - It loads variables from .env automatically
   - It centralizes all configuration in one place
   - It provides safe default values
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "Finance Tracker"
    DEBUG: bool = False

    # Database
    # SQLite path — relative to where the app runs
    DATABASE_URL: str = "sqlite:///data/finance.db"

    # JWT Authentication (we'll use this in Phase 3)
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS — allows the frontend (React) to talk to the backend
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Singleton — a single Settings instance for the entire app
settings = Settings()
