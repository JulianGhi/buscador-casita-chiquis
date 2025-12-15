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

### MercadoLibre 403 / Rate Limiting
- **Problema**: MercadoLibre bloquea requests después de muchas seguidas (rate limiting)
- **Síntomas**: Status 403, o "No se pudo extraer precio"
- **Solución**: Usar cache (evitar `--no-cache`), esperar unas horas, o usar proxy
- **Nota**: El scraper usa headers mejorados (Sec-Ch-Ua, Sec-Fetch-*, etc.) para simular navegador real

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
- **Columnas**: tier/score, activo, apto, status, barrio, dirección, tipo, precio, m², m² desc, $/m², vs ref, a juntar, OK, cocheras, terraza, balcón, baños
- **Sistema de tiers + score** para ordenar candidatos (ver abajo)
- **Vista detallada** con:
  - Slider de negociación de precio (0-15%)
  - Slider de dólar estimado ($900-$2000)
  - **Calculadora de quita necesaria**: Si no alcanza el presupuesto, muestra cuánto % y USD hay que negociar para que entre
  - Desglose completo de costos (escribano, sellos, etc.)
  - Indicador de datos faltantes (qué atributos faltan y penalizan el score)
  - Características: tipo, ambientes, m² totales/desc, baños, antigüedad, estado, expensas, disposición, piso, etc.
  - Rating personal y fechas (publicado, contacto, visita)
- **Página de stats** con gráfico precio vs m²
- **Cotización dólar BNA** en tiempo real

### Agregar propiedades (flujo completo)

```bash
source .venv/bin/activate
python sheets/sync_sheet.py pull      # 1. Traer datos de Google Sheets
# (agregar link en el JSON o en el Sheet)
python sheets/sync_sheet.py scrape    # 2. Scrapear datos de los links
python sheets/sync_sheet.py view      # 3. Preview cambios
python sheets/sync_sheet.py push      # 4. Subir a Google Sheets
```

**Flags útiles del scraper:**
```bash
python sheets/sync_sheet.py scrape --all        # Re-scrapea todos (no solo faltantes)
python sheets/sync_sheet.py scrape --no-cache   # Ignora cache
python sheets/sync_sheet.py scrape --update     # Sobrescribe valores existentes
python sheets/sync_sheet.py scrape --all --no-cache --update  # Full refresh
```

**Sistema de validaciones:** Al final del scrape muestra warnings de:
- m² inconsistentes (cub > tot, o cub + desc ≠ tot)
- Atributos inciertos (terraza/balcon detectado pero valor ambiguo → "?")
- Datos faltantes (sin barrio, sin m²)
- Precios sospechosos

**Detección de si/no:** El scraper usa `ATTR_PATTERNS` en `sync_sheet.py` para detectar
correctamente valores como "terraza: no" (antes se marcaba como "si" incorrectamente).

Ver `sheets/README.md` para documentación completa del sync.

### Sistema de Prints (Backups PDF)

Sistema para guardar backups PDF de los avisos y trackear su estado.

#### Pipeline de prints

```bash
source .venv/bin/activate
python sheets/sync_sheet.py prints     # Ver estado de prints
# Guardar PDF manualmente (Ctrl+P en navegador)
# Nombrar: {ID}_{FECHA}.pdf (ej: MLA123456_2025-12-15.pdf)
python sheets/sync_sheet.py push       # Sincroniza fecha_print al Sheet
```

#### Nomenclatura de archivos

| Formato | Ejemplo | Descripción |
|---------|---------|-------------|
| `{ID}_{FECHA}.pdf` | `MLA123456_2025-12-15.pdf` | ✅ Recomendado |
| `{ID}.pdf` | `AP17094976.pdf` | Válido, sin fecha |
| Título del aviso | `Depto 3 amb Caballito.pdf` | Se matchea por contenido |

Los IDs se extraen automáticamente del link:
- MercadoLibre: `MLA-123456789` → `MLA123456789`
- Argenprop: `...--17094976` → `AP17094976`
- Zonaprop: `...--12345678.html` → `ZP12345678`

#### Comandos

```bash
python sheets/sync_sheet.py prints           # Estado general
python sheets/sync_sheet.py pendientes       # Datos faltantes + sin print
python sheets/sync_sheet.py pendientes --sin-print  # Solo sin print
```

#### Detección automática

