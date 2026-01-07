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
- **Columnas**: tier/score, activo, apto, status, barrio, dirección, tipo, precio, m² cub, m² desc, $/m², vs ref, a juntar, OK, cocheras, terraza, balcón, baños
- **Iconos terraza/balcón**: ✓ verde (si), ✗ rojo (no), - gris (desconocido)
- **Sistema de tiers + score** para ordenar candidatos (ver abajo)
- **Vista detallada** con:
  - Slider de negociación de precio (0-15%)
  - Slider de dólar estimado ($900-$2000)
  - **Calculadora de quita necesaria**: Si no alcanza el presupuesto, muestra cuánto % y USD hay que negociar para que entre
  - Desglose completo de costos (escribano, sellos, etc.)
  - Indicador de datos faltantes (qué atributos faltan y penalizan el score)
  - Características: tipo, ambientes, m² cub/desc/tot/terreno, baños, antigüedad, estado, expensas, disposición, piso, etc.
  - Rating personal y fechas (publicado, contacto, visita)
- **Página de stats** con gráfico precio vs m²
- **Cotización dólar BNA** en tiempo real

### Sistema de Status

| Status | Descripción | Automático |
|--------|-------------|------------|
| `Visita programada` | Tiene fecha_visita ≥ hoy | ✓ (override automático) |
| `Por ver` | Default al agregar | |
| `Visitado` | Ya se visitó | |
| `Interesado` | Candidato serio | |
| `Descartado` | No interesa | |

**Campos de fecha:**
- `fecha_agregado`: Cuando se agregó al sheet
- `fecha_visita`: Fecha de visita programada (si es futura, el status se muestra como "Visita programada")
- `fecha_contacto`: Cuando se contactó a la inmobiliaria
- `fecha_publicado`: Cuando se publicó el aviso
- `fecha_inactivo`: Cuando se detectó que bajó el aviso
- `fecha_print`: Cuando se guardó el PDF de backup

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
- m² desc inconsistentes (tiene balcón/terraza pero m²_desc = 0)
- Atributos inciertos (terraza/balcon detectado pero valor ambiguo → "?")
- Datos faltantes (sin barrio, sin m²)
- Precios sospechosos

