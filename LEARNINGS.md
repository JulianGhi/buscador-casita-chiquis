# Aprendizajes del Proyecto - Argentina Real Estate Scraper

Documentación de problemas encontrados y soluciones para futura referencia.

---

## PROCEDIMIENTOS PRINCIPALES

### Agregar nuevos links
```bash
cd /home/julian/Documents/repos/argentina-real-estate-scraper
source .venv/bin/activate

# Un link
python sheets/add_links.py "https://mercadolibre.com.ar/MLA-123456"

# Con nota
python sheets/add_links.py "https://mercadolibre.com.ar/MLA-123456 - tiene patio"

# Múltiples links
python sheets/add_links.py URL1 URL2 URL3

# Desde archivo (uno por línea)
python sheets/add_links.py --file links.txt
```

### Actualizar datos (re-scrapear)
```bash
# Ver qué hay en la planilla vs local
python sheets/sync_sheet.py diff

# Descargar datos de la planilla
python sheets/sync_sheet.py pull

# Re-scrapear links existentes
python sheets/sync_sheet.py scrape

# Subir cambios a la planilla
python sheets/sync_sheet.py push
```

### Verificar links activos
```bash
# Verifica cuáles dan 404 y los marca como activo='no'
python sheets/sync_sheet.py scrape --check-links
```

---

## CAMPOS Y SUS FUENTES

### 📝 Campos MANUALES (el usuario los llena en la planilla)
| Campo | Descripción |
|-------|-------------|
| rating | Puntuación 1-5 |
| contacto | Teléfono/email del vendedor |
| fecha_visita | Cuándo se visitó |
| fecha_contacto | Cuándo se contactó |
| status | Visitado/Por ver/Descartado/etc |
| notas | Observaciones |
| inmobiliaria | Nombre de la inmobiliaria |
| estado | Estado del inmueble (Bueno/A refaccionar) |

### 🤖 Campos SCRAPEADOS (dependen del anuncio)
| Campo | % vacíos (ML) | Nota |
|-------|--------------|------|
| direccion | 0% | Siempre disponible |
| barrio | 0% | A veces incorrecto |
| precio | 0% | Siempre disponible |
| m2_cub, m2_tot | 0% | Casi siempre |
| amb | 0% | Casi siempre |
| expensas | 6% | A veces no dice |
| tipo | 47% | depto/ph/casa |
| apto_credito | 53% | Solo si lo dice |
| terraza | 47% | Solo si lo tiene |
| balcon | 65% | Solo si lo tiene |
| cocheras | 65% | Solo si lo tiene |
| ascensor | 71% | Solo si lo tiene |
| piso | 76% | A veces no dice |
| disposicion | 53% | frente/contrafrente |
| luminosidad | 47% | A veces no dice |
| fecha_publicado | 88% | Falla el scraper |

### ⚙️ Campos AUTOMÁTICOS
| Campo | Descripción |
|-------|-------------|
| activo | si/no - basado en si el link funciona |
| fecha_agregado | Fecha cuando se agregó a la planilla |
| link | La URL del anuncio |

### ⚠️ Problemas conocidos
1. **fecha_publicado** falla 88% - MercadoLibre cambió el formato
2. **barrio** puede ser incorrecto - no validamos vs altura de calle
3. **Argenprop** scraper anda mal - casi todo vacío

---

## 1. Google Sheets - `append_row` puede corromper datos

### Problema
Al usar `ws.append_row()` de gspread, los datos pueden escribirse en columnas incorrectas si:
- La planilla tiene columnas vacías extras más allá de los headers
- Hubo filas previamente corruptas que extendieron el ancho de la planilla

### Síntomas
- Los datos aparecen desplazados (offset) hacia la derecha
- El offset puede ser acumulativo (cada fila nueva más corrida que la anterior)
- `get_all_values()` retorna más columnas que las esperadas

### Solución
En lugar de `append_row`, usar `update` con un rango específico:

```python
# MAL - puede fallar si la planilla está corrupta
ws.append_row(new_row, value_input_option='USER_ENTERED')

# BIEN - escribe en columnas específicas
cell_range = f'A{next_row}:AD{next_row}'  # A-AD = 30 columnas
ws.update(values=[new_row], range_name=cell_range, value_input_option='USER_ENTERED')
```

### Prevención
1. Limitar headers a las primeras N columnas: `headers = ws.row_values(1)[:30]`
2. Usar `ws.get('A:AD')` en lugar de `get_all_values()` para obtener solo columnas específicas
3. Después de detectar corrupción, limpiar con `ws.resize(cols=30)`

---

## 2. Diferencias entre métodos de gspread

### `row_values(1)` vs `get_all_values()[0]`

| Método | Comportamiento |
|--------|---------------|
| `ws.row_values(1)` | Retorna solo celdas con datos (hasta la última no vacía) |
| `ws.get_all_values()[0]` | Retorna todas las celdas incluyendo vacías hasta el ancho máximo de la planilla |

### Implicación
Si la planilla tiene 345 columnas (por corrupción previa), `get_all_values()` retornará filas de 345 elementos aunque solo las primeras 30 tengan datos.

---

## 3. Estructura de datos en sheet_data.json

```json
{
  "headers": ["activo", "apto_credito", ...],
  "rows": [
    {"_row": 2, "activo": "si", "direccion": "...", ...},
    {"_row": 3, ...}
  ],
  "source": "google_sheets",
  "pulled_at": "2025-12-12T..."
}
```

- `rows` es una lista de diccionarios
- Cada fila tiene `_row` con el número de fila en la planilla
- Los campos vacíos se incluyen con valor `""`

---

## 4. Scraping de MercadoLibre

### Campos extraídos por el scraper
- `direccion`, `barrio`, `tipo`, `precio`
- `m2_cub`, `m2_tot`, `amb`, `disposicion`
- `balcon`, `cocheras`, `luminosidad`, `antiguedad`, `expensas`
- `apto_credito` (si dice "Apto crédito" en el anuncio)
- `fecha_publicado` (calculada desde "Publicado hace X días")

### Campo `activo` - NO lo devuelve el scraper
El campo `activo` NO se extrae del contenido de la página. Se determina así:
- Si el scraping funciona → `activo = 'si'`
- Si devuelve 404/410 → `activo = 'no'`
- Si hay otro error → `activo = '?'`

**IMPORTANTE**: En `add_links.py` hay que setear este campo manualmente después de scrapear:
```python
if '_error' in data:
    data['activo'] = '?'
else:
    data['activo'] = 'si'
```

### Campos opcionales
Algunos campos solo aparecen si el anuncio los tiene:
- `apto_credito` - solo si dice "Apto crédito"
- `terraza`, `balcon`, `cocheras`, `ascensor` - dependen del anuncio
- `disposicion` (frente/contrafrente) - no siempre está

**Los campos vacíos NO son errores** - simplemente el anuncio no tiene esa información.

### Fecha de publicación
```python
import re
from datetime import datetime, timedelta

pub_match = re.search(r'Publicado hace (\d+) día', resp.text)
if pub_match:
    dias = int(pub_match.group(1))
    fecha_pub = datetime.now() - timedelta(days=dias)
    data['fecha_publicado'] = fecha_pub.strftime('%Y-%m-%d')
```

---

## 5. Columnas de la planilla (30 columnas, A-AD)

