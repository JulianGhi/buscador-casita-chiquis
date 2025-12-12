"""Zonaprop scraper - requires Playwright with stealth for Cloudflare bypass."""

import asyncio
import re
from collections.abc import AsyncIterator
from urllib.parse import urljoin

from argentina_scraper.config import settings
from argentina_scraper.models import OperationType, Property, PropertyType
from argentina_scraper.scrapers.base import BaseScraper
from argentina_scraper.utils import parse_area, parse_price, random_delay
from argentina_scraper.utils.helpers import clean_text, extract_number


class ZonapropScraper(BaseScraper):
    """
    Scraper for Zonaprop.com.ar.

    Zonaprop uses Cloudflare protection and requires headless browser
    with stealth techniques to bypass bot detection.
    """

    name = "zonaprop"
    base_url = "https://www.zonaprop.com.ar"

    # Property type URL mappings
    PROPERTY_TYPES = {
        "apartment": "departamentos",
        "house": "casas",
        "ph": "ph",
        "land": "terrenos",
        "office": "oficinas",
        "local": "locales-comerciales",
    }

    # Operation type URL mappings
    OPERATIONS = {
        "rent": "alquiler",
        "sale": "venta",
    }

    def __init__(self, proxy_url: str | None = None):
        """Initialize scraper."""
        super().__init__(proxy_url)
        self.browser = None
        self.context = None
        self.page = None

    async def _init_browser(self):
        """Initialize Playwright browser with stealth settings."""
        if self.browser is not None:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for Zonaprop. "
                "Install with: pip install playwright && playwright install chromium"
            )

        self._playwright = await async_playwright().start()

        # Launch browser with stealth settings
        self.browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        # Create context with realistic settings
        self.context = await self.browser.new_context(
            user_agent=self.user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="es-AR",
            timezone_id="America/Argentina/Buenos_Aires",
            proxy={"server": self.proxy_url} if self.proxy_url else None,
        )

        # Add stealth scripts to evade detection
        await self.context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-AR', 'es', 'en']
            });

            // Mock Chrome runtime
            window.chrome = {
                runtime: {}
            };
        """)

        self.page = await self.context.new_page()

    async def close(self) -> None:
        """Close browser and clean up."""
        if self.page:
            await self.page.close()
            self.page = None
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if hasattr(self, "_playwright"):
            await self._playwright.stop()

    def _build_search_url(
        self,
        operation: str,
        property_type: str,
        location: str | None = None,
        page: int = 1,
    ) -> str:
        """Build search URL from parameters."""
        pt = self.PROPERTY_TYPES.get(property_type, "departamentos")
        op = self.OPERATIONS.get(operation, "alquiler")

        # Build URL
        path = f"/{pt}-{op}"

        if location:
            # Normalize location for URL
            loc_normalized = location.lower().replace(" ", "-")
            path += f"-{loc_normalized}"

        path += ".html"

        if page > 1:
            path = path.replace(".html", f"-pagina-{page}.html")

        return f"{self.base_url}{path}"

    async def search(
        self,
        operation: str = "rent",
        property_type: str = "apartment",
        location: str | None = None,
        max_pages: int = 10,
    ) -> AsyncIterator[Property]:
        """
        Search for properties on Zonaprop.

        Args:
            operation: "rent" or "sale"
            property_type: "apartment", "house", "ph", etc.
            location: Neighborhood or city name
            max_pages: Maximum pages to scrape (note: robots.txt limits to pages 2-5)

        Yields:
            Property objects
        """
        await self._init_browser()

        for page_num in range(1, max_pages + 1):
            url = self._build_search_url(operation, property_type, location, page_num)

            try:
                # Navigate - use domcontentloaded instead of networkidle (faster, avoids tracker timeout)
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Wait for page to stabilize
                await asyncio.sleep(2)

                # Check if we hit a Cloudflare challenge page
                content = await self.page.content()
                if "challenge" in content.lower() or "checking your browser" in content.lower():
                    # Wait for challenge to resolve
                    await asyncio.sleep(5)
                    content = await self.page.content()

                # Wait for listings to load
                try:
                    await self.page.wait_for_selector(
                        "[data-qa='posting CARD'], .PostingCardLayout-sc, div[data-posting-type]",
                        timeout=10000,
                    )
                except Exception:
                    # Try alternative selectors
                    try:
                        await self.page.wait_for_selector(
                            "div.postings-container, div[class*='Posting']",
                            timeout=5000,
                        )
                    except Exception:
                        # No listings found
                        break

            except Exception as e:
                print(f"Error loading {url}: {e}")
                break

            # Parse listings from the page - try multiple selectors
            listings = await self.page.query_selector_all(
                "div[data-posting-type], div[data-qa='posting CARD'], .PostingCardLayout-sc"
            )

            if not listings:
                # Try alternative selector
                listings = await self.page.query_selector_all(
                    "div[class*='PostingCard'], a[data-to-posting]"
                )

            if not listings:
                break

            for listing in listings:
                prop = await self._parse_listing(listing, operation)
                if prop:
                    yield prop

            # Respectful delay
            await random_delay(3.0, 5.0)

    async def _parse_listing(self, element, operation: str) -> Property | None:
        """Parse a listing element into a Property."""
        try:
            # Get link
            link = await element.query_selector("a")
            if not link:
                return None

            href = await link.get_attribute("href")
            if not href:
                return None

            url = urljoin(self.base_url, href)

            # Extract ID from URL or data attribute
            external_id = await element.get_attribute("data-id")
            if not external_id:
                # Try to extract from URL
                match = re.search(r"-(\d+)\.html", url)
                external_id = match.group(1) if match else url.split("/")[-1]

            # Title
            title_elem = await element.query_selector(
                "[data-qa='posting-title'], .posting-title, h2"
            )
            title = await title_elem.inner_text() if title_elem else "Sin título"

            # Price
            price_elem = await element.query_selector(
                "[data-qa='posting-price'], .posting-price, .price"
            )
            price_text = await price_elem.inner_text() if price_elem else ""
            price, currency = parse_price(price_text)

            # Location/Address
            address_elem = await element.query_selector(
                "[data-qa='posting-location'], .posting-location, .location"
            )
            address = await address_elem.inner_text() if address_elem else None

            # Features
            features_elem = await element.query_selector(
                "[data-qa='posting-main-features'], .posting-features, .main-features"
            )
            features_text = await features_elem.inner_text() if features_elem else ""

            # Parse features
            total_area = None
            rooms = None
            bedrooms = None
            bathrooms = None

            if features_text:
                # Area
                area_match = re.search(r"(\d+)\s*m[²2]", features_text)
                if area_match:
                    total_area = float(area_match.group(1))

                # Rooms/Ambientes
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
            img_elem = await element.query_selector("img")
            if img_elem:
                img_src = await img_elem.get_attribute("src")
                if img_src:
                    images.append(img_src)

            # Determine property type from URL
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
                title=clean_text(title),
                property_type=property_type,
                operation_type=OperationType.RENT if operation == "rent" else OperationType.SALE,
                price=price,
                currency=currency,
                address=clean_text(address),
                total_area=total_area,
                rooms=rooms,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                images=images,
            )

        except Exception as e:
            print(f"Error parsing Zonaprop listing: {e}")
            return None

    async def get_property(self, url: str) -> Property | None:
        """Get full details for a single property."""
        await self._init_browser()

        try:
            await self.page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)  # Wait for Cloudflare

            # Wait for content
            await self.page.wait_for_selector(
                "[data-qa='section-title'], .property-title, h1",
                timeout=15000,
            )

        except Exception as e:
            print(f"Error loading {url}: {e}")
            return None

        # Extract ID from URL
        match = re.search(r"-(\d+)\.html", url)
        external_id = match.group(1) if match else url.split("/")[-1]

        # Title
        title_elem = await self.page.query_selector(
            "[data-qa='section-title'], .property-title, h1"
        )
        title = await title_elem.inner_text() if title_elem else "Sin título"

        # Description
        desc_elem = await self.page.query_selector(
            "[data-qa='section-description'], .property-description, .description"
        )
        description = await desc_elem.inner_text() if desc_elem else None

        # Price
        price_elem = await self.page.query_selector(
            "[data-qa='price'], .property-price, .price"
        )
        price_text = await price_elem.inner_text() if price_elem else ""
        price, currency = parse_price(price_text)

        # Expenses
        expenses_elem = await self.page.query_selector(
            "[data-qa='expenses'], .expenses"
        )
        expenses_text = await expenses_elem.inner_text() if expenses_elem else ""
        expenses, _ = parse_price(expenses_text)

        # Address
        address_elem = await self.page.query_selector(
            "[data-qa='location'], .property-location, .location"
        )
        address = await address_elem.inner_text() if address_elem else None

        # Features
        features = {}
        feature_items = await self.page.query_selector_all(
            "[data-qa='feature'], .feature-item, .property-feature"
        )
        for item in feature_items:
            text = (await item.inner_text()).lower()
            if "m²" in text or "m2" in text:
                area = parse_area(text)
                if area:
                    if "cub" in text:
                        features["covered_area"] = area
                    else:
                        features["total_area"] = area
            elif "amb" in text:
                features["rooms"] = extract_number(text)
            elif "dorm" in text:
                features["bedrooms"] = extract_number(text)
            elif "baño" in text:
                features["bathrooms"] = extract_number(text)
            elif "coch" in text or "garag" in text:
                features["garages"] = extract_number(text)

        # Images
        images = []
        img_elements = await self.page.query_selector_all(
            ".gallery img, .carousel img, [data-qa='gallery'] img"
        )
        for img in img_elements[:10]:
            src = await img.get_attribute("src")
            if src and "placeholder" not in src.lower():
                images.append(src)

        # Amenities
        amenities = []
        amenity_items = await self.page.query_selector_all(
            "[data-qa='amenity'], .amenity-item"
        )
        for item in amenity_items:
            text = clean_text(await item.inner_text())
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
            title=clean_text(title),
            description=clean_text(description),
            property_type=property_type,
            operation_type=operation_type,
            price=price,
            currency=currency,
            expenses=expenses,
            address=clean_text(address),
            total_area=features.get("total_area"),
            covered_area=features.get("covered_area"),
            rooms=features.get("rooms"),
            bedrooms=features.get("bedrooms"),
            bathrooms=features.get("bathrooms"),
            garages=features.get("garages"),
            amenities=amenities,
            images=images,
        )
