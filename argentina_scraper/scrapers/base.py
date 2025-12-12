"""Base scraper class."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from argentina_scraper.config import settings
from argentina_scraper.models import Property


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    name: str = "base"
    base_url: str = ""

    def __init__(self, proxy_url: str | None = None):
        """Initialize scraper with optional proxy."""
        self.proxy_url = proxy_url or settings.proxy_url
        self.user_agent = settings.user_agent

    @abstractmethod
    async def search(
        self,
        operation: str = "rent",
        property_type: str = "apartment",
        location: str | None = None,
        max_pages: int = 10,
    ) -> AsyncIterator[Property]:
        """
        Search for properties.

        Args:
            operation: "rent" or "sale"
            property_type: "apartment", "house", "ph", etc.
            location: Neighborhood or city name
            max_pages: Maximum number of pages to scrape

        Yields:
            Property objects
        """
        pass

    @abstractmethod
    async def get_property(self, url: str) -> Property | None:
        """
        Get details for a single property.

        Args:
            url: URL of the property listing

        Returns:
            Property object or None if not found
        """
        pass

    async def close(self) -> None:
        """Clean up resources."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
