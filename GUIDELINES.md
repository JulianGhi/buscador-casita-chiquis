# Guidelines de Código - Casita Chiquis

> Estándares de calidad para mantener el código limpio, mantenible y profesional.

## Principios Fundamentales

### 1. Simplicidad sobre Complejidad
```
✓ Código que se entiende en 5 segundos
✗ Abstracciones innecesarias "por si acaso"
```

### 2. Explícito sobre Implícito
```
✓ Nombres descriptivos aunque sean largos
✗ Abreviaciones crípticas (x, tmp, data2)
```

### 3. Falla Rápido y Fuerte
```
✓ Validar inputs al inicio de la función
✗ Dejar que el error aparezca 10 niveles más abajo
```

---

## Python (sheets/)

### Estructura de Archivos

```
sheets/
├── sync_sheet.py      # CLI principal, orquestación
├── add_links.py       # Script standalone
├── core/              # Módulos reutilizables
│   ├── __init__.py    # Exports públicos
│   ├── helpers.py     # Funciones puras (sin side effects)
│   ├── scrapers.py    # Extracción de datos externos
│   ├── storage.py     # I/O archivos (JSON, cache)
│   ├── sheets_api.py  # I/O Google Sheets
│   ├── validation.py  # Validación y warnings
│   ├── prints.py      # Lógica de PDFs
│   └── templates.py   # Generación de HTML
└── tests/             # Tests (test_*.py)
```

### Naming Conventions

```python
# Funciones: verbo_sustantivo (snake_case)
def extraer_precio(html):      # ✓
def get_active_rows(data):     # ✓
def precio(html):              # ✗ No es claro qué hace
def extractPrice(html):        # ✗ camelCase no es Python

# Variables: sustantivo descriptivo
rows_to_scrape = []            # ✓
filas_activas = []             # ✓
r = []                         # ✗
temp = []                      # ✗

# Constantes: UPPER_SNAKE_CASE
SCRAPEABLE_COLS = [...]        # ✓
MAX_RETRIES = 3                # ✓
scrapeable_cols = [...]        # ✗

# Clases: PascalCase (si las hubiera)
class PropertyScraper:         # ✓
```

### Funciones

```python
# ✓ BIEN: Función pura, un solo propósito
def calcular_m2_faltantes(data):
    """Calcula m² faltantes si tenemos 2 de 3 valores."""
    m2_cub = int(data.get('m2_cub') or 0)
    m2_tot = int(data.get('m2_tot') or 0)
    m2_desc = int(data.get('m2_desc') or 0)

    if m2_tot > 0 and m2_cub > 0 and m2_desc == 0:
        return {'m2_desc': str(m2_tot - m2_cub)}
    return {}

# ✗ MAL: Hace demasiadas cosas, side effects ocultos
def procesar_propiedad(url):
    html = requests.get(url).text  # Side effect: HTTP
    data = extraer_datos(html)
    guardar_en_db(data)            # Side effect: I/O
    enviar_notificacion(data)      # Side effect: HTTP
    return data
```

### Docstrings

```python
# Funciones públicas: docstring obligatorio
def scrape_mercadolibre(url, use_cache=True, cache=None):
    """Extrae datos de una publicación de MercadoLibre.

    Args:
        url: URL completa de la publicación
        use_cache: Si True, busca en cache antes de hacer request
        cache: Dict de cache, se modifica in-place si se provee

    Returns:
        dict con campos extraídos, o {'_error': msg} si falla
    """

# Funciones internas/privadas: docstring opcional pero recomendado
def _parse_price(text):
    """Extrae número de precio de texto como '$150.000' -> 150000"""
```

### Imports

```python
# Orden: stdlib → third-party → local
import json
import re
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .helpers import extraer_numero, detectar_barrio
from .storage import load_cache, save_cache

# ✗ MAL: Import desordenado o con wildcards
from .helpers import *
import json, re, os
```

### Manejo de Errores

```python
# ✓ BIEN: Específico y con contexto
try:
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
except httpx.TimeoutException:
    return {'_error': f'Timeout después de 10s: {url}'}
except httpx.HTTPStatusError as e:
    return {'_error': f'Status {e.response.status_code}'}

# ✗ MAL: Silenciar errores
try:
    data = scrape(url)
except:
    pass  # ¿Qué pasó? Nadie sabe
```

### Type Hints (Opcionales pero Recomendados)

```python
def extraer_numero(texto: str, quitar_miles: bool = False) -> str | None:
    """Extrae primer número de un texto."""
    ...

def get_active_rows(rows: list[dict]) -> list[dict]:
    """Filtra filas activas con links válidos."""
    ...
```

---

## JavaScript (docs/js/)

### Estructura de Archivos

```
docs/js/
├── config.js      # Constantes, estado inicial, localStorage
├── utils.js       # Funciones puras (cálculos, formateo)
├── api.js         # Fetch de datos externos
├── components.js  # Funciones render*() que retornan HTML
└── app.js         # Event handlers, inicialización
```

### Naming Conventions

```javascript
// Funciones: camelCase, verbo primero
function renderTable(data) { }     // ✓
function calculateScore(p) { }     // ✓
function table(data) { }           // ✗ ¿Qué hace?

// Constantes: UPPER_SNAKE_CASE
const SHEET_ID = '1abc...';        // ✓
const DEFAULT_WEIGHTS = {...};     // ✓

// Estado global: objeto `state`
const state = {
  loading: false,
  filterStatus: 'todos',
  // ...
};

// Funciones de render: render + Componente
function renderHeader() { }
function renderFilters() { }
function renderDetailModal(p) { }
```

### Componentes (HTML en JS)

