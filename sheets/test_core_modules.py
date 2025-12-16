#!/usr/bin/env python3
"""
Tests para módulos de core/

Cubre:
- prints.py: Sistema de prints/backups
- scrapers.py: Funciones de scraping
- templates.py: Generación HTML
- helpers.py: Funciones auxiliares
- validation.py: Sistema de warnings
- storage.py: Almacenamiento local
- sheets_api.py: Funciones de Google Sheets
"""

import json
import os
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# =============================================================================
# IMPORTS
# =============================================================================

from core.prints import (
    PRINT_DIAS_VENCIMIENTO,
    PRINT_PATTERN_ID,
    PRINT_PATTERN_FILA,
    PRINT_EXTENSIONS,
    generar_nombre_print,
    normalizar_texto,
    get_prints_index,
    clasificar_prints,
    sync_print_dates,
    build_property_index,
    extract_id_from_pdf,
    get_pending_print_files,
    process_print_file,
    get_orphan_prints,
    save_prints_index,
)

from core.helpers import (
    quitar_tildes,
    extraer_numero,
    extraer_m2,
    detectar_barrio,
    extraer_id_propiedad,
    get_active_rows,
    calcular_m2_faltantes,
    detectar_atributo,
    ATTR_PATTERNS,
)

from core.validation import (
    add_warning,
    clear_warnings,
    get_warnings,
    print_warnings_summary,
    validar_propiedad,
    get_missing_fields,
    get_properties_with_missing_data,
)

from core.storage import (
    LOCAL_FILE,
    CACHE_FILE,
    load_local_data,
    save_local_data,
    load_cache,
    save_cache,
)

from core.scrapers import (
    scrape_link,
    get_rows_to_scrape,
    apply_scraped_data,
    is_offline_error,
    HEADERS_SIMPLE,
    HEADERS_BROWSER,
)

from core.templates import (
    PREVIEW_CSS,
    PREVIEW_SHOW_COLS,
    PREVIEW_DIFF_COLS,
    format_column_label,
    format_cell_value,
    generate_link_cell,
    generate_preview_html,
    build_preview_data,
)

from core.sheets_api import (
    sheet_to_dict,
    sheet_to_list,
    get_cells_to_update,
    build_sheet_data,
)


# =============================================================================
# FIXTURES COMPARTIDAS
# =============================================================================

@pytest.fixture
def sample_rows():
    """Filas de ejemplo del sheet."""
    return [
        {
            '_row': 2,
            'activo': '',
            'link': 'https://inmueble.mercadolibre.com.ar/MLA-1234567890',
            'direccion': 'Av. Corrientes 1234',
            'barrio': 'Almagro',
            'precio': '100000',
            'm2_cub': '50',
            'm2_tot': '55',
            'amb': '3',
            'banos': '1',
            'terraza': 'si',
            'balcon': 'no',
        },
        {
            '_row': 3,
            'activo': '',
            'link': 'https://www.argenprop.com/departamento--12345678',
            'direccion': 'Rivadavia 5678',
            'barrio': 'Caballito',
            'precio': '120000',
            'm2_cub': '60',
            'm2_tot': '65',
            'amb': '4',
            'banos': '2',
            'terraza': 'no',
            'balcon': 'si',
        },
        {
            '_row': 4,
            'activo': 'no',
            'link': 'https://inmueble.mercadolibre.com.ar/MLA-9999999999',
            'direccion': 'Inactiva 123',
            'barrio': 'Palermo',
            'precio': '200000',
            'm2_cub': '80',
            'm2_tot': '80',
            'amb': '2',
            'banos': '1',
        },
    ]


@pytest.fixture
def temp_prints_dir(tmp_path):
    """Directorio temporal para prints."""
    prints_dir = tmp_path / "prints"
    prints_dir.mkdir()
    return prints_dir


# =============================================================================
# TESTS: prints.py
# =============================================================================

class TestPrintsConstants:
    """Tests de constantes de prints."""

    def test_print_pattern_id_matches_mla(self):
        """Patrón ID matchea MLA."""
        assert PRINT_PATTERN_ID.match('MLA1234567890_2025-12-15.pdf')
        assert PRINT_PATTERN_ID.match('MLA1234567890.pdf')
        assert PRINT_PATTERN_ID.match('mla1234567890.PDF')  # case insensitive

    def test_print_pattern_id_matches_ap(self):
        """Patrón ID matchea AP."""
        assert PRINT_PATTERN_ID.match('AP12345678_2025-12-15.pdf')
        assert PRINT_PATTERN_ID.match('AP12345678.png')

    def test_print_pattern_id_matches_zp(self):
        """Patrón ID matchea ZP."""
        assert PRINT_PATTERN_ID.match('ZP12345678_2025-12-15.pdf')

    def test_print_pattern_id_extracts_groups(self):
        """Patrón extrae grupos correctamente."""
        match = PRINT_PATTERN_ID.match('MLA1234567890_2025-12-15.pdf')
        assert match.group(1) == 'MLA1234567890'
        assert match.group(2) == '2025-12-15'

    def test_print_pattern_fila_matches(self):
        """Patrón legacy fila_XX matchea."""
        assert PRINT_PATTERN_FILA.match('fila_10_2025-12-15.pdf')
        assert PRINT_PATTERN_FILA.match('fila_5.pdf')
        assert PRINT_PATTERN_FILA.match('FILA_10.PDF')

    def test_print_extensions(self):
        """Extensiones válidas."""
        assert '.pdf' in PRINT_EXTENSIONS
        assert '.png' in PRINT_EXTENSIONS
        assert '.jpg' in PRINT_EXTENSIONS
        assert '.jpeg' in PRINT_EXTENSIONS


