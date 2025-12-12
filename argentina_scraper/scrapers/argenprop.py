"""Argenprop scraper - SSR site, simple to scrape."""

import re
from collections.abc import AsyncIterator
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from argentina_scraper.config import settings
from argentina_scraper.models import OperationType, Property, PropertyType
from argentina_scraper.scrapers.base import BaseScraper
from argentina_scraper.utils import parse_area, parse_price, random_delay
from argentina_scraper.utils.helpers import clean_text, extract_number


class ArgenpropScraper(BaseScraper):
    """
    Scraper for Argenprop.com.

    Argenprop uses Server-Side Rendering (SSR), making it the easiest
    portal to scrape among Argentine real estate sites.
    """

    name = "argenprop"
    base_url = "https://www.argenprop.com"

    # Property type URL mappings
    PROPERTY_TYPES = {
        "apartment": "departamento",
        "house": "casa",
        "ph": "ph",
        "land": "terreno",
        "office": "oficina",
        "local": "local",
    }

    # Operation type URL mappings
    OPERATIONS = {
        "rent": "alquiler",
        "sale": "venta",
    }

    def __init__(self, proxy_url: str | None = None):
        """Initialize with HTTP client."""
        super().__init__(proxy_url)
        self.client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                },
                follow_redirects=True,
                timeout=30.0,
                proxy=self.proxy_url,
            )
        return self.client

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    def _build_search_url(
        self,
        operation: str,
        property_type: str,
        location: str | None = None,
        page: int = 1,
    ) -> str:
        """Build search URL from parameters."""
        op = self.OPERATIONS.get(operation, "alquiler")
        pt = self.PROPERTY_TYPES.get(property_type, "departamento")

        # Build URL path
        path_parts = [pt, op]

        if location:
            # Normalize location for URL (e.g., "Palermo" -> "barrio-palermo")
            loc_normalized = location.lower().replace(" ", "-")
            if not loc_normalized.startswith("barrio-"):
                loc_normalized = f"barrio-{loc_normalized}"
            path_parts.append(loc_normalized)

        if page > 1:
            path_parts.append(f"pagina-{page}")

        return f"{self.base_url}/{'-'.join(path_parts)}"

    async def search(
        self,
        operation: str = "rent",
        property_type: str = "apartment",
        location: str | None = None,
        max_pages: int = 10,
    ) -> AsyncIterator[Property]:
        """
        Search for properties on Argenprop.

        Args:
            operation: "rent" or "sale"
            property_type: "apartment", "house", "ph", etc.
            location: Neighborhood name (e.g., "Palermo", "Belgrano")
            max_pages: Maximum pages to scrape

        Yields:
            Property objects
        """
        client = await self._get_client()

        for page in range(1, max_pages + 1):
            url = self._build_search_url(operation, property_type, location, page)

            try:
                response = await client.get(url)
                response.raise_for_status()
            except httpx.HTTPError as e:
                print(f"Error fetching {url}: {e}")
                break

            soup = BeautifulSoup(response.text, "lxml")

            # Find listing items
            listings = soup.select("div.listing__items div.listing__item")

            if not listings:
                # Try alternative selector
                listings = soup.select("div.listing__item")

            if not listings:
                break  # No more results

            for listing in listings:
                prop = self._parse_listing(listing, operation)
                if prop:
                    yield prop

            # Respectful delay between pages
            await random_delay(2.0, 4.0)

    def _parse_listing(self, element, operation: str) -> Property | None:
        """Parse a listing element into a Property."""
        try:
            # Get link and URL
            link = element.select_one("a.card")
            if not link:
                link = element.select_one("a")

            if not link or not link.get("href"):
                return None

            url = urljoin(self.base_url, link["href"])

            # Extract ID from URL
            external_id = url.split("/")[-1] if "/" in url else url

            # Title
            title_elem = element.select_one(".card__title, h2, .listing__title")
            title = clean_text(title_elem.get_text()) if title_elem else "Sin título"

            # Price
            price_elem = element.select_one(".card__price, .listing__price")
            price, currency = parse_price(price_elem.get_text() if price_elem else None)

            # Location
            address_elem = element.select_one(".card__address, .listing__address")
            address = clean_text(address_elem.get_text()) if address_elem else None

            # Features
            features_elem = element.select_one(".card__main-features, .listing__features")
            features_text = features_elem.get_text() if features_elem else ""

            # Parse features
            total_area = None
            covered_area = None
            rooms = None
            bedrooms = None
            bathrooms = None

            if features_text:
                # Look for area patterns
                area_match = re.search(r"(\d+)\s*m[²2]", features_text)
                if area_match:
                    total_area = float(area_match.group(1))

                # Look for rooms/ambientes
                rooms_match = re.search(r"(\d+)\s*amb", features_text, re.IGNORECASE)
                if rooms_match:
                    rooms = int(rooms_match.group(1))

                # Bedrooms
                bed_match = re.search(r"(\d+)\s*(?:dorm|hab)", features_text, re.IGNORECASE)
                if bed_match:
                    bedrooms = int(bed_match.group(1))

                # Bathrooms
                bath_match = re.search(r"(\d+)\s*ba[ñn]", features_text, re.IGNORECASE)
                if bath_match:
                    bathrooms = int(bath_match.group(1))

            # Image
            images = []
            img_elem = element.select_one("img")
            if img_elem:
                img_src = img_elem.get("src") or img_elem.get("data-src")
                if img_src:
                    images.append(img_src)

            # Determine property type from URL or content
            property_type = PropertyType.APARTMENT
            url_lower = url.lower()
            if "casa" in url_lower:
                property_type = PropertyType.HOUSE
            elif "ph" in url_lower:
                property_type = PropertyType.PH
            elif "terreno" in url_lower:
                property_type = PropertyType.LAND
            elif "oficina" in url_lower:
                property_type = PropertyType.OFFICE
            elif "local" in url_lower:
                property_type = PropertyType.LOCAL

            return Property(
                source=self.name,
                external_id=external_id,
                url=url,
                title=title,
                property_type=property_type,
                operation_type=OperationType.RENT if operation == "rent" else OperationType.SALE,
                price=price,
                currency=currency,
                address=address,
                total_area=total_area,
                covered_area=covered_area,
                rooms=rooms,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                images=images,
            )

        except Exception as e:
            print(f"Error parsing listing: {e}")
            return None

    async def get_property(self, url: str) -> Property | None:
        """Get full details for a single property."""
        client = await self._get_client()

        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            print(f"Error fetching {url}: {e}")
            return None

        soup = BeautifulSoup(response.text, "lxml")

        # Extract ID from URL
        external_id = url.split("/")[-1]

        # Title
        title_elem = soup.select_one("h1.titlebar__title, h1")
        title = clean_text(title_elem.get_text()) if title_elem else "Sin título"

        # Description
        desc_elem = soup.select_one(".section-description--content, .description")
        description = clean_text(desc_elem.get_text()) if desc_elem else None

        # Price
        price_elem = soup.select_one(".titlebar__price, .price")
        price, currency = parse_price(price_elem.get_text() if price_elem else None)

        # Expenses
        expenses_elem = soup.select_one(".titlebar__expenses, .expenses")
        expenses, _ = parse_price(expenses_elem.get_text() if expenses_elem else None)

        # Address
        address_elem = soup.select_one(".titlebar__address, .address")
        address = clean_text(address_elem.get_text()) if address_elem else None

        # Features from the features section
        features = {}
        feature_items = soup.select(".property-features li, .features-item")
        for item in feature_items:
            text = item.get_text().lower()
            if "m²" in text or "m2" in text:
                area = parse_area(text)
                if area:
                    if "cub" in text:
                        features["covered_area"] = area
                    else:
                        features["total_area"] = area
            elif "amb" in text:
                features["rooms"] = extract_number(text)
            elif "dorm" in text or "hab" in text:
                features["bedrooms"] = extract_number(text)
            elif "baño" in text or "bano" in text:
                features["bathrooms"] = extract_number(text)
            elif "coch" in text or "garag" in text:
                features["garages"] = extract_number(text)
            elif "año" in text or "ano" in text:
                features["age"] = extract_number(text)

        # Images
        images = []
        gallery = soup.select(".gallery img, .carousel img, [data-src]")
        for img in gallery:
            src = img.get("src") or img.get("data-src")
            if src and "placeholder" not in src.lower():
                images.append(src)

        # Amenities
        amenities = []
        amenity_items = soup.select(".property-amenities li, .amenities-item")
        for item in amenity_items:
            text = clean_text(item.get_text())
            if text:
                amenities.append(text)

        # Determine operation and property type from URL
        operation_type = OperationType.RENT if "alquiler" in url.lower() else OperationType.SALE

        property_type = PropertyType.APARTMENT
        url_lower = url.lower()
        if "casa" in url_lower:
            property_type = PropertyType.HOUSE
        elif "ph" in url_lower:
            property_type = PropertyType.PH
        elif "terreno" in url_lower:
            property_type = PropertyType.LAND

        return Property(
            source=self.name,
            external_id=external_id,
            url=url,
            title=title,
            description=description,
            property_type=property_type,
            operation_type=operation_type,
            price=price,
            currency=currency,
            expenses=expenses,
            address=address,
            total_area=features.get("total_area"),
            covered_area=features.get("covered_area"),
            rooms=features.get("rooms"),
            bedrooms=features.get("bedrooms"),
            bathrooms=features.get("bathrooms"),
            garages=features.get("garages"),
            age=features.get("age"),
            amenities=amenities,
            images=images[:10],  # Limit images
        )
