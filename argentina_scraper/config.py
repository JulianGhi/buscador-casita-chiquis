"""Configuration settings for the scraper."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite+aiosqlite:///properties.db"

    # Scraping defaults
    default_delay_min: float = 2.0
    default_delay_max: float = 5.0
    max_concurrent_requests: int = 1

    # Proxy settings (optional)
    proxy_url: str | None = None

    # MercadoLibre API
    meli_client_id: str | None = None
    meli_client_secret: str | None = None
    meli_access_token: str | None = None

    # User agent
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    model_config = {"env_file": ".env", "env_prefix": "ARSCRAPER_"}


settings = Settings()
