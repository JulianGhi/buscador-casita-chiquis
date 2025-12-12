# Scripts de sincronización

Scripts para sincronizar Google Sheets con datos scrapeados de los links de propiedades.

## Flujo de trabajo

```
Google Sheets ──pull──▶ Local JSON ──scrape──▶ Local JSON ──view/diff──▶ ──push──▶ Google Sheets
                        (descarga)              (completa)     (revisar)             (subir)
```

### 1. Descargar datos

```bash
python sheets/sync_sheet.py pull
```
Descarga los datos actuales de Google Sheets a `data/sheet_data.json`.

### 2. Scrapear links

```bash
python sheets/sync_sheet.py scrape        # Solo filas sin precio/m²
python sheets/sync_sheet.py scrape --all  # Todos los links (re-verifica activo)
```
Recorre las filas que tienen link, scrapea los datos y actualiza el JSON local.

**Datos extraídos:**
- `precio`, `m2_cub`, `m2_tot`, `amb`
- `direccion`, `barrio`
- `expensas`, `antiguedad`, `terraza`
- `activo` (si/no según estado del link)

**Dominios soportados:**
| Dominio | Método | Notas |
|---------|--------|-------|
| mercadolibre.com.ar | httpx | Detecta "Publicación finalizada" |
| argenprop.com | httpx | Algunos links caen (410) |
| zonaprop.com.ar | - | No soportado (requiere Playwright) |

**Detección de links inactivos:**
- HTTP 404/410 → `activo = no`
- Redirect a búsqueda (ML) → `activo = no`
- Mensaje "Publicación finalizada" (ML) → `activo = no`

### 3. Revisar cambios

**Opción A: Preview visual en browser**
```bash
python sheets/sync_sheet.py view              # Abre preview HTML
python sheets/sync_sheet.py view --check-links  # + verifica links online
```
Genera `data/preview.html` con tabla interactiva:
- **Verde** = Dato nuevo
- **Amarillo** = Dato modificado
- **Rojo** = Link offline

**Opción B: Diff en terminal**
```bash
python sheets/sync_sheet.py diff
```
Muestra tabla comparando Local vs Google Sheets con colores ANSI.

### 4. Subir cambios

```bash
python sheets/sync_sheet.py push            # Solo celdas vacías (merge)
python sheets/sync_sheet.py push --force    # Sobrescribe todo el sheet
python sheets/sync_sheet.py push --dry-run  # Muestra qué haría sin aplicar
```

**Modos de push:**
- **merge** (default): Solo actualiza celdas que están vacías en el Sheet
- **force**: Sobrescribe todas las celdas con los valores locales

## Ejemplo completo

```bash
# Activar entorno
source .venv/bin/activate

# Flujo completo
python sheets/sync_sheet.py pull           # 1. Traer datos
python sheets/sync_sheet.py scrape         # 2. Scrapear links faltantes
python sheets/sync_sheet.py view           # 3. Preview en browser
python sheets/sync_sheet.py push           # 4. Subir cambios

# Re-verificar todos los links (útil si cambiaron estados)
python sheets/sync_sheet.py scrape --all   # Re-verifica activo en todos
python sheets/sync_sheet.py push --force   # Sobrescribe incluyendo activo
```

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `sync_sheet.py` | Script principal con pull/scrape/view/diff/push |
| `complete_excel.py` | Scrapea links del Excel local (legacy) |
| `sheets.py` | Utilidades base para Google Sheets |
| `update_sheet.py` | Sube Excel a Google Sheets (legacy) |
| `clean_sheet.py` | Limpia/normaliza datos en Sheets |

## Configuración

### Requisitos

```bash
pip install httpx beautifulsoup4 lxml gspread google-auth
```

### Google Sheets API

1. Crear proyecto en [Google Cloud Console](https://console.cloud.google.com)
2. Habilitar Google Sheets API y Google Drive API
3. Crear Service Account y descargar `credentials.json`
4. Poner `credentials.json` en la raíz del proyecto
5. Compartir el Sheet con el email del Service Account

### Variables en sync_sheet.py

```python
SHEET_ID = '16n92ghEe8Vr1tiLdqbccF3i97kiwhHin9OPWY-O50L4'  # ID del Google Sheet
LOCAL_FILE = Path('data/sheet_data.json')  # Archivo local de trabajo
```

## Datos

- **Google Sheet**: https://docs.google.com/spreadsheets/d/16n92ghEe8Vr1tiLdqbccF3i97kiwhHin9OPWY-O50L4
- **Archivo local**: `data/sheet_data.json`
- **Preview HTML**: `data/preview.html`
