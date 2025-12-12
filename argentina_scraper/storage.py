"""Storage utilities for persisting scraped data."""

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from argentina_scraper.models import Property
from argentina_scraper.models.database import PropertyDB, get_session, init_db


def save_property(prop: Property) -> bool:
    """
    Save a property to the database, updating if it already exists.

    Args:
        prop: Property to save

    Returns:
        True if inserted, False if updated
    """
    session = get_session()

    try:
        # Use SQLite upsert
        stmt = sqlite_insert(PropertyDB).values(
            source=prop.source,
            external_id=prop.external_id,
            url=prop.url,
            unique_key=prop.unique_key,
            title=prop.title,
            description=prop.description,
            property_type=prop.property_type.value,
            operation_type=prop.operation_type.value,
            price=prop.price,
            currency=prop.currency,
            expenses=prop.expenses,
            address=prop.address,
            neighborhood=prop.neighborhood,
            city=prop.city,
            province=prop.province,
            latitude=prop.latitude,
            longitude=prop.longitude,
            total_area=prop.total_area,
            covered_area=prop.covered_area,
            rooms=prop.rooms,
            bedrooms=prop.bedrooms,
            bathrooms=prop.bathrooms,
            garages=prop.garages,
            age=prop.age,
            amenities=prop.amenities,
            images=prop.images,
            raw_data=prop.raw_data,
            publisher=prop.publisher,
            published_at=prop.published_at,
            scraped_at=prop.scraped_at,
        )

        # On conflict, update most fields but keep original scraped_at
        stmt = stmt.on_conflict_do_update(
            index_elements=["unique_key"],
            set_={
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "price": stmt.excluded.price,
                "currency": stmt.excluded.currency,
                "expenses": stmt.excluded.expenses,
                "address": stmt.excluded.address,
                "neighborhood": stmt.excluded.neighborhood,
                "city": stmt.excluded.city,
                "latitude": stmt.excluded.latitude,
                "longitude": stmt.excluded.longitude,
                "total_area": stmt.excluded.total_area,
                "covered_area": stmt.excluded.covered_area,
                "rooms": stmt.excluded.rooms,
                "bedrooms": stmt.excluded.bedrooms,
                "bathrooms": stmt.excluded.bathrooms,
                "garages": stmt.excluded.garages,
                "age": stmt.excluded.age,
                "amenities": stmt.excluded.amenities,
                "images": stmt.excluded.images,
                "raw_data": stmt.excluded.raw_data,
                "publisher": stmt.excluded.publisher,
                "published_at": stmt.excluded.published_at,
            },
        )

        result = session.execute(stmt)
        session.commit()

        return result.rowcount == 1

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_properties(properties: list[Property]) -> tuple[int, int]:
    """
    Save multiple properties to the database.

    Args:
        properties: List of properties to save

    Returns:
        Tuple of (inserted_count, updated_count)
    """
    inserted = 0
    updated = 0

    for prop in properties:
        try:
            if save_property(prop):
                inserted += 1
            else:
                updated += 1
        except Exception as e:
            print(f"Error saving property {prop.unique_key}: {e}")

    return inserted, updated


def get_property_count(source: str | None = None) -> int:
    """Get count of properties in database."""
    session = get_session()
    try:
        query = session.query(PropertyDB)
        if source:
            query = query.filter(PropertyDB.source == source)
        return query.count()
    finally:
        session.close()


def property_exists(source: str, external_id: str) -> bool:
    """Check if a property already exists in the database."""
    session = get_session()
    try:
        unique_key = f"{source}:{external_id}"
        return session.query(PropertyDB).filter(PropertyDB.unique_key == unique_key).first() is not None
    finally:
        session.close()


def export_to_csv(filepath: str, source: str | None = None) -> int:
    """
    Export properties to CSV file.

    Args:
        filepath: Path to output CSV file
        source: Optional source filter

    Returns:
        Number of rows exported
    """
    import csv

    session = get_session()
    try:
        query = session.query(PropertyDB)
        if source:
            query = query.filter(PropertyDB.source == source)

        properties = query.all()

        if not properties:
            return 0

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "source", "external_id", "url", "title", "property_type",
                "operation_type", "price", "currency", "expenses",
                "address", "neighborhood", "city", "province",
                "latitude", "longitude", "total_area", "covered_area",
                "rooms", "bedrooms", "bathrooms", "garages", "age",
                "publisher", "published_at", "scraped_at"
            ])

            # Data rows
            for p in properties:
                writer.writerow([
                    p.source, p.external_id, p.url, p.title, p.property_type,
                    p.operation_type, p.price, p.currency, p.expenses,
                    p.address, p.neighborhood, p.city, p.province,
                    p.latitude, p.longitude, p.total_area, p.covered_area,
                    p.rooms, p.bedrooms, p.bathrooms, p.garages, p.age,
                    p.publisher, p.published_at, p.scraped_at
                ])

        return len(properties)

    finally:
        session.close()


# Initialize database on import
init_db()