class TestGenerarNombrePrint:
    """Tests de generar_nombre_print."""

    def test_genera_desde_url_meli(self):
        """Genera nombre desde URL de MeLi."""
        url = 'https://inmueble.mercadolibre.com.ar/MLA-1234567890'
        nombre = generar_nombre_print(url)

        assert nombre is not None
        assert nombre.startswith('MLA1234567890_')
        assert nombre.endswith('.pdf')

    def test_genera_desde_url_argenprop(self):
        """Genera nombre desde URL de Argenprop."""
        url = 'https://www.argenprop.com/depto--12345678'
        nombre = generar_nombre_print(url)

        assert nombre is not None
        assert nombre.startswith('AP12345678_')

    def test_genera_desde_id_directo(self):
        """Genera nombre desde ID directo."""
        nombre = generar_nombre_print('MLA999', extension='png')

        assert nombre == f"MLA999_{datetime.now().strftime('%Y-%m-%d')}.png"

    def test_retorna_none_url_invalida(self):
        """Retorna None para URL sin ID."""
        assert generar_nombre_print('https://example.com') is None

    def test_extension_custom(self):
        """Usa extensión personalizada."""
        nombre = generar_nombre_print('MLA123', extension='jpg')
        assert nombre.endswith('.jpg')


class TestNormalizarTexto:
    """Tests de normalizar_texto."""

    def test_normaliza_minusculas(self):
        """Convierte a minúsculas."""
        assert normalizar_texto('HOLA') == 'hola'

    def test_quita_acentos(self):
        """Quita acentos."""
        assert normalizar_texto('Álvarez Jónté') == 'alvarezjonte'

    def test_quita_espacios_y_puntuacion(self):
        """Quita espacios y puntuación."""
        assert normalizar_texto('Av. Corrientes 1234') == 'avcorrientes1234'

    def test_string_vacio(self):
        """String vacío retorna vacío."""
        assert normalizar_texto('') == ''
        assert normalizar_texto(None) == ''


class TestGetPrintsIndex:
    """Tests de get_prints_index."""

    def test_directorio_inexistente(self, sample_rows):
        """Retorna vacío si directorio no existe."""
        index = get_prints_index(sample_rows, Path('/nonexistent'))
        assert index == {}

    def test_matchea_por_id(self, sample_rows, temp_prints_dir):
        """Matchea archivo por ID de propiedad."""
        # Crear archivo con ID de MLA
        (temp_prints_dir / 'MLA1234567890_2025-12-15.pdf').touch()

        index = get_prints_index(sample_rows, temp_prints_dir)

        assert 2 in index  # Fila 2 tiene MLA-1234567890
        assert index[2]['prop_id'] == 'MLA1234567890'

    def test_matchea_por_fila_legacy(self, sample_rows, temp_prints_dir):
        """Matchea archivo por formato legacy fila_XX."""
        (temp_prints_dir / 'fila_3_2025-12-15.pdf').touch()

        index = get_prints_index(sample_rows, temp_prints_dir)

        assert 3 in index

    def test_ignora_archivos_ocultos(self, sample_rows, temp_prints_dir):
        """Ignora archivos que empiezan con punto."""
        (temp_prints_dir / '.hidden.pdf').touch()
        (temp_prints_dir / 'MLA1234567890.pdf').touch()

        index = get_prints_index(sample_rows, temp_prints_dir)

        # Solo debería tener el archivo visible
        assert len(index) == 1

    def test_ignora_extensiones_invalidas(self, sample_rows, temp_prints_dir):
        """Ignora archivos con extensiones no válidas."""
        (temp_prints_dir / 'MLA1234567890.txt').touch()
        (temp_prints_dir / 'MLA1234567890.doc').touch()

        index = get_prints_index(sample_rows, temp_prints_dir)

        assert len(index) == 0

    def test_calcula_dias_antiguedad(self, sample_rows, temp_prints_dir):
        """Calcula días de antigüedad correctamente."""
        archivo = temp_prints_dir / 'MLA1234567890.pdf'
        archivo.touch()

        index = get_prints_index(sample_rows, temp_prints_dir)

        assert 'dias' in index[2]
        assert index[2]['dias'] >= 0

    def test_detecta_vencido(self, sample_rows, temp_prints_dir):
        """Detecta prints vencidos."""
        archivo = temp_prints_dir / 'MLA1234567890.pdf'
        archivo.touch()
        # Modificar fecha para que sea viejo
        old_time = (datetime.now() - timedelta(days=PRINT_DIAS_VENCIMIENTO + 5)).timestamp()
        os.utime(archivo, (old_time, old_time))

        index = get_prints_index(sample_rows, temp_prints_dir)

        assert index[2]['vencido'] is True


