"""Scrapers for Argentine real estate portals."""

from argentina_scraper.scrapers.base import BaseScraper
from argentina_scraper.scrapers.argenprop import ArgenpropScraper
from argentina_scraper.scrapers.zonaprop import ZonapropScraper
from argentina_scraper.scrapers.mercadolibre import MercadoLibreClient

__all__ = ["BaseScraper", "ArgenpropScraper", "ZonapropScraper", "MercadoLibreClient"]
