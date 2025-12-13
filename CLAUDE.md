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

## Dashboard Web (docs/)

Dashboard interactivo en GitHub Pages para visualizar y filtrar propiedades.

### Estructura modular

```
docs/
├── index.html          # Entry point buscador
├── stats.html          # Página de estadísticas con gráfico
├── css/styles.css      # Animaciones CSS
└── js/
    ├── config.js       # Configuración, defaults, state, localStorage
    ├── utils.js        # Cálculos, parseCSV, badges, helpers
    ├── api.js          # fetchData, fetchDolarBNA, auto-refresh
    ├── components.js   # Todos los render* (header, table, cards, modal)
    ├── app.js          # Event handlers, render(), init() del buscador
    └── stats.js        # Lógica específica de stats (Chart.js)
```

### Funcionalidades del dashboard

- **Vista tabla/cards** con filtros (status, barrio, activo, apto crédito)
- **Sistema de tiers + score** para ordenar candidatos (ver abajo)
- **Vista detallada** con:
  - Slider de negociación de precio (0-15%)
  - Slider de dólar estimado ($900-$1500)
  - Desglose completo de costos (escribano, sellos, etc.)
  - Características y amenities
- **Página de stats** con gráfico precio vs m²
- **Cotización dólar BNA** en tiempo real

### Agregar propiedades (flujo completo)

```bash
source .venv/bin/activate
python sheets/sync_sheet.py pull      # 1. Traer datos de Google Sheets
# (agregar link en el JSON o en el Sheet)
python sheets/sync_sheet.py scrape    # 2. Scrapear datos de los links
# 3. IMPORTANTE: Completar datos manualmente (ver sheets/README.md)
#    - Abrir cada link y leer descripción
#    - Buscar: apto crédito, estado, terraza/balcón, ascensor
#    - Verificar coherencia de m2, expensas, piso
#    - Editar data/sheet_data.json
python sheets/sync_sheet.py view      # 4. Preview cambios
python sheets/sync_sheet.py push      # 5. Subir a Google Sheets
```

Ver `sheets/README.md` para documentación completa del sync.

### Sistema de valoración (Tiers + Score)

El ordenamiento "Mejor candidato" usa un sistema de **tiers** (niveles de prioridad) combinado con un **score** (puntuación dentro de cada tier).

#### Tiers (orden estricto)

| Tier | Condición | Color | Descripción |
|------|-----------|-------|-------------|
| T1 | activo + apto_credito=si + OK$ | Verde | Mejores candidatos: aceptan crédito y entran en presupuesto |
| T2 | activo + apto_credito=si + Caro | Azul | Buenos pero caros: aceptan crédito, hay que negociar |
| T3 | activo + apto_credito=? | Amarillo | Hay que averiguar si aceptan crédito |
| T4 | activo + apto_credito=no | Naranja | No aceptan crédito (difícil) |
| T5 | inactivo o sin link | Rojo | Descartadas |

#### Score (bonus dentro de cada tier)

Dentro de cada tier, las propiedades se ordenan por score. El score base depende del tier, y se suman bonus por:
- **Bajo precio de mercado**: +15 a +105 puntos según qué tan bajo (configurado por peso `bajo_mercado`)
- **Metros cuadrados**: +10 a +40 puntos según m² (configurado por peso `m2`)
- **Amenities**: terraza, balcón, cochera, luminosidad, disposición frente (+10 c/u × peso)
- **Completitud de datos**: +3 puntos por cada campo completo

#### Condiciones toggleables

En la pestaña "Ponderación" del panel de configuración se pueden habilitar/deshabilitar:
- **Activo**: Si se deshabilita, no filtra por estado del aviso
- **Apto crédito**: Si se deshabilita, ignora si acepta crédito o no
- **En presupuesto**: Si se deshabilita, ignora si entra en presupuesto o no

Al deshabilitar condiciones, los tiers se recalculan automáticamente (ej: sin apto_credito, solo queda activo+presupuesto).

#### Archivos relacionados

- `docs/js/config.js`: Define `DEFAULT_CONDITIONS` y `DEFAULT_WEIGHTS`
- `docs/js/utils.js`: Función `calculateProperty()` implementa tiers y score
- `docs/js/components.js`: Función `renderConfigPanel()` muestra UI de configuración

## Para Continuar Desarrollo

1. **Mejorar parsing de Zonaprop**: Los selectores CSS pueden cambiar
2. **Implementar OAuth flow para MercadoLibre**: Actualmente solo acepta token manual
3. **Agregar más portales**: Properati, inmobiliarias individuales
4. **Scheduler**: Agregar opción de scraping periódico (cron/GitHub Actions)
5. **Notificaciones**: Telegram/email cuando aparecen nuevas propiedades
