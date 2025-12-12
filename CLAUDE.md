# Argentina Real Estate Scraper - Guía para Claude

## Resumen del Proyecto

Scraper de portales inmobiliarios argentinos: **Argenprop**, **Zonaprop** y **MercadoLibre**.

## Estructura

```
argentina_scraper/
├── cli.py              # CLI con Typer (arscraper command)
├── config.py           # Settings via pydantic-settings (.env)
├── storage.py          # SQLite persistence, CSV export
├── models/
│   ├── property.py     # Pydantic model Property
│   └── database.py     # SQLAlchemy model PropertyDB
├── scrapers/
│   ├── base.py         # BaseScraper ABC
│   ├── argenprop.py    # httpx + BeautifulSoup (SSR, fácil)
│   ├── zonaprop.py     # Playwright + stealth (Cloudflare)
│   └── mercadolibre.py # API REST oficial
└── utils/
    └── helpers.py      # parse_price, parse_area, random_delay
```

## Estado de los Scrapers

| Scraper | Estado | Tecnología | Notas |
|---------|--------|------------|-------|
| Argenprop | ✅ Funciona | httpx + BS4 | SSR, sin protección anti-bot |
| Zonaprop | ✅ Funciona | Playwright | Cloudflare, usa `domcontentloaded` en vez de `networkidle` |
| MercadoLibre | ⚠️ Requiere Auth | httpx | API oficial, necesita OAuth token |

## Comandos CLI

```bash
# Activar entorno
source .venv/bin/activate

# Test rápido
arscraper test-scraper argenprop
arscraper test-scraper zonaprop

# Scraping
arscraper scrape argenprop -o rent -t apartment -l Palermo -p 5
arscraper scrape zonaprop -o sale -t house -p 2

# Base de datos
arscraper stats
arscraper export propiedades.csv
arscraper export --source argenprop solo_argenprop.csv
```

## Configuración (.env)

```bash
# Proxy (opcional, recomendado para scraping intensivo)
ARSCRAPER_PROXY_URL=http://user:pass@proxy:8080

# MercadoLibre API (registrar en developers.mercadolibre.com.ar)
ARSCRAPER_MELI_CLIENT_ID=xxx
ARSCRAPER_MELI_CLIENT_SECRET=xxx
ARSCRAPER_MELI_ACCESS_TOKEN=xxx

# Delays
ARSCRAPER_DEFAULT_DELAY_MIN=2.0
ARSCRAPER_DEFAULT_DELAY_MAX=5.0
```

## Problemas Conocidos y Soluciones

### Zonaprop timeout
- **Problema**: `networkidle` nunca completa por trackers
- **Solución**: Usar `domcontentloaded` + sleep manual (ya implementado)

### MercadoLibre 403
- **Problema**: API requiere autenticación
- **Solución**: Registrar app en developers.mercadolibre.com.ar, obtener token OAuth

### Precios no parseados en Zonaprop
- Los selectores de precio pueden necesitar actualización si Zonaprop cambia el HTML
- Revisar `_parse_listing()` en `zonaprop.py`

## Modelo de Datos

```python
Property:
  source: str           # argenprop, zonaprop, mercadolibre
  external_id: str      # ID del portal
  url: str
  title: str
  property_type: enum   # apartment, house, ph, land, office, local
  operation_type: enum  # rent, sale, temporary_rent
  price: float | None
  currency: str         # ARS, USD
  expenses: float | None
  address: str | None
  neighborhood: str | None
  city: str | None
  province: str
  latitude/longitude: float | None
  total_area/covered_area: float | None
  rooms/bedrooms/bathrooms/garages: int | None
  amenities: list[str]
  images: list[str]
  publisher: str | None
  scraped_at: datetime
```

## Dependencias Clave

- **scrapy-playwright**: Para Zonaprop (Cloudflare bypass)
- **httpx**: Cliente HTTP async para Argenprop y MercadoLibre API
- **beautifulsoup4 + lxml**: Parsing HTML
- **pydantic**: Validación de datos
- **sqlalchemy**: ORM para SQLite
- **typer + rich**: CLI bonito

## Para Continuar Desarrollo

1. **Mejorar parsing de Zonaprop**: Los selectores CSS pueden cambiar
2. **Implementar OAuth flow para MercadoLibre**: Actualmente solo acepta token manual
3. **Agregar más portales**: Properati, inmobiliarias individuales
4. **Scheduler**: Agregar opción de scraping periódico (cron/GitHub Actions)
5. **Notificaciones**: Telegram/email cuando aparecen nuevas propiedades
