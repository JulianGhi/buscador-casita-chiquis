# Argentina Real Estate Scraper

Web scraper for Argentine real estate portals: **Argenprop**, **Zonaprop**, and **MercadoLibre**.

## Features

- **Argenprop**: Simple HTTP scraper (SSR site, no anti-bot protection)
- **Zonaprop**: Playwright-based scraper with stealth techniques (Cloudflare bypass)
- **MercadoLibre**: Official REST API client (recommended over scraping)
- SQLite database for persistent storage
- CSV export functionality
- CLI interface with progress indicators

## Installation

```bash
# Clone and install
cd argentina-real-estate-scraper
pip install -e .

# For Zonaprop (requires Playwright)
playwright install chromium
```

## Quick Start

```bash
# Test a scraper
arscraper test-scraper argenprop

# Scrape Argenprop apartments for rent in Palermo
arscraper scrape argenprop --operation rent --type apartment --location Palermo --pages 5

# Scrape Zonaprop houses for sale
arscraper scrape zonaprop --operation sale --type house --pages 3

# Fetch from MercadoLibre API
arscraper scrape mercadolibre --operation rent --type apartment --pages 2

# View statistics
arscraper stats

# Export to CSV
arscraper export properties.csv
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key settings:
- `ARSCRAPER_PROXY_URL`: Residential proxy for avoiding blocks
- `ARSCRAPER_MELI_*`: MercadoLibre API credentials for higher rate limits

## Portal Difficulty

| Portal | Difficulty | Method | Notes |
|--------|------------|--------|-------|
| Argenprop | Easy | HTTP requests | SSR, no protection |
| Zonaprop | Medium | Playwright + stealth | Cloudflare, needs delays |
| MercadoLibre | API | REST API | 1,500 req/min limit |

## Legal Notice

Web scraping may violate the Terms of Service of these portals. This tool is for educational and personal use only. Use responsibly with appropriate delays.

## License

MIT
