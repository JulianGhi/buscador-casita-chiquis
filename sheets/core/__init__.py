"""
Modulos de sync_sheet organizados.

Estructura:
- helpers: Funciones puras de extraccion y calculo
- scrapers: Scrapers para cada portal
- sheets_api: Conexion a Google Sheets
- storage: Carga/guardado de archivos locales
- validation: Sistema de warnings y validacion
"""

from .helpers import (
    # Constantes
    BARRIOS_CABA,
    ATTR_PATTERNS,
    # Funciones de extraccion
    quitar_tildes,
    extraer_numero,
    extraer_m2,
    detectar_barrio,
    extraer_id_propiedad,
    # Funciones de filtrado
    get_active_rows,
    # Funciones de calculo
    calcular_m2_faltantes,
    # Deteccion de atributos
    detectar_atributo,
)

from .scrapers import (
    scrape_argenprop,
    scrape_mercadolibre,
    scrape_link,
    HEADERS_SIMPLE,
    HEADERS_BROWSER,
)

from .sheets_api import (
    SCOPES,
    SHEET_ID,
    WORKSHEET_NAME,
    get_client,
    get_worksheet,
    sheet_to_dict,
    sheet_to_list,
)

from .storage import (
    LOCAL_FILE,
    CACHE_FILE,
    PRINTS_DIR,
    PRINTS_INDEX,
    load_local_data,
    save_local_data,
    require_local_data,
    load_cache,
    save_cache,
)

from .validation import (
    add_warning,
    clear_warnings,
    get_warnings,
    print_warnings_summary,
    validar_propiedad,
)