**Cálculo automático de m²:** Si tenés 2 de los 3 valores (m2_cub, m2_tot, m2_desc),
el scraper calcula el tercero automáticamente:
- `m2_desc = m2_tot - m2_cub`
- `m2_cub = m2_tot - m2_desc`
- `m2_tot = m2_cub + m2_desc`

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
python sheets/sync_sheet.py prints validate  # Validar datos PDFs vs sheet (offline)
python sheets/sync_sheet.py prints compare   # Comparar Sheet vs Web Cache vs PDF
python sheets/sync_sheet.py prints import    # Importar datos con consenso de fuentes
python sheets/sync_sheet.py pendientes       # Datos faltantes + sin print
python sheets/sync_sheet.py pendientes --sin-print  # Solo sin print
```

#### Sistema de 3 fuentes (Sheet vs Web Cache vs PDF)

El sistema compara datos de 3 fuentes antes de importar:

| Fuente | Descripción |
|--------|-------------|
| **Sheet** | Valor actual en Google Sheets |
| **Web Cache** | Lo que scrapeó el web scraper (`data/scrape_cache.json`) |
| **PDF** | Datos extraídos del PDF guardado (`data/prints/*.pdf`) |

**`prints compare`** - Muestra tabla comparativa con acciones:
- ✓ OK: Todas las fuentes coinciden
- ← IMPORTAR: Web y PDF coinciden, sheet vacío (alta confianza)
- ← solo PDF/Web: Una sola fuente, sheet vacío (media confianza)
- ⚠ REVISAR: Fuentes no coinciden (no se importa automáticamente)
- Muestra antigüedad del cache (ej: "4d" = 4 días)

**`prints import`** - Importa solo datos seguros:
- Alta confianza: Web y PDF coinciden → importa
- Media confianza: Solo una fuente → importa
- Discrepancias: NO importa, muestra warning
- Usar `--dry-run` para preview sin modificar

**Política de contradicciones:**
- Un campo vacío NO cuenta como contradicción (si Web="-" y PDF="si" → importa)
- Contradicción = dos fuentes con valores DIFERENTES (ej: Web="no" vs PDF="si")
- Diferencias de formato también cuentan (ej: cocheras="0" vs cochera="si")

```bash
# Flujo recomendado
python sync_sheet.py scrape        # Actualiza web cache
python sync_sheet.py prints compare # Revisar diferencias
python sync_sheet.py prints import --dry-run  # Preview
python sync_sheet.py prints import  # Aplicar cambios seguros
python sync_sheet.py push           # Subir a Google Sheets
```

#### Validación offline (prints validate)

El comando `prints validate` compara PDF vs Sheet directamente:
- No hace requests a internet (evita rate limiting)
- Detecta discrepancias (precio cambió, m² no coinciden)
- Muestra datos que están en el PDF pero faltan en el sheet
- Útil para verificar que el scraper extrajo bien los datos

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

## Notas de Sesión (2025-12-15 tarde) - Scraper de PDFs

### Arquitectura de datos (IMPORTANTE para entender)

```
┌─────────────────┐     pull      ┌─────────────────┐
│  Google Sheet   │ ───────────►  │  sheet_data.json│
│  (fuente verdad)│               │  (copia local)  │
└─────────────────┘               └─────────────────┘
                                          │
                                          ▼ scrape
                                  ┌─────────────────┐
                                  │  WEB SCRAPER    │
                                  │  (MeLi/Argenprop│
                                  │  via HTTP)      │
                                  └─────────────────┘
                                          │
                                          ▼ push
┌─────────────────┐     push      ┌─────────────────┐
│  Google Sheet   │ ◄───────────  │  sheet_data.json│
│  (actualizado)  │               │  (con datos)    │
└─────────────────┘               └─────────────────┘

┌─────────────────┐   validate    ┌─────────────────┐
│  PDFs guardados │ ───────────►  │  PDF SCRAPER    │
│  (backups)      │               │  (pdftotext)    │
└─────────────────┘               └─────────────────┘
                                          │
                                          ▼ compara
                                  ┌─────────────────┐
                                  │  Discrepancias  │
                                  │  sheet vs PDF   │
                                  └─────────────────┘
```

**Hay DOS scrapers diferentes:**

| Scraper | Archivo | Qué hace | Cuándo se usa |
|---------|---------|----------|---------------|
| **Web scraper** | `core/scrapers.py` | Fetch HTTP a MeLi/Argenprop | `sync_sheet.py scrape` |
| **PDF scraper** | `core/prints.py` | Extrae texto de PDFs locales | `sync_sheet.py prints validate` |

### Problema descubierto

El **web scraper** NO extrae estos campos (están en el HTML pero no los parseamos):
- `ambientes` → 17 propiedades sin dato
- `cochera` → 13 propiedades sin dato
- `luminoso` → 9 propiedades sin dato

El **PDF scraper** SÍ los extrae (porque lee el texto completo del PDF).

### Qué se hizo hoy

1. **Creado `prints validate`** - Compara datos del PDF vs sheet SIN hacer requests web
2. **Funciones nuevas en `core/prints.py`**:
   - `extraer_datos_pdf()` - Extrae precio, m², baños, cochera, terraza, etc.
   - `validar_datos_pdf_vs_sheet()` - Compara y reporta diferencias
3. **Tests agregados** - 49 tests pasan

### Pendientes para próxima sesión

1. **Mejorar web scraper** (`core/scrapers.py`) para extraer:
   - `ambientes` (buscar "3 ambientes" en el HTML)
   - `cochera` (buscar "cochera", "garage")
   - `luminoso` (buscar "luminoso")

2. **O alternativamente**: Crear comando para importar datos del PDF al sheet
   - `sync_sheet.py prints import` → Llena campos vacíos desde PDFs

3. **Verificar discrepancia Fila 7 (Lavalleja)**:
   - PDF dice `balcon=si`
   - Sheet dice `balcon=no`
   - Hay que mirar el aviso y decidir cuál es correcto

## Notas de Sesión (2025-12-17) - Sistema de 3 Fuentes

### Problema resuelto

Antes: `prints import` importaba datos del PDF sin validar contra otras fuentes.
Ahora: Sistema compara **3 fuentes** (Sheet vs Web Cache vs PDF) antes de importar.

### Arquitectura de comparación

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   SHEET     │   │  WEB CACHE  │   │    PDF      │
│ (actual)    │   │ (scrape_    │   │ (pdftotext) │
│             │   │  cache.json)│   │             │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       └────────────────►│◄────────────────┘
                         ▼
              ┌─────────────────────┐
              │ comparar_tres_      │
              │ fuentes()           │
              │                     │
              │ Acciones:           │
              │ - OK (coinciden)    │
              │ - IMPORTAR (Web=PDF)│
              │ - SOLO_PDF/WEB      │
              │ - REVISAR (difieren)│
              └─────────────────────┘
```

### Lógica de extracción unificada

**IMPORTANTE**: Ambos scrapers usan `detectar_atributo()` de `core/helpers.py`:

```python
# En helpers.py - FUENTE ÚNICA DE VERDAD para patrones
ATTR_PATTERNS = {
    'terraza': {
        'si': ['terraza: si', 'con terraza', ...],
        'no': ['terraza: no', 'sin terraza', ...],  # Se evalúa PRIMERO
    },
    # ... otros atributos
}
```

- **Web scraper** (`core/scrapers.py`): Usa `detectar_atributo(txt, 'terraza')`
- **PDF scraper** (`core/prints.py`): Usa `detectar_atributo(texto, 'terraza')`

Para agregar un nuevo patrón, modificar SOLO `ATTR_PATTERNS` en `helpers.py`.

### Normalización en comparación

En `comparar_tres_fuentes()` se normalizan valores antes de comparar:

```python
# cocheras: 0 = "no", 1+ = "si"
if campo == 'cocheras':
    if v in ('0', 'no'): return 'no'
    elif v.isdigit() and int(v) > 0: return 'si'

# expensas: valores < 1000 se asumen en miles
if campo == 'expensas':
    if num < 1000: num = num * 1000
```

### Bugs conocidos

1. **Web scraper terraza**: A veces detecta "terraza=si" cuando el aviso dice "balcón tipo terraza"
   - **Solución**: PDF es la fuente más confiable para terraza
   - **Propiedades afectadas**: Fila 28 (Alvarez Jonte), Fila 29 (Espinosa)

2. **Ambientes**: Ambigüedad entre "3 ambientes" vs "2 dormitorios + living"
   - Esto es un problema del aviso, no del scraper

### Comandos nuevos

```bash
python sync_sheet.py prints compare   # Ver tabla de 3 columnas
python sync_sheet.py prints import    # Importar solo datos seguros
```

### Política de importación

- **Vacío NO es contradicción**: Si Web="-" y PDF="si" → importa "si"
- **Contradicción = valores diferentes**: Web="no" vs PDF="si" → NO importar
- **Formato normalizado**: cocheras 0="no", expensas en pesos completos

### Commits de la sesión

```
efa04f1 Agregar sistema de comparación de 3 fuentes
5b7f074 Documentar política de contradicciones
2712ab7 Agregar extracción de apto_credito y ascensor
4120ec5 Unificar lógica de extracción con detectar_atributo()
```

## Notas de Sesión (2025-12-17 noche) - Automatización del flujo

### Cambios integrados al flujo de scrape

El comando `scrape` ahora ejecuta automáticamente:

```
scrape_link()           ← Extrae datos del portal
    ↓
apply_scraped_data()    ← Aplica a la fila
    ↓
validar_propiedad()     ← Warnings de inconsistencias
    ↓
calcular_m2_faltantes() ← Si hay 2 de 3 m², calcula el tercero
    ↓
inferir_valores_faltantes() ← Infiere valores lógicos
```

### Inferencia automática de valores

Nueva función `inferir_valores_faltantes()` en `core/helpers.py`:

| Condición | Inferencia |
|-----------|------------|
| `status` vacío | → `"Por ver"` |
| `m2_desc = 0` | → `terraza=no`, `balcon=no` |
| `tipo = "ph"` | → `ascensor=no`, `cochera=no` |

### Extracción de `estado`

Agregada extracción del campo `estado` (condición del inmueble):
- **Argenprop**: Busca "estado: X" en features
- **MercadoLibre**: Busca en tabla de características
- **PDF**: Busca patrones como "usado", "a estrenar", etc.

**Nota**: No siempre está disponible como dato estructurado.

### Limpieza de código

Eliminados imports no utilizados en `sync_sheet.py`:
- Constantes: `BARRIOS_CABA`, `ATTR_PATTERNS`
- Funciones: `quitar_tildes`, `extraer_numero`, `extraer_m2`, `detectar_barrio`, `extraer_id_propiedad`, `detectar_atributo`
- Módulo: `unicodedata`

Estas funciones siguen disponibles internamente en `core/`.

### Commits de la sesión

```
8b4600e Limpiar imports no utilizados en sync_sheet.py
66db232 Agregar extracción de campo 'estado' a scrapers
bcc54dd Agregar cálculo automático de m² faltantes al flujo
d373581 Integrar inferencia automática de valores al flujo
71d1480 Arreglar bugs del PDF extractor
aabe837 Agregar status='Por ver' por defecto en add_links.py
```

## Notas de Sesión (2025-12-18)

### Campo `patio` agregado

Nuevo campo booleano similar a `balcon` y `terraza`. Agregado en:
- **Backend**: `helpers.py` (ATTR_PATTERNS), `scrapers.py`, `validation.py`, `prints.py`, `sync_sheet.py`
- **Dashboard**: `config.js` (ICONS, WEIGHTS), `utils.js` (scoring), `components.js` (tabla, cards, modal)
- **Tests**: 4 tests nuevos en `test_sync_sheet.py`

**Diferencia clave**: Patio es a nivel de suelo, no requiere m²_desc (a diferencia de balcón/terraza que son elevados).

### Sistema de validaciones (_warnings)

Nuevo campo calculado `_warnings` en `calculateProperty()` que detecta inconsistencias:

| Tipo | Descripción | Severidad |
|------|-------------|-----------|
| `m2_math` | cub + desc ≠ tot | warning |
| `m2_cub_tot` | cub > tot (ilógico) | error |
| `exterior_sin_m2` | Tiene balcón/terraza pero m²_desc = 0 | warning |
| `m2_sin_exterior` | Tiene m²_desc pero sin exterior marcado | warning/info |

Visualización:
- **Tabla**: Nueva columna ⚠ con badge
- **Cards**: Badge de warnings
- **Modal**: Sección detallada con cada warning

### Rediseño UX/UI de Cards Mobile

Análisis profundo y rediseño basado en principios UX mobile:

**Cambios de jerarquía visual:**
- Barrio ahora es prominente (decisión #1 del usuario)
- Precio y m² grandes y enfrentados
- Border color indica status de un vistazo

**Datos agregados a las cards:**
- Badge `NUEVA`/`VENDIDA` (temporal awareness)
- Antigüedad (`✨ A estrenar` o `✨15a`)
- m² descubiertos en verde (`+8`)
- Disposición `☀️ Frente` cuando aplica
- Tiempo desde publicación (`hace 5d`)

**Simplificaciones:**
- "A juntar" ahora es chip inline (`✓ $42k`)
- Tier + Score unificados en un badge (`T1-85`)
- Amenities con checks claros: `T✓ B✗ P✓ 🚗`

**Colores de borde según status:**
- Verde: OK + Apto crédito
- Azul: OK + Sin confirmar crédito
- Ámbar: No entra en presupuesto
- Rojo: Inactivo

### Commits de la sesión

```
9207616 Unificar tier y score en badge único (T1-85)
3085a1d Hacer score más visible en cards (debug)
e3c60f0 Restaurar score numérico junto al tier en cards
9bbe90a Rediseño UX/UI de cards para mobile
9ccc56b Agregar validaciones de m² y exterior con warnings visuales
161e571 Agregar campo patio al sistema completo
```

## Notas de Sesión (2025-12-18 tarde) - Fix Sliders Mobile

### Problema identificado

Los sliders del modal (negociación y dólar) funcionaban mal en mobile:
- El modal se recreaba completo en cada movimiento del slider
- La animación `slideUp` se disparaba repetidamente
- El scroll del modal se perdía al soltar el slider
- El gesto de arrastre se interrumpía

### Arquitectura del problema

El dashboard usa vanilla JS con un patrón de "re-render completo":
```
slider cambia → render() → destruye TODO el DOM → recrea TODO
```

Esto funciona bien para páginas estáticas, pero causa problemas con interacciones continuas como sliders.

### Solución implementada

**Actualización parcial del DOM** - Solo se actualiza lo que cambia:

1. **Separar sliders de cálculos**:
   - `#simulation-calcs`: Contiene precios, costos, desglose (SE ACTUALIZA)
   - Sliders: Están fuera del contenedor, no se recrean

2. **Funciones de actualización parcial**:
   - `updateSimulation()`: Solo actualiza `#simulation-calcs`
   - `updateNegotiation()` y `updateDolarEstimado()`: Actualizan displays + cálculos

3. **Displays con IDs para actualización directa**:
   - `#neg-display`: Muestra el % de negociación
   - `#dolar-display`: Muestra el valor del dólar
   - `#dolar-credito-info`: Muestra impacto en crédito

### Mejoras de CSS para touch

```css
input[type="range"] {
  touch-action: manipulation;  /* Evita delay 300ms */
  -webkit-user-select: none;
}

