"""Helper utilities for scraping."""

import asyncio
import random
import re

from argentina_scraper.config import settings


async def random_delay(min_seconds: float | None = None, max_seconds: float | None = None) -> None:
    """Sleep for a random duration between min and max seconds."""
    min_s = min_seconds or settings.default_delay_min
    max_s = max_seconds or settings.default_delay_max
    delay = random.uniform(min_s, max_s)
    await asyncio.sleep(delay)


def parse_price(text: str | None) -> tuple[float | None, str]:
    """
    Parse price text and extract amount and currency.

    Returns:
        Tuple of (price, currency)
    """
    if not text:
        return None, "ARS"

    text = text.strip().upper()

    # Detect currency
    currency = "ARS"
    if "USD" in text or "U$S" in text or "US$" in text or text.startswith("$"):
        if "USD" in text or "U$S" in text or "US$" in text:
            currency = "USD"

    # Remove currency symbols and text
    cleaned = re.sub(r"[USD$\s.,]|U\$S|US\$", "", text)

    # Handle thousand separators (Argentine format: 1.000.000 or 1,000,000)
    text_for_parse = text.replace("USD", "").replace("U$S", "").replace("US$", "").strip()

    # Try to find number pattern
    match = re.search(r"[\d.,]+", text_for_parse)
    if match:
        number_str = match.group()
        # Normalize: if uses dots as thousands separator
        if number_str.count(".") > 1 or (number_str.count(".") == 1 and len(number_str.split(".")[-1]) == 3):
            number_str = number_str.replace(".", "")
        # Handle comma as decimal separator
        number_str = number_str.replace(",", ".")
        try:
            return float(number_str), currency
        except ValueError:
            pass

    return None, currency


def parse_area(text: str | None) -> float | None:
    """Parse area text and extract square meters."""
    if not text:
        return None

    # Remove common suffixes and clean
    text = text.lower().replace("m²", "").replace("m2", "").replace("mts", "").strip()

    # Find number
    match = re.search(r"[\d.,]+", text)
    if match:
        number_str = match.group().replace(".", "").replace(",", ".")
        try:
            return float(number_str)
        except ValueError:
            pass

    return None


def extract_number(text: str | None) -> int | None:
    """Extract first integer from text."""
    if not text:
        return None

    match = re.search(r"\d+", text)
    if match:
        return int(match.group())
    return None


def clean_text(text: str | None) -> str | None:
    """Clean and normalize text."""
    if not text:
        return None

    # Remove extra whitespace
    text = " ".join(text.split())
    return text.strip() or None
