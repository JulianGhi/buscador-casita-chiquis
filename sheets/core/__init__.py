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
    # Inferencia de valores
    inferir_valores_faltantes,
)

from .scrapers import (
    scrape_argenprop,
    scrape_mercadolibre,
    scrape_link,
    HEADERS_SIMPLE,
    HEADERS_BROWSER,
    # Helpers de scraping
    get_rows_to_scrape,
    apply_scraped_data,
    is_offline_error,
)

from .sheets_api import (
    SCOPES,
    SHEET_ID,
    WORKSHEET_NAME,
    get_client,
    get_worksheet,
    sheet_to_dict,
    sheet_to_list,
    # Funciones de push
    get_cells_to_update,
    build_sheet_data,
    format_header_row,
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
    get_cache_for_url,
)

from .validation import (
    add_warning,
    clear_warnings,
    get_warnings,
    print_warnings_summary,
    validar_propiedad,
    get_missing_fields,
    get_properties_with_missing_data,
)

from .prints import (
    # Constantes
    PRINT_DIAS_VENCIMIENTO,
    PRINT_PATTERN_ID,
    PRINT_PATTERN_FILA,
    PRINT_EXTENSIONS,
    # Funciones
    generar_nombre_print,
    normalizar_texto,
    get_prints_index,
    clasificar_prints,
    sync_print_dates,
    # Funciones de scan
    build_property_index,
    extract_id_from_pdf,
    get_pending_print_files,
    process_print_file,
    get_orphan_prints,
    save_prints_index,
    # Funciones de extracción de datos de PDFs
    extraer_texto_pdf,
    extraer_datos_pdf,
    validar_datos_pdf_vs_sheet,
    analizar_prints_vs_sheet,
    # Funciones de comparación de 3 fuentes
    comparar_tres_fuentes,
    analizar_tres_fuentes,
)

from .templates import (
    # Constantes
    PREVIEW_CSS,
    PREVIEW_SHOW_COLS,
    PREVIEW_DIFF_COLS,
    # Funciones
    format_column_label,
    format_cell_value,
    generate_link_cell,
    generate_preview_html,
    build_preview_data,
)
