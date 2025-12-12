"""Property data model."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PropertyType(str, Enum):
    """Type of property."""

    APARTMENT = "apartment"
    HOUSE = "house"
    PH = "ph"
    LAND = "land"
    OFFICE = "office"
    LOCAL = "local"
    WAREHOUSE = "warehouse"
    OTHER = "other"


class OperationType(str, Enum):
    """Type of operation."""

    SALE = "sale"
    RENT = "rent"
    TEMPORARY_RENT = "temporary_rent"


class Property(BaseModel):
    """Unified property model for all scrapers."""

    # Identifiers
    source: str = Field(..., description="Source portal (argenprop, zonaprop, mercadolibre)")
    external_id: str = Field(..., description="ID from the source portal")
    url: str = Field(..., description="URL of the listing")

    # Basic info
    title: str
    description: str | None = None
    property_type: PropertyType = PropertyType.OTHER
    operation_type: OperationType

    # Price
    price: float | None = None
    currency: str = "ARS"
    expenses: float | None = None

    # Location
    address: str | None = None
    neighborhood: str | None = None
    city: str | None = None
    province: str = "Buenos Aires"
    latitude: float | None = None
    longitude: float | None = None

    # Features
    total_area: float | None = Field(None, description="Total area in m²")
    covered_area: float | None = Field(None, description="Covered area in m²")
    rooms: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    garages: int | None = None
    age: int | None = Field(None, description="Age in years")

    # Amenities
    amenities: list[str] = Field(default_factory=list)

    # Images
    images: list[str] = Field(default_factory=list)

    # Metadata
    publisher: str | None = None
    published_at: datetime | None = None
    scraped_at: datetime = Field(default_factory=datetime.now)

    # Raw data for debugging
    raw_data: dict | None = None

    @property
    def unique_key(self) -> str:
        """Generate a unique key for deduplication."""
        return f"{self.source}:{self.external_id}"