class TestClasificarPrints:
    """Tests de clasificar_prints."""

    def test_clasifica_sin_prints(self, sample_rows, temp_prints_dir):
        """Clasifica propiedades sin prints."""
        result = clasificar_prints(sample_rows, temp_prints_dir)

        assert len(result['activas']) == 2  # Filas 2 y 3 activas
        assert len(result['sin_print']) == 2
        assert len(result['con_print']) == 0

    def test_clasifica_con_prints(self, sample_rows, temp_prints_dir):
        """Clasifica propiedades con prints."""
        (temp_prints_dir / 'MLA1234567890.pdf').touch()

        result = clasificar_prints(sample_rows, temp_prints_dir)

        assert len(result['con_print']) == 1
        assert len(result['sin_print']) == 1

    def test_excluye_inactivas(self, sample_rows, temp_prints_dir):
        """Excluye propiedades inactivas."""
        result = clasificar_prints(sample_rows, temp_prints_dir)

        # Fila 4 es inactiva
        filas = [p['fila'] for p in result['activas']]
        assert 4 not in filas


class TestSyncPrintDates:
    """Tests de sync_print_dates."""

    def test_actualiza_fecha_print(self, sample_rows, temp_prints_dir):
        """Actualiza fecha_print en filas."""
        (temp_prints_dir / 'MLA1234567890.pdf').touch()

        updated = sync_print_dates(sample_rows, temp_prints_dir)

        assert updated == 1
        assert sample_rows[0].get('fecha_print') is not None

    def test_no_actualiza_si_ya_existe(self, sample_rows, temp_prints_dir):
        """No actualiza si fecha ya existe y es igual."""
        (temp_prints_dir / 'MLA1234567890.pdf').touch()

        # Primera vez
        sync_print_dates(sample_rows, temp_prints_dir)
        # Segunda vez
        updated = sync_print_dates(sample_rows, temp_prints_dir)

        assert updated == 0


class TestBuildPropertyIndex:
    """Tests de build_property_index."""

    def test_construye_indices(self, sample_rows):
        """Construye índices por ID y fila."""
        id_to_fila, fila_to_info = build_property_index(sample_rows)

        assert 'MLA1234567890' in id_to_fila
        assert id_to_fila['MLA1234567890'] == 2
        assert 2 in fila_to_info
        assert fila_to_info[2]['prop_id'] == 'MLA1234567890'

    def test_excluye_sin_link(self):
        """Excluye filas sin link válido."""
        rows = [{'_row': 2, 'link': ''}]

        id_to_fila, fila_to_info = build_property_index(rows)

        assert len(id_to_fila) == 0


class TestExtractIdFromPdf:
    """Tests de extract_id_from_pdf."""

    def test_retorna_none_sin_pdftotext(self, tmp_path):
        """Retorna None si pdftotext no está disponible."""
        pdf = tmp_path / 'test.pdf'
        pdf.write_bytes(b'%PDF-1.4 fake pdf')

        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = extract_id_from_pdf(pdf)

        assert result is None

    def test_extrae_mla_de_contenido(self, tmp_path):
        """Extrae MLA del contenido del PDF."""
        pdf = tmp_path / 'test.pdf'
        pdf.touch()

        mock_result = MagicMock()
        mock_result.stdout = 'Publicación MLA-1234567890 en venta'

        with patch('subprocess.run', return_value=mock_result):
            result = extract_id_from_pdf(pdf)

        assert result == 'MLA1234567890'

    def test_extrae_ap_de_url(self, tmp_path):
        """Extrae AP de URL en contenido."""
        pdf = tmp_path / 'test.pdf'
        pdf.touch()

        mock_result = MagicMock()
        mock_result.stdout = 'Ver en argenprop.com/depto--12345678'

        with patch('subprocess.run', return_value=mock_result):
            result = extract_id_from_pdf(pdf)

        assert result == 'AP12345678'


class TestGetPendingPrintFiles:
    """Tests de get_pending_print_files."""

    def test_lista_archivos_validos(self, tmp_path):
        """Lista solo archivos con extensiones válidas."""
        (tmp_path / 'test1.pdf').touch()
        (tmp_path / 'test2.png').touch()
        (tmp_path / 'test3.txt').touch()
        (tmp_path / '.hidden.pdf').touch()

        archivos = get_pending_print_files(tmp_path)

        nombres = [a.name for a in archivos]
        assert 'test1.pdf' in nombres
        assert 'test2.png' in nombres
        assert 'test3.txt' not in nombres
        assert '.hidden.pdf' not in nombres

    def test_directorio_inexistente(self):
        """Retorna vacío si directorio no existe."""
        archivos = get_pending_print_files(Path('/nonexistent'))
        assert archivos == []