El sistema detecta prints por:
1. **ID en nombre del archivo** - Busca MLA/AP/ZP en el nombre
2. **Contenido del PDF** - Lee el PDF y extrae URLs/IDs
3. **Matching por dirección** - Compara direcciones del archivo con el sheet

#### Estados en el dashboard

| Icono | Significado |
|-------|-------------|
| 📄 (verde) | Print actualizado (< 30 días) |
| 📄 (ámbar) | Print desactualizado (> 30 días) |
| ○ (gris) | Sin print |

#### Archivos

```
data/prints/
├── index.json           # Índice de prints (generado automáticamente)
├── MLA123456_2025-12-15.pdf
├── AP17094976_2025-12-15.png
└── ...
```

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

#### Score (bonus/penalidad dentro de cada tier)

Dentro de cada tier, las propiedades se ordenan por score. **Datos faltantes penalizan** (asumimos lo peor si no está verificado).

**Sistema de 3 estados:**
| Estado | Score | Significado |
|--------|-------|-------------|
| `"si"` | +bonus × peso | Verificado que tiene el atributo |
| `"no"` | 0 | Verificado que NO tiene (neutro) |
| `""` / `"?"` / missing | -penalidad × peso | No sabemos, asumimos lo peor |

**Pesos configurables (11 atributos):**

| Peso | Qué prioriza | Bonus si cumple |
|------|--------------|-----------------|
| 💰 Bajo mercado | Precio bajo vs barrio | +15 a +105 pts si <15% bajo ref |
| 📐 M² grandes | Más m² cubiertos | +40 pts si ≥70m², +20 si ≥50m² |
| 🚪 Ambientes | 3+ ambientes | +24 pts si 4+, +12 si 3 |
| 🚿 Baños | 2+ baños | +12 pts si 2+ |
| ✨ Nuevo | Menos antigüedad | +30 pts si a estrenar, +18 si <15 años |
| 💵 Exp. bajas | Expensas bajas | +16 pts si $0, +10 si <$80k |
| 🌿 Terraza | Tiene terraza | +10 × peso |
| 🏠 Balcón | Tiene balcón | +10 × peso |
| 🚗 Cochera | Tiene cochera | +10 × peso |
| ☀️ Luminoso | Es luminoso | +10 × peso |
| 🪟 Al frente | Disposición frente | +10 × peso |

**Penalidad por dato faltante:** -3 a -5 × peso (incentiva completar datos)

#### Condiciones toggleables

En la pestaña "Ponderación" del panel de configuración se pueden habilitar/deshabilitar:
- **Activo**: Si se deshabilita, no filtra por estado del aviso
- **Apto crédito**: Si se deshabilita, ignora si acepta crédito o no
- **En presupuesto**: Si se deshabilita, ignora si entra en presupuesto o no

Al deshabilitar condiciones, los tiers se recalculan automáticamente (ej: sin apto_credito, solo queda activo+presupuesto).

#### Archivos relacionados

- `docs/js/config.js`: Define `DEFAULT_CONDITIONS` y `DEFAULT_WEIGHTS` (11 pesos con enabled/weight)
- `docs/js/utils.js`:
  - `scoreAtributo()`, `scoreNumerico()`, `scoreDisposicion()` - scoring de atributos booleanos
  - `scoreAmbientes()`, `scoreBanos()`, `scoreAntiguedad()`, `scoreExpensas()` - scoring de atributos numéricos
  - `calculateProperty()` - implementa tiers y score, guarda `_attrScores` y `_missingCount`
- `docs/js/components.js`: `renderConfigPanel()` muestra checkboxes + sliders para cada peso
- `docs/js/app.js`: `toggleWeightEnabled()` para habilitar/deshabilitar cada peso

## Para Continuar Desarrollo

1. **Mejorar parsing de Zonaprop**: Los selectores CSS pueden cambiar
2. **Implementar OAuth flow para MercadoLibre**: Actualmente solo acepta token manual
3. **Agregar más portales**: Properati, inmobiliarias individuales
4. **Scheduler**: Agregar opción de scraping periódico (cron/GitHub Actions)
5. **Notificaciones**: Telegram/email cuando aparecen nuevas propiedades

## Notas de Sesión (2025-12-13)

### Cambios realizados

