"""MercadoLibre API client - uses official REST API (preferred over scraping)."""

from collections.abc import AsyncIterator
from datetime import datetime

import httpx

from argentina_scraper.config import settings
from argentina_scraper.models import OperationType, Property, PropertyType
from argentina_scraper.utils import random_delay


class MercadoLibreClient:
    """
    Client for MercadoLibre's official REST API.

    Using the API is preferred over scraping as MercadoLibre has aggressive
    anti-bot protection. The API provides rate limits of 1,500 req/min.

    API docs: https://developers.mercadolibre.com.ar
    """

    name = "mercadolibre"
    base_url = "https://api.mercadolibre.com"

    # Category IDs for real estate in Argentina (MLA)
    CATEGORIES = {
        "all": "MLA1459",  # Inmuebles
        "apartment": "MLA1472",  # Departamentos
        "house": "MLA1474",  # Casas
        "land": "MLA1475",  # Terrenos y lotes
        "office": "MLA1489",  # Oficinas
        "local": "MLA1476",  # Locales
        "ph": "MLA1473",  # PH
    }

    # Operation type filters
    OPERATIONS = {
        "rent": "242073",  # Alquiler
        "sale": "242074",  # Venta
        "temporary_rent": "242075",  # Alquiler temporal
    }

    def __init__(
        self,
        access_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        """
        Initialize API client.

        Args:
            access_token: Pre-existing access token (optional)
            client_id: App client ID for OAuth (optional)
            client_secret: App client secret for OAuth (optional)
        """
        self.access_token = access_token or settings.meli_access_token
        self.client_id = client_id or settings.meli_client_id
        self.client_secret = client_secret or settings.meli_client_secret
        self.client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"

            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0,
            )
        return self.client

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def search(
        self,
        operation: str = "rent",
        property_type: str = "apartment",
        location: str | None = None,
        neighborhood: str | None = None,
        max_results: int = 100,
        price_min: float | None = None,
        price_max: float | None = None,
        bedrooms: int | None = None,
    ) -> AsyncIterator[Property]:
        """
        Search for properties using MercadoLibre API.

        Args:
            operation: "rent", "sale", or "temporary_rent"
            property_type: "apartment", "house", "ph", "land", etc.
            location: City or state name
            neighborhood: Neighborhood name (more specific)
            max_results: Maximum number of results to return
            price_min: Minimum price filter
            price_max: Maximum price filter
            bedrooms: Number of bedrooms filter

        Yields:
            Property objects
        """
        client = await self._get_client()

        # Build query parameters
        params = {
            "category": self.CATEGORIES.get(property_type, self.CATEGORIES["all"]),
            "limit": 50,  # API max per page
            "offset": 0,
        }

        # Add operation filter
        if operation in self.OPERATIONS:
            params["OPERATION"] = self.OPERATIONS[operation]

        # Add location filters
        if neighborhood:
            params["q"] = neighborhood
        elif location:
            params["q"] = location

        # Add price filters
        if price_min is not None or price_max is not None:
            price_filter = ""
            if price_min is not None:
                price_filter += f"{price_min}"
            price_filter += "-"
            if price_max is not None:
                price_filter += f"{price_max}"
            params["price"] = price_filter

        # Add bedroom filter
        if bedrooms is not None:
            params["BEDROOMS"] = str(bedrooms)

        results_count = 0

        while results_count < max_results:
            try:
                response = await client.get("/sites/MLA/search", params=params)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError as e:
                print(f"API error: {e}")
                break

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                if results_count >= max_results:
                    break

                prop = self._parse_item(item, operation)
                if prop:
                    yield prop
                    results_count += 1

            # Check if there are more results
            paging = data.get("paging", {})
            total = paging.get("total", 0)
            offset = paging.get("offset", 0) + paging.get("limit", 50)

            if offset >= total or offset >= 1000:  # API limit
                break

            params["offset"] = offset

            # Respectful delay between pages
            await random_delay(0.5, 1.0)

    def _parse_item(self, item: dict, operation: str) -> Property | None:
        """Parse API item into Property."""
        try:
            external_id = item.get("id", "")
            url = item.get("permalink", "")

            # Title
            title = item.get("title", "Sin título")

            # Price
            price = item.get("price")
            currency = item.get("currency_id", "ARS")

            # Location
            location = item.get("location", {})
            address_parts = []
            if location.get("address_line"):
                address_parts.append(location["address_line"])
            neighborhood = location.get("neighborhood", {}).get("name")
            city = location.get("city", {}).get("name")
            state = location.get("state", {}).get("name", "Buenos Aires")

            if neighborhood:
                address_parts.append(neighborhood)
            if city:
                address_parts.append(city)

            address = ", ".join(address_parts) if address_parts else None

            # Coordinates
            latitude = location.get("latitude")
            longitude = location.get("longitude")

            # Features from attributes
            attributes = {
                attr.get("id"): attr.get("value_name")
                for attr in item.get("attributes", [])
            }

            total_area = self._parse_area(attributes.get("TOTAL_AREA"))
            covered_area = self._parse_area(attributes.get("COVERED_AREA"))
            rooms = self._parse_int(attributes.get("ROOMS"))
            bedrooms = self._parse_int(attributes.get("BEDROOMS"))
            bathrooms = self._parse_int(attributes.get("FULL_BATHROOMS"))
            garages = self._parse_int(attributes.get("PARKING_LOTS"))
            age = self._parse_int(attributes.get("PROPERTY_AGE"))

            # Images
            images = [
                pic.get("secure_url") or pic.get("url")
                for pic in item.get("pictures", [])
                if pic.get("secure_url") or pic.get("url")
            ][:10]

            # Property type from category
            property_type = self._get_property_type(item.get("category_id", ""))

            # Operation type
            operation_type = OperationType.RENT
            if operation == "sale":
                operation_type = OperationType.SALE
            elif operation == "temporary_rent":
                operation_type = OperationType.TEMPORARY_RENT

            # Publisher
            seller = item.get("seller", {})
            publisher = seller.get("nickname")

            # Date
            published_at = None
            date_str = item.get("start_time")
            if date_str:
                try:
                    published_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            return Property(
                source=self.name,
                external_id=external_id,
                url=url,
                title=title,
                property_type=property_type,
                operation_type=operation_type,
                price=price,
                currency=currency,
                address=address,
                neighborhood=neighborhood,
                city=city,
                province=state,
                latitude=latitude,
                longitude=longitude,
                total_area=total_area,
                covered_area=covered_area,
                rooms=rooms,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                garages=garages,
                age=age,
                images=images,
                publisher=publisher,
                published_at=published_at,
                raw_data=item,
            )

        except Exception as e:
            print(f"Error parsing MercadoLibre item: {e}")
            return None

    async def get_property(self, item_id: str) -> Property | None:
        """
        Get full details for a single property by ID.

        Args:
            item_id: MercadoLibre item ID (e.g., "MLA123456789")

        Returns:
            Property object or None
        """
        client = await self._get_client()

        try:
            response = await client.get(f"/items/{item_id}")
            response.raise_for_status()
            item = response.json()
        except httpx.HTTPError as e:
            print(f"API error fetching {item_id}: {e}")
            return None

        # Get description separately
        description = None
        try:
            desc_response = await client.get(f"/items/{item_id}/description")
            if desc_response.status_code == 200:
                desc_data = desc_response.json()
                description = desc_data.get("plain_text")
        except httpx.HTTPError:
            pass

        # Determine operation from attributes
        operation = "rent"
        for attr in item.get("attributes", []):
            if attr.get("id") == "OPERATION":
                op_value = attr.get("value_id", "")
                if "242074" in op_value:
                    operation = "sale"
                elif "242075" in op_value:
                    operation = "temporary_rent"
                break

        prop = self._parse_item(item, operation)
        if prop:
            prop.description = description

        return prop

    async def get_multiple(self, item_ids: list[str]) -> list[Property]:
        """
        Get multiple properties in a single API call (multiget).

        Args:
            item_ids: List of item IDs (max 20)

        Returns:
            List of Property objects
        """
        if not item_ids:
            return []

        # API limit is 20 items per request
        item_ids = item_ids[:20]

        client = await self._get_client()

        try:
            response = await client.get("/items", params={"ids": ",".join(item_ids)})
            response.raise_for_status()
            items = response.json()
        except httpx.HTTPError as e:
            print(f"API error in multiget: {e}")
            return []

        properties = []
        for item_data in items:
            if item_data.get("code") == 200:
                item = item_data.get("body", {})
                prop = self._parse_item(item, "rent")
                if prop:
                    properties.append(prop)

        return properties

    def _get_property_type(self, category_id: str) -> PropertyType:
        """Map category ID to PropertyType."""
        mapping = {
            "MLA1472": PropertyType.APARTMENT,
            "MLA1474": PropertyType.HOUSE,
            "MLA1473": PropertyType.PH,
            "MLA1475": PropertyType.LAND,
            "MLA1489": PropertyType.OFFICE,
            "MLA1476": PropertyType.LOCAL,
        }
        return mapping.get(category_id, PropertyType.OTHER)

    def _parse_area(self, value: str | None) -> float | None:
        """Parse area value from string."""
        if not value:
            return None
        try:
            # Remove units and convert
            cleaned = value.replace("m²", "").replace("m2", "").strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return None

    def _parse_int(self, value: str | None) -> int | None:
        """Parse integer from string."""
        if not value:
            return None
        try:
            return int(value)
        except (ValueError, AttributeError):
            return None
