"""
Funciones de almacenamiento local.

Incluye:
- Carga/guardado de datos JSON
- Cache de scraping
- Constantes de paths
"""

import json
from datetime import datetime
from pathlib import Path

# =============================================================================
# PATHS
# =============================================================================

LOCAL_FILE = Path('data/sheet_data.json')
CACHE_FILE = Path('data/scrape_cache.json')
PRINTS_DIR = Path('data/prints')
PRINTS_INDEX = Path('data/prints/index.json')


# =============================================================================
# DATOS LOCALES (sheet_data.json)
# =============================================================================

def load_local_data():
    """Carga datos del archivo JSON local.

    Returns:
        dict con headers y rows, o None si no existe
    """
    if not LOCAL_FILE.exists():
        return None
    with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_local_data(data):
    """Guarda datos al archivo JSON local."""
    LOCAL_FILE.parent.mkdir(exist_ok=True)
    with open(LOCAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def require_local_data():
    """Verifica que exista LOCAL_FILE. Imprime error si no.

    Returns:
        bool: True si existe, False si no
    """
    if not LOCAL_FILE.exists():
        print(f"❌ No existe {LOCAL_FILE}")
        print("   Ejecutá primero: python sync_sheet.py pull")
        return False
    return True


# =============================================================================
# CACHE DE SCRAPING (scrape_cache.json)
# =============================================================================

def load_cache():
    """Carga el cache de scraping.

    Returns:
        dict con URL -> datos scrapeados
    """
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Guarda el cache de scraping."""
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_cache_for_url(url, cache=None, max_age_days=30):
    """Obtiene datos del cache para una URL específica.

    Args:
        url: URL a buscar en el cache
        cache: Cache ya cargado (opcional, si no se pasa se carga)
        max_age_days: Máximo de días de antigüedad para considerar válido

    Returns:
        dict con:
            - data: datos del cache (None si no existe o es muy viejo)
            - age_days: antigüedad en días (None si no existe)
            - is_stale: True si >7 días pero <max_age_days
            - is_expired: True si >max_age_days
    """
    if cache is None:
        cache = load_cache()

    result = {
        'data': None,
        'age_days': None,
        'is_stale': False,
        'is_expired': False,
    }

    if url not in cache:
        return result

    entry = cache[url]

    # Calcular antigüedad
    cached_at = entry.get('_cached_at')
    if cached_at:
        try:
            cache_date = datetime.strptime(cached_at, '%Y-%m-%d %H:%M:%S')
            age = (datetime.now() - cache_date).days
            result['age_days'] = age
            result['is_stale'] = age > 7
            result['is_expired'] = age > max_age_days
        except ValueError:
            pass

    # Solo devolver datos si no está expirado
    if not result['is_expired']:
        # Filtrar campos internos (_cached_at, _error)
        result['data'] = {k: v for k, v in entry.items() if not k.startswith('_')}

    return result