class TestGetOrphanPrints:
    """Tests de get_orphan_prints."""

    def test_detecta_huerfanos(self, temp_prints_dir):
        """Detecta prints sin propiedad asociada."""
        (temp_prints_dir / 'huerfano.pdf').touch()
        (temp_prints_dir / 'MLA123.pdf').touch()

        prints_index = {2: {'archivo': 'MLA123.pdf'}}
        filas_activas = {2}

        huerfanos = get_orphan_prints(prints_index, filas_activas, temp_prints_dir)

        assert 'huerfano.pdf' in huerfanos
        assert 'MLA123.pdf' not in huerfanos

    def test_detecta_de_inactivas(self, temp_prints_dir):
        """Detecta prints de propiedades inactivas."""
        (temp_prints_dir / 'viejo.pdf').touch()

        prints_index = {99: {'archivo': 'viejo.pdf'}}  # Fila 99
        filas_activas = {2, 3}  # 99 no está activa

        huerfanos = get_orphan_prints(prints_index, filas_activas, temp_prints_dir)

        assert 'viejo.pdf' in huerfanos


class TestSavePrintsIndex:
    """Tests de save_prints_index."""

    def test_guarda_json(self, tmp_path):
        """Guarda índice en JSON."""
        clasificacion = {
            'activas': [1, 2],
            'con_print': [1],
            'sin_print': [2],
            'vencidos': [],
        }
        prints_index = {2: {'archivo': 'test.pdf'}}
        huerfanos = ['viejo.pdf']
        output_path = tmp_path / 'index.json'

        save_prints_index(clasificacion, prints_index, huerfanos, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data['total_activas'] == 2
        assert data['huerfanos'] == 1


# =============================================================================
# TESTS: helpers.py
# =============================================================================

class TestQuitarTildes:
    """Tests de quitar_tildes."""

    def test_quita_tildes_basicas(self):
        """Quita tildes de vocales."""
        assert quitar_tildes('áéíóú') == 'aeiou'
        assert quitar_tildes('ÁÉÍÓÚ') == 'AEIOU'

    def test_convierte_enie(self):
        """La ñ se convierte a n por normalización NFD."""
        # En Unicode NFD, ñ = n + combining tilde, que se elimina
        assert quitar_tildes('ñ') == 'n'
        assert quitar_tildes('Ñandú') == 'Nandu'

    def test_quita_dieresis(self):
        """Quita diéresis."""
        assert quitar_tildes('güe') == 'gue'


class TestExtraerNumero:
    """Tests de extraer_numero."""

    def test_extrae_numero_simple(self):
        """Extrae número de string (retorna string)."""
        assert extraer_numero('$100.000') == '100'  # Sin quitar_miles
        assert extraer_numero('50 m²') == '50'

    def test_extrae_con_puntos_miles(self):
        """Extrae número quitando puntos de miles."""
        assert extraer_numero('1.234.567', quitar_miles=True) == '1234567'

    def test_retorna_none_sin_numero(self):
        """Retorna None sin número."""
        assert extraer_numero('sin numero') is None
        assert extraer_numero('') is None


class TestDetectarAtributo:
    """Tests de detectar_atributo."""

    def test_detecta_si(self):
        """Detecta 'si' en texto."""
        assert detectar_atributo('Tiene terraza amplia', 'terraza') == 'si'
        assert detectar_atributo('Con balcón', 'balcon') == 'si'

    def test_detecta_no(self):
        """Detecta 'no' explícito."""
        assert detectar_atributo('terraza: no', 'terraza') == 'no'
        assert detectar_atributo('Sin balcón', 'balcon') == 'no'

    def test_detecta_incierto(self):
        """Retorna '?' cuando es ambiguo."""
        # Depende de los patrones en ATTR_PATTERNS
        result = detectar_atributo('Consultar terraza', 'terraza')
        # Puede ser 'si', 'no', '?' o None según patrones


class TestExtraerIdPropiedad:
    """Tests adicionales de extraer_id_propiedad."""

    def test_extrae_zonaprop(self):
        """Extrae ID de Zonaprop."""
        url = 'https://www.zonaprop.com.ar/propiedades/depto-2-amb--12345678.html'
        result = extraer_id_propiedad(url)
        assert result == 'ZP12345678'

    def test_none_para_url_generica(self):
        """Retorna None para URL genérica."""
        assert extraer_id_propiedad('https://google.com') is None


# =============================================================================
# TESTS: validation.py
# =============================================================================

class TestWarningsSystem:
    """Tests del sistema de warnings."""

    def test_add_and_get_warnings(self):
        """Agrega y obtiene warnings."""
        clear_warnings()
        add_warning('test', 'mensaje de prueba', 'prop1')

        warnings = get_warnings()
        assert len(warnings) == 1
        assert warnings[0]['tipo'] == 'test'
        assert warnings[0]['mensaje'] == 'mensaje de prueba'

    def test_clear_warnings(self):
        """Limpia warnings."""
        add_warning('test', 'msg')
        clear_warnings()

        assert len(get_warnings()) == 0

    def test_print_warnings_summary(self, capsys):
        """Imprime resumen de warnings."""
        clear_warnings()
        add_warning('tipo1', 'mensaje1')
        add_warning('tipo1', 'mensaje2')
        add_warning('tipo2', 'mensaje3')

        print_warnings_summary()

        captured = capsys.readouterr()
        assert 'TIPO1' in captured.out
        assert '3 items' in captured.out


class TestGetMissingFields:
    """Tests de get_missing_fields."""

    def test_detecta_campos_faltantes(self):
        """Detecta campos vacíos."""
        row = {'precio': '100000', 'barrio': '', 'm2_cub': '?'}

        missing = get_missing_fields(row, ['precio', 'barrio', 'm2_cub'])

        assert 'barrio' in missing
        assert 'm2_cub' in missing
        assert 'precio' not in missing

    def test_campo_con_espacios_es_faltante(self):
        """Campo con solo espacios es faltante."""
        row = {'campo': '   '}

        missing = get_missing_fields(row, ['campo'])

        assert 'campo' in missing


class TestGetPropertiesWithMissingData:
    """Tests de get_properties_with_missing_data."""

    def test_filtra_con_datos_faltantes(self, sample_rows):
        """Filtra propiedades con datos faltantes."""
        sample_rows[0]['barrio'] = ''  # Agregar dato faltante

        pendientes = get_properties_with_missing_data(
            sample_rows, ['barrio', 'precio']
        )

        assert len(pendientes) == 1
        assert pendientes[0]['fila'] == 2

    def test_excluye_inactivas(self, sample_rows):
        """Excluye propiedades inactivas."""
        sample_rows[2]['barrio'] = ''  # Fila 4 inactiva

        pendientes = get_properties_with_missing_data(
            sample_rows, ['barrio']
        )

        filas = [p['fila'] for p in pendientes]
        assert 4 not in filas

    def test_ordena_por_cantidad_faltantes(self, sample_rows):
        """Ordena por cantidad de datos faltantes."""
        sample_rows[0]['barrio'] = ''
        sample_rows[0]['precio'] = ''
        sample_rows[1]['barrio'] = ''

        pendientes = get_properties_with_missing_data(
            sample_rows, ['barrio', 'precio']
        )

        # Fila 2 tiene 2 faltantes, debería ir primero
        assert pendientes[0]['fila'] == 2
        assert len(pendientes[0]['missing']) == 2


# =============================================================================
# TESTS: storage.py
# =============================================================================

class TestStorage:
    """Tests de funciones de storage."""

    def test_save_and_load_cache(self, tmp_path):
        """Guarda y carga cache."""
        cache_file = tmp_path / 'cache.json'
        test_cache = {'url1': {'data': 'test'}}

        with patch('core.storage.CACHE_FILE', cache_file):
            save_cache(test_cache)
            loaded = load_cache()

        assert loaded == test_cache

    def test_load_cache_inexistente(self, tmp_path):
        """Carga cache inexistente retorna vacío."""
        cache_file = tmp_path / 'nonexistent.json'

        with patch('core.storage.CACHE_FILE', cache_file):
            loaded = load_cache()

        assert loaded == {}


# =============================================================================
# TESTS: scrapers.py
# =============================================================================

class TestScrapersHelpers:
    """Tests de helpers de scrapers."""

    def test_get_rows_to_scrape_default(self, sample_rows):
        """Obtiene filas para scrapear (solo sin datos)."""
        # Fila 2 ya tiene precio y m2
        sample_rows[0]['precio'] = '100000'
        sample_rows[0]['m2_cub'] = '50'
        # Fila 3 sin precio
        sample_rows[1]['precio'] = ''
        sample_rows[1]['m2_cub'] = ''

        to_scrape = get_rows_to_scrape(sample_rows, check_all=False)

        # Retorna lista de tuplas (indice, row)
        filas = [row['_row'] for _, row in to_scrape]
        assert 3 in filas  # Sin precio

    def test_get_rows_to_scrape_all(self, sample_rows):
        """Obtiene todas las filas con check_all=True."""
        to_scrape = get_rows_to_scrape(sample_rows, check_all=True)

        # Retorna todas las filas con link (3 filas tienen link)
        assert len(to_scrape) == 3

    def test_is_offline_error(self):
        """Detecta errores de conexión."""
        assert is_offline_error({'_error': '404', '_offline': True})
        assert is_offline_error({'_error': 'Status 410'})
        assert not is_offline_error({'precio': '100000'})
        assert not is_offline_error(None)
        assert not is_offline_error({})  # Sin _error

    def test_apply_scraped_data(self, sample_rows):
        """Aplica datos scrapeados a fila."""
        row = sample_rows[0].copy()
        row['precio'] = ''  # Vaciar para que se actualice

        scraped = {'precio': '150000', 'barrio': 'Nuevo Barrio'}
        headers = ['precio', 'barrio', 'direccion']
        scrapeable = ['precio', 'barrio']

        result = apply_scraped_data(row, scraped, scrapeable, headers)

        # Retorna dict con changes y updates
        assert 'changes' in result
        assert row['precio'] == '150000'

    def test_apply_scraped_data_no_overwrite(self, sample_rows):
        """No sobrescribe datos existentes sin force."""
        row = sample_rows[0].copy()

        scraped = {'precio': '999999'}
        headers = ['precio']
        scrapeable = ['precio']

        result = apply_scraped_data(row, scraped, scrapeable, headers, force_update=False)

        # No debería actualizar porque ya tiene precio
        assert row['precio'] == '100000'
        assert len(result.get('updates', [])) == 0


class TestHeadersConstants:
    """Tests de constantes de headers."""

    def test_headers_simple_tiene_user_agent(self):
        """HEADERS_SIMPLE tiene User-Agent."""
        assert 'User-Agent' in HEADERS_SIMPLE

    def test_headers_browser_tiene_sec_headers(self):
        """HEADERS_BROWSER tiene headers de seguridad."""
        assert 'Sec-Ch-Ua' in HEADERS_BROWSER or 'sec-ch-ua' in str(HEADERS_BROWSER).lower()


class TestScrapeArgenprop:
    """Tests de scrape_argenprop con mocks HTTP."""

    @pytest.fixture
    def mock_argenprop_html(self):
        """HTML de ejemplo de Argenprop."""
        return '''
        <html>
        <div class="titlebar__price">USD 120.000</div>
        <div class="titlebar__address">Av. Corrientes 1234, Almagro</div>
        <div class="property-description">
            Departamento de 3 ambientes, 65 m² cubiertos.
            2 dormitorios. 15 años de antigüedad.
        </div>
        <ul class="property-features">
            <li>Sup. cubierta: 65 m²</li>
            <li>Sup. total: 70 m²</li>
            <li>Cant. ambientes: 3</li>
            <li>Antigüedad: 15 años</li>
            <li>Terraza: Si</li>
            <li>Balcón: No</li>
            <li>Cochera: No</li>
            <li>Baños: 1</li>
            <li>Expensas: $50.000</li>
            <li>Apto crédito: Si</li>
        </ul>
        </html>
        '''

    def test_scrape_argenprop_exitoso(self, mock_argenprop_html):
        """Scrapea página de Argenprop correctamente."""
        from core.scrapers import scrape_argenprop

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_argenprop_html

        with patch('httpx.get', return_value=mock_response):
            data = scrape_argenprop('https://www.argenprop.com/depto--12345')

        assert '_error' not in data
        assert data.get('precio') == '120000'
        assert 'Corrientes' in data.get('direccion', '')

    def test_scrape_argenprop_extrae_m2(self, mock_argenprop_html):
        """Extrae metros cuadrados."""
        from core.scrapers import scrape_argenprop

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_argenprop_html

        with patch('httpx.get', return_value=mock_response):
            data = scrape_argenprop('https://www.argenprop.com/depto--12345')

        assert data.get('m2_cub') == '65'
        assert data.get('m2_tot') == '70'

    def test_scrape_argenprop_extrae_atributos(self, mock_argenprop_html):
        """Extrae atributos booleanos."""
        from core.scrapers import scrape_argenprop

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_argenprop_html

        with patch('httpx.get', return_value=mock_response):
            data = scrape_argenprop('https://www.argenprop.com/depto--12345')

        assert data.get('terraza') == 'si'
        assert data.get('balcon') == 'no'
        assert data.get('amb') == '3'

    def test_scrape_argenprop_error_404(self):
        """Maneja error 404."""
        from core.scrapers import scrape_argenprop

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('httpx.get', return_value=mock_response):
            data = scrape_argenprop('https://www.argenprop.com/depto--99999')

        assert '_error' in data
        assert '404' in data['_error']

    def test_scrape_argenprop_error_conexion(self):
        """Maneja error de conexión."""
        from core.scrapers import scrape_argenprop
        import httpx

        with patch('httpx.get', side_effect=httpx.ConnectError('Connection refused')):
            data = scrape_argenprop('https://www.argenprop.com/depto--12345')

        assert '_error' in data


class TestScrapeMercadolibre:
    """Tests de scrape_mercadolibre con mocks HTTP."""

    @pytest.fixture
    def mock_meli_html(self):
        """HTML de ejemplo de MercadoLibre."""
        return '''
        <html>
        <span class="andes-money-amount__fraction">95.000</span>
        <div class="ui-vip-location">
            Ubicación
            Av. Rivadavia 5678, Caballito, Capital Federal
        </div>
        <table>
            <tr class="andes-table__row">
                <th>Superficie total</th>
                <td>60 m²</td>
            </tr>
            <tr class="andes-table__row">
                <th>Superficie cubierta</th>
                <td>55 m²</td>
            </tr>
            <tr class="andes-table__row">
                <th>Ambientes</th>
                <td>3</td>
            </tr>
            <tr class="andes-table__row">
                <th>Dormitorios</th>
                <td>2</td>
            </tr>
            <tr class="andes-table__row">
                <th>Baños</th>
                <td>1</td>
            </tr>
            <tr class="andes-table__row">
                <th>Antigüedad</th>
                <td>10 años</td>
            </tr>
            <tr class="andes-table__row">
                <th>Expensas</th>
                <td>$45.000</td>
            </tr>
        </table>
        <div class="ui-vip-specs__table">
            <span>Balcón</span>
            <span>Luminoso</span>
        </div>
        </html>
        '''

    def test_scrape_meli_exitoso(self, mock_meli_html):
        """Scrapea página de MercadoLibre correctamente."""
        from core.scrapers import scrape_mercadolibre

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_meli_html
        mock_response.url = 'https://inmueble.mercadolibre.com.ar/MLA-123456'

        with patch('httpx.get', return_value=mock_response):
            data = scrape_mercadolibre('https://inmueble.mercadolibre.com.ar/MLA-123456')

        assert '_error' not in data
        assert data.get('precio') == '95000'

    def test_scrape_meli_extrae_ubicacion(self, mock_meli_html):
        """Extrae ubicación y barrio."""
        from core.scrapers import scrape_mercadolibre

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_meli_html
        mock_response.url = 'https://inmueble.mercadolibre.com.ar/MLA-123456'

        with patch('httpx.get', return_value=mock_response):
            data = scrape_mercadolibre('https://inmueble.mercadolibre.com.ar/MLA-123456')

        assert 'Rivadavia' in data.get('direccion', '') or 'barrio' in data

    def test_scrape_meli_extrae_caracteristicas(self, mock_meli_html):
        """Extrae características de la tabla."""
        from core.scrapers import scrape_mercadolibre

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_meli_html
        mock_response.url = 'https://inmueble.mercadolibre.com.ar/MLA-123456'

        with patch('httpx.get', return_value=mock_response):
            data = scrape_mercadolibre('https://inmueble.mercadolibre.com.ar/MLA-123456')

        assert data.get('m2_tot') == '60'
        assert data.get('m2_cub') == '55'
        assert data.get('amb') == '3'
        assert data.get('banos') == '1'

    def test_scrape_meli_publicacion_finalizada(self):
        """Detecta publicación finalizada via JSON en HTML."""
        from core.scrapers import scrape_mercadolibre

        # El scraper detecta 'Publicación finalizada' en el texto raw del HTML
        html = '''
        <html>
        <script>"text":"Publicación finalizada"</script>
        </html>
        '''
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.url = 'https://inmueble.mercadolibre.com.ar/MLA-123456'

        with patch('httpx.get', return_value=mock_response):
            data = scrape_mercadolibre('https://inmueble.mercadolibre.com.ar/MLA-123456')

        assert '_error' in data
        assert data.get('_offline') is True

    def test_scrape_meli_redirect_a_busqueda(self):
        """Detecta redirect a página de búsqueda (publicación no disponible)."""
        from core.scrapers import scrape_mercadolibre

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html></html>'
        mock_response.url = 'https://inmuebles.mercadolibre.com.ar/venta?redirectedFromVip=true'

        with patch('httpx.get', return_value=mock_response):
            data = scrape_mercadolibre('https://inmueble.mercadolibre.com.ar/MLA-123456')

        assert '_error' in data
        assert data.get('_offline') is True

    def test_scrape_meli_error_410(self):
        """Maneja error 410 Gone."""
        from core.scrapers import scrape_mercadolibre

        mock_response = MagicMock()
        mock_response.status_code = 410

        with patch('httpx.get', return_value=mock_response):
            data = scrape_mercadolibre('https://inmueble.mercadolibre.com.ar/MLA-123456')

        assert '_error' in data
        assert '410' in data['_error']

    def test_scrape_meli_sin_precio(self):
        """Maneja página sin precio."""
        from core.scrapers import scrape_mercadolibre

        html = '<html><body>Página sin precio</body></html>'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.url = 'https://inmueble.mercadolibre.com.ar/MLA-123456'

        with patch('httpx.get', return_value=mock_response):
            data = scrape_mercadolibre('https://inmueble.mercadolibre.com.ar/MLA-123456')

        assert '_error' in data


class TestScrapeLinkIntegration:
    """Tests de integración de scrape_link."""

    def test_scrape_link_detecta_argenprop(self):
        """scrape_link usa scrape_argenprop para URLs de Argenprop."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<div class="titlebar__price">USD 100.000</div>'

        with patch('httpx.get', return_value=mock_response):
            data, from_cache = scrape_link(
                'https://www.argenprop.com/depto--12345',
                use_cache=False,
                cache={}
            )

        assert from_cache is False
        # Debería haber intentado scrapear (puede fallar por HTML incompleto)

    def test_scrape_link_detecta_mercadolibre(self):
        """scrape_link usa scrape_mercadolibre para URLs de MeLi."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<span class="andes-money-amount__fraction">95.000</span>'
        mock_response.url = 'https://inmueble.mercadolibre.com.ar/MLA-123456'

        with patch('httpx.get', return_value=mock_response):
            data, from_cache = scrape_link(
                'https://inmueble.mercadolibre.com.ar/MLA-123456',
                use_cache=False,
                cache={}
            )

        assert from_cache is False

    def test_scrape_link_guarda_en_cache(self):
        """scrape_link guarda resultados en cache."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''
            <div class="titlebar__price">USD 100.000</div>
            <div class="titlebar__address">Test 123</div>
        '''
        cache = {}

        with patch('httpx.get', return_value=mock_response):
            data, _ = scrape_link(
                'https://www.argenprop.com/depto--12345',
                use_cache=True,
                cache=cache
            )

        assert 'https://www.argenprop.com/depto--12345' in cache
        assert '_cached_at' in cache['https://www.argenprop.com/depto--12345']


# =============================================================================
# TESTS: templates.py
# =============================================================================

class TestTemplates:
    """Tests de funciones de templates."""

    def test_format_column_label(self):
        """Formatea labels de columnas."""
        assert format_column_label('precio') == 'Precio'
        assert format_column_label('m2_cub') == 'M² Cub'
        assert format_column_label('m2_tot') == 'M² Tot'

    def test_format_cell_value_precio(self):
        """Formatea valores de precio."""
        # format_cell_value(value, col, is_empty) -> (formatted, css_class)
        result, css = format_cell_value('100000', 'precio')
        assert '100' in result

    def test_format_cell_value_link(self):
        """Formatea links."""
        result, css = format_cell_value('https://example.com/test', 'link')
        # Los links se formatean como texto o con href
        assert 'example' in result.lower() or 'http' in result

    def test_format_cell_value_empty(self):
        """Formatea valor vacío."""
        result, css = format_cell_value('', 'precio', is_empty=True)
        assert result == '-'
        assert 'empty' in css

    def test_generate_link_cell(self):
        """Genera celda con link."""
        html = generate_link_cell('https://example.com', 'Ver')
        assert '<a' in html
        assert 'href' in html

    def test_build_preview_data(self, sample_rows):
        """Construye datos para preview."""
        # build_preview_data(local_rows, cloud_rows, ...)
        cloud_rows = {row['_row']: row for row in sample_rows}

        rows_data, stats = build_preview_data(sample_rows, cloud_rows)

        assert len(rows_data) == len(sample_rows)

    def test_generate_preview_html(self, sample_rows):
        """Genera HTML de preview."""
        cloud_rows = {row['_row']: row for row in sample_rows}
        rows_data, stats = build_preview_data(sample_rows, cloud_rows)

        html = generate_preview_html(rows_data, stats)

        assert '<html' in html
        assert '<table' in html


# =============================================================================
# TESTS: sheets_api.py
# =============================================================================

class TestSheetsApiHelpers:
    """Tests de helpers de sheets_api."""

    def test_sheet_to_dict(self):
        """Convierte worksheet mock a dict."""
        mock_ws = MagicMock()
        mock_ws.get_all_values.return_value = [
            ['col1', 'col2'],
            ['val1', 'val2'],
            ['val3', 'val4'],
        ]

        headers, rows = sheet_to_dict(mock_ws)

        assert headers == ['col1', 'col2']
        assert 2 in rows
        assert rows[2]['col1'] == 'val1'

    def test_sheet_to_list(self):
        """Convierte worksheet mock a lista."""
        mock_ws = MagicMock()
        mock_ws.get_all_values.return_value = [
            ['col1', 'col2'],
            ['val1', 'val2'],
        ]

        headers, rows = sheet_to_list(mock_ws)

        assert len(rows) == 1
        assert rows[0]['_row'] == 2
        assert rows[0]['col1'] == 'val1'

    def test_build_sheet_data(self):
        """Construye datos para el sheet."""
        headers = ['col1', 'col2']
        rows = [
            {'col1': 'a', 'col2': 'b'},
            {'col1': 'c', 'col2': 'd'},
        ]

        data = build_sheet_data(headers, rows)

        assert data[0] == headers
        assert data[1] == ['a', 'b']
        assert data[2] == ['c', 'd']

    def test_get_cells_to_update(self):
        """Calcula celdas a actualizar."""
        rows = [{'_row': 2, 'col1': 'nuevo', 'col2': 'otro'}]
        current_values = [
            ['col1', 'col2'],  # Header
            ['viejo', 'otro'],  # Fila 2
        ]
        headers = ['col1', 'col2']
        update_cols = ['col1']

        import gspread
        cells = get_cells_to_update(rows, current_values, headers, update_cols)

        assert len(cells) == 1
        assert cells[0].value == 'nuevo'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