1. **Sistema de penalización por datos faltantes**
   - Antes: dato faltante = 0 puntos (igual que "no")
   - Ahora: dato faltante = -penalidad (asumimos lo peor)
   - Funciones: `scoreAtributo()`, `scoreNumerico()`, `scoreDisposicion()`
   - Campos nuevos: `_attrScores` (status de cada atributo), `_missingCount`

2. **Nuevos pesos agregados (4 nuevos, total 11)**
   - `ambientes`: 4+ = muy bien, 3 = bien
   - `banos`: 2+ = bonus
   - `antiguedad`: <15 años = bonus, >50 = penalidad
   - `expensas`: $0 = bonus, >$250k = penalidad
   - Funciones: `scoreAmbientes()`, `scoreBanos()`, `scoreAntiguedad()`, `scoreExpensas()`

3. **Panel de configuración mejorado**
   - Checkbox para habilitar/deshabilitar cada peso
   - Emojis y descripciones claras ("↑ peso = prioriza X")
   - Grid de 4 columnas con cards
   - `toggleWeightEnabled()` en app.js

4. **Calculadora de quita necesaria**
   - Cuando no alcanza el presupuesto, muestra:
     - % de quita necesaria
     - Monto en USD de la quita
     - Precio objetivo
   - Se actualiza con el slider de dólar
   - Distingue quitas realistas (≤20%) de poco realistas

5. **Slider de dólar ampliado**
   - Antes: $900-$1500
   - Ahora: $900-$2000

### Issues conocidos / Pendientes

1. **MercadoLibre rate limiting**
   - La IP está bloqueada temporalmente
   - Headers mejorados (Sec-Ch-Ua, Sec-Fetch-*) no fueron suficientes
   - Playwright instalado pero no integrado (sigue bloqueado)
   - **Workaround**: usar cache, esperar unas horas, o usar proxy

2. **Propiedad Alvarez Jonte 4314**
   - Tenía terraza="si" cuando el aviso decía "terraza: no"
   - **Arreglado**: se creó sistema ATTR_PATTERNS para detectar "no" antes que "si"
   - Se corrigió manualmente en el JSON

3. **Bug de ordenamiento por tier**
   - El sort por tier asc/desc tenía la misma fórmula
   - **Arreglado** en utils.js línea 169

### Commits de la sesión

```
e71d804 Agregar monto en USD de la quita necesaria
a0ebcdc Mostrar quita necesaria cuando no alcanza el presupuesto
d6099a7 Aumentar límite del slider de dólar a $2000
f1458eb Agregar más pesos y mejorar sistema de scoring
ce20b67 Penalizar datos faltantes en score y permitir toggle de pesos
```

## Notas de Sesión (2025-12-15)

### Cambios realizados

1. **Columna `banos` agregada al Google Sheet**
   - Faltaba la columna en el Sheet, por eso el dashboard mostraba "-" en baños
   - El scraper ya extraía el dato (`sync_sheet.py` líneas 397-400 y 561-564)
   - Columna insertada después de `amb` en el Sheet
   - Re-scrapeadas todas las propiedades para llenar los datos

### Datos actualizados

- 18 propiedades con baños scrapeados (1-3 baños según propiedad)
- 9 links marcados como NO activos (publicaciones finalizadas)
- MercadoLibre funcionando (rate limiting resuelto, no hubo 403)

### Issue resuelto

- **Dashboard no mostraba baños**: El campo `banos` estaba en `SCRAPEABLE_COLS` y el scraper lo extraía, pero la columna no existía en el Google Sheet, por lo que nunca se guardaba.

### Sistema de Prints implementado

1. **Naming basado en IDs de portal**
   - Nuevo formato: `{ID}_{FECHA}.pdf` (ej: `MLA123456_2025-12-15.pdf`)
   - Extrae ID automáticamente del link de cada portal
   - Detecta prints por ID, por nombre de archivo, o por contenido del PDF

2. **Columna `fecha_print` agregada**
   - Se sincroniza automáticamente con `push`
   - El dashboard muestra indicador (📄 verde/ámbar, ○ si falta)

3. **Comandos mejorados**
   - `prints`: Muestra estado completo, sugiere nombres de archivo
   - `pendientes --sin-print`: Filtra solo propiedades sin backup

4. **Matching automático de PDFs**
   - Lee contenido del PDF para extraer URLs/IDs
   - Matchea por dirección si el nombre es genérico
   - Movidos 4 PDFs de `sin_asociar/` a prints activos
