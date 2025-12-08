"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Neighborhood Story Weaver"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ipswich_stories"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/ipswich_stories"

    # External APIs
    weather_api_key: Optional[str] = None
    weather_api_base_url: str = "https://api.openweathermap.org/data/2.5"

    # LLM API (Anthropic Claude)
    anthropic_api_key: Optional[str] = None
    llm_model: str = "claude-sonnet-4-20250514"
    use_llm_for_stories: bool = True  # If True and API key present, use LLM

    # Ipswich, MA coordinates
    ipswich_lat: float = 42.6792
    ipswich_lon: float = -70.8412
    ipswich_location_name: str = "Ipswich, MA"

    # Tide API (NOAA station for Ipswich Bay area)
    tide_station_id: str = "8443970"  # Boston - closest major station
    tide_api_base_url: str = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

    # Feature flags
    enable_story_regen_endpoint: bool = True
    enable_manual_generation: bool = True

    # Story generation
    max_news_items_per_story: int = 3
    story_generation_hour: int = 11  # 11 AM ET

    # News scraping
    news_source_url: str = "https://thelocalnews.news/category/ipswich/"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