```javascript
// ✓ BIEN: Template literals con indentación clara
function renderCard(p) {
  return `
    <div class="card">
      <h3>${escapeHtml(p.titulo)}</h3>
      <p class="price">$${p.precio.toLocaleString()}</p>
    </div>
  `;
}

// ✗ MAL: Concatenación ilegible
function renderCard(p) {
  return '<div class="card"><h3>' + p.titulo + '</h3><p class="price">$' + p.precio + '</p></div>';
}
```

### Seguridad XSS

```javascript
// ✓ SIEMPRE escapar contenido dinámico de usuarios/APIs
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Usar así:
`<h3>${escapeHtml(p.direccion)}</h3>`

// ✗ NUNCA insertar directamente
`<h3>${p.direccion}</h3>`  // XSS vulnerable!
```

### CSS Classes (Tailwind)

```javascript
// ✓ BIEN: Clases ordenadas por tipo
// Layout → Spacing → Typography → Colors → Effects
`<div class="flex items-center gap-2 p-4 text-sm text-slate-600 hover:bg-slate-50">`

// ✓ BIEN: Usar objeto THEME para colores semánticos
const THEME = {
  success: { bg: 'bg-green-100', text: 'text-green-800' },
  error: { bg: 'bg-red-100', text: 'text-red-800' },
};
`<span class="${THEME.success.bg} ${THEME.success.text}">OK</span>`

// ✗ MAL: Colores hardcodeados dispersos
`<span class="bg-green-100 text-green-800">OK</span>`  // Repetido en 20 lugares
```

---

## CSS (docs/css/)

### Mobile-First

```css
/* ✓ BIEN: Base mobile, expandir para desktop */
.card {
  padding: 12px;          /* Mobile */
}

@media (min-width: 640px) {
  .card {
    padding: 16px;        /* Desktop */
  }
}

/* ✗ MAL: Desktop first, reducir para mobile */
.card {
  padding: 16px;
}

@media (max-width: 640px) {
  .card {
    padding: 12px;
  }
}
```

### Naming (BEM-ish)

```css
/* Componente */
.config-panel { }

/* Elemento dentro del componente */
.config-header { }
.config-tabs { }
.config-tab { }

/* Modificador/Estado */
.config-tab.active { }

/* ✗ MAL: Clases genéricas sin contexto */
.header { }     /* ¿De qué? */
.active { }     /* ¿De qué componente? */
```

---

## Git

### Commits

```bash
# Formato: Emoji + Verbo en infinitivo + qué
✓ "Agregar extracción de campo 'estado'"
✓ "Arreglar bug de cálculo de m²"
✓ "Mejorar responsividad del modal"
✓ "Refactorizar scrapers en módulos separados"

✗ "fix"
✗ "cambios"
✗ "WIP"
✗ "asdasd"

# Emojis opcionales pero útiles:
# 🐛 Fix bug
# ✨ Nueva feature
# 🎨 UI/UX
# ♻️ Refactor
# 📝 Docs
# 🧹 Cleanup
```

### Branches (si se usan)

```bash
# feature/descripcion-corta
feature/agregar-filtro-expensas
fix/calculo-m2-incorrecto
```

---

## Testing

### Estructura

```python
# Archivo: test_*.py
# Función: test_nombre_descriptivo

def test_extraer_numero_con_miles():
    assert extraer_numero('$150.000', quitar_miles=True) == '150000'

def test_extraer_numero_sin_numero_retorna_none():
    assert extraer_numero('sin número') is None

def test_calcular_m2_faltantes_cuando_falta_desc():
    data = {'m2_cub': '50', 'm2_tot': '70'}
    result = calcular_m2_faltantes(data)
    assert result == {'m2_desc': '20'}
```

### Coverage Mínimo

- `helpers.py`: 90%+ (funciones puras, fáciles de testear)
- `scrapers.py`: 70%+ (mockear HTTP)
- `storage.py`: 50%+ (I/O es más difícil)

---

## Documentación

### CLAUDE.md

Mantener actualizado con:
- Estructura del proyecto
- Comandos principales
- Flujos de trabajo
- Notas de sesión (cambios importantes)
- Bugs conocidos

### Comentarios en Código

```python
# ✓ BIEN: Explica el POR QUÉ, no el QUÉ
# MercadoLibre a veces devuelve precios en miles (ej: 150 = $150.000)
if precio < 1000:
    precio = precio * 1000

# ✗ MAL: Comenta lo obvio
# Sumar 1 al contador
contador += 1
```

---

## Checklist de Calidad

Antes de commitear, verificar:

- [ ] ¿Los nombres son descriptivos?
- [ ] ¿Las funciones hacen una sola cosa?
- [ ] ¿Hay docstrings en funciones públicas?
- [ ] ¿Se escapan los datos de usuario (XSS)?
- [ ] ¿Los errores se manejan explícitamente?
- [ ] ¿Funciona en mobile?
- [ ] ¿Los tests pasan?
- [ ] ¿CLAUDE.md está actualizado si hubo cambios importantes?

---

## Anti-Patterns a Evitar

```python
# 1. Código muerto
# def funcion_vieja():  # TODO: borrar
#     pass

# 2. Números mágicos
if precio > 500000:  # ¿Por qué 500000?
# ✓ Mejor:
PRECIO_MAXIMO_RAZONABLE = 500000
if precio > PRECIO_MAXIMO_RAZONABLE:

# 3. Imports no usados
import os  # Nunca se usa

# 4. Print debugging olvidado
print("DEBUG:", data)  # Borrar antes de commit

# 5. Catch-all exceptions
except Exception:
    pass

# 6. Copy-paste de código
# Si algo se repite 3+ veces, extraer a función
```

---

*Última actualización: 2026-01-07*