| Índice | Header | Descripción |
|--------|--------|-------------|
| 0 | activo | si/no/? |
| 1 | apto_credito | si/no/? |
| 2 | status | Visitado/Contactado/etc |
| 3 | direccion | Dirección del inmueble |
| 4 | barrio | Barrio |
| 5 | tipo | depto/ph/casa |
| 6 | precio | Precio en USD |
| 7 | m2_cub | Metros cubiertos |
| 8 | m2_tot | Metros totales |
| 9 | amb | Ambientes |
| 10 | piso | Número de piso |
| 11 | disposicion | frente/contrafrente |
| 12 | terraza | si/no |
| 13 | balcon | si/no |
| 14 | cocheras | Cantidad |
| 15 | ascensor | si/no |
| 16 | luminosidad | Buena/Regular/etc |
| 17 | antiguedad | Años |
| 18 | estado | Bueno/A refaccionar/etc |
| 19 | expensas | Monto en pesos |
| 20 | m2_terr | Metros de terreno |
| 21 | rating | 1-5 |
| 22 | inmobiliaria | Nombre |
| 23 | contacto | Teléfono/email |
| 24 | fecha_contacto | YYYY-MM-DD |
| 25 | fecha_visita | YYYY-MM-DD |
| 26 | notas | Texto libre |
| 27 | link | URL del anuncio |
| 28 | fecha_publicado | YYYY-MM-DD (desde scraping) |
| 29 | fecha_agregado | YYYY-MM-DD (cuando se agregó a la planilla) |

---

## 6. Dashboard - Cálculo de rango de precios

```javascript
function getPrecioRange(dolar = null) {
  const credito = getCreditoUSD(dolar);
  // Precio mínimo: cuando ponemos solo el 10% (crédito cubre el 90%)
  const precioMin = Math.round(credito / 0.9);

  // Precio máximo: todo lo que tenemos menos gastos
  const gastosRate = CONFIG.ESCRIBANO + CONFIG.SELLOS + CONFIG.REGISTRALES + CONFIG.INMOB + CONFIG.HIPOTECA;
  const precioMax = Math.round((CONFIG.PRESUPUESTO + credito) / (1 + gastosRate));

  return { min: precioMin, max: precioMax };
}
```

---

## 7. Lógica de colores en el dashboard

### Propiedades en rojo (inactivas)
```javascript
const isInactivo = activo?.toLowerCase() === 'no';
```

### Propiedades en amarillo (necesitan verificación)
```javascript
const needsCheck = (activo === '?' || apto === '?' || !apto) && p._ok;
// _ok = entra en presupuesto
```

### Propiedades en verde (ok y dentro de presupuesto)
```javascript
const rowBg = p._ok ? 'bg-green-50/30' : '';
```

---

## 8. Scripts disponibles

### `sheets/sync_sheet.py`
```bash
python sync_sheet.py pull      # Descargar datos a JSON
python sync_sheet.py scrape    # Re-scrapear links existentes
python sync_sheet.py view      # Ver datos actuales
python sync_sheet.py diff      # Ver diferencias
python sync_sheet.py push      # Subir cambios a la planilla
```

### `sheets/add_links.py`
```bash
# Agregar links individuales
python add_links.py URL1 URL2 URL3

# Con notas
python add_links.py "URL - nota para este link"

# Desde archivo
python add_links.py --file links.txt
```

---

## 9. Problemas comunes y soluciones

### "Los datos no aparecen en la planilla"
1. Verificar con `ws.get('A:AD')` directamente
2. Buscar datos en columnas lejanas (pueden estar corridos)
3. Si hay corrupción, limpiar con `ws.resize(cols=30)`

### "El scraper no encuentra datos"
1. Verificar que la URL sea de mercadolibre.com.ar o argenprop.com
2. El anuncio puede haber sido dado de baja
3. MercadoLibre puede bloquear requests frecuentes

### "sync_sheet.py pull muestra filas vacías"
1. La planilla puede tener filas vacías en el medio
2. Verificar que no haya datos corridos a la derecha

---

## 10. Notas de implementación

### Evitar caracteres especiales en JSON
Los valores se escriben tal cual vienen del scraper. Si hay problemas de encoding, verificar que el JSON se guarde con UTF-8.

### Rate limiting de Google Sheets API
- Límite: ~100 requests por 100 segundos
- Para operaciones bulk, usar `batch_update` en lugar de múltiples `update`

### MercadoLibre anti-scraping
- Usar headers con User-Agent realista
- No hacer más de 1 request por segundo
- Rotar IPs si es necesario (no implementado actualmente)
