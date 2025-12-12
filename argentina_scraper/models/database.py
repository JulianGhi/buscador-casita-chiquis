"""Database models and session management."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from argentina_scraper.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class PropertyDB(Base):
    """Property database model."""

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifiers
    source: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(100), index=True)
    url: Mapped[str] = mapped_column(Text)
    unique_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)

    # Basic info
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    property_type: Mapped[str] = mapped_column(String(50))
    operation_type: Mapped[str] = mapped_column(String(50))

    # Price
    price: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(10), default="ARS")
    expenses: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Location
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str] = mapped_column(String(100), default="Buenos Aires")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Features
    total_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    covered_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    garages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # JSON fields
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    images: Mapped[list] = mapped_column(JSON, default=list)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Metadata
    publisher: Mapped[str | None] = mapped_column(String(200), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


def get_engine():
    """Create database engine."""
    # Convert async URL to sync for regular SQLAlchemy
    url = settings.database_url.replace("sqlite+aiosqlite://", "sqlite://")
    return create_engine(url, echo=False)


def get_session():
    """Create database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