input[type="range"]::-webkit-slider-thumb {
  width: 28px;   /* Desktop */
  width: 32px;   /* Mobile (@media) */
}

input[type="range"]::-webkit-slider-thumb:active {
  transform: scale(1.15);  /* Feedback visual */
}
```

### Otras mejoras de la sesión

1. **Versión visible**: `APP_VERSION` en status bar y panel de ayuda
2. **Animación slideUp removida**: Causaba flicker en re-renders
3. **Indicador de uso del crédito**: Muestra % usado y cuánto sobra
4. **Fix inmobiliaria**: Se muestra cuando `!esVentaDirecta()`, no solo cuando existe el campo

### Lógica del crédito explicada

```
anticipo = max(precio - crédito, 10% del precio)
```

- Si crédito ≥ 90% del precio → anticipo = 10% (mínimo legal)
- Si crédito < 90% del precio → anticipo = precio - crédito

Esto causa un "punto de quiebre" cuando el dólar sube y el crédito (en USD) ya no cubre el 90%.

### Archivos modificados

- `docs/js/app.js`: Funciones de actualización parcial
- `docs/js/components.js`: Separación sliders/cálculos, IDs para displays
- `docs/js/config.js`: APP_VERSION
- `docs/css/styles.css`: Mejoras touch, sin animación slideUp

### Commits de la sesión

```
6c0be08 Fix: mostrar inmobiliaria correctamente + actualizar displays de sliders en tiempo real
8d8c57b Mostrar uso del crédito en desglose de costos
8ac66e5 Fix: separar sliders de cálculos para arrastre fluido en mobile
0a257dd Refactor: actualización parcial del modal (fix scroll en sliders mobile)
7ffe760 Quitar animación slideUp del modal (fix flicker en sliders)
dccc429 Fix sliders en mobile: evitar re-render durante arrastre
```
