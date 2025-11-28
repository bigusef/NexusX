"""Application configuration module.

This module provides centralized configuration management using pydantic-settings.
Settings are loaded from environment variables and .env file.
"""

from functools import lru_cache

from pydantic import PostgresDsn, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.shared.enums import Environment


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        environment: Current runtime environment. Defaults to development.
        database_dsn: PostgreSQL async connection DSN using asyncpg driver.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project Global Configuration
    environment: Environment = Environment.DEVELOPMENT

    # Database Configuration
    database_dsn: PostgresDsn = Field(alias="database_url", default="postgresql+asyncpg://user:pass@host:5432/db")

    @property
    def debug(self) -> bool:
        """Check if application is running in debug mode.

        Returns:
            True if environment is development, testing, or staging.
        """
        return self.environment in (
            Environment.DEVELOPMENT,
            Environment.TESTING,
            Environment.STAGING,
        )

    @property
    def database_url(self) -> str:
        """Get database URL as string for SQLAlchemy.

        Returns:
            Database connection string.
        """
        return self.database_dns.unicode_string()


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings instance.

    Uses lru_cache to ensure settings are loaded only once.

    Returns:
        Singleton Settings instance.
    """
    return Settings()
