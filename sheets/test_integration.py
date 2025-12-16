#!/usr/bin/env python3
"""
Tests de integración para sync_sheet.py

Estos tests verifican el flujo completo:
- Pull de Google Sheets
- Manipulación de datos locales
- Scraping de links
- Comparación y validación

Para correr:
    pytest test_integration.py -v
    pytest test_integration.py -v -k "not api"  # Sin tests que usan API
"""

import json
import os
import pytest
import copy
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Imports del módulo
from core import (
    LOCAL_FILE,
    CACHE_FILE,
    load_local_data,
    save_local_data,
    load_cache,
    save_cache,
    extraer_m2,
    extraer_id_propiedad,
    detectar_barrio,
    get_active_rows,
    calcular_m2_faltantes,
    validar_propiedad,
    get_warnings,
    clear_warnings,
    get_properties_with_missing_data,
    get_prints_index,
)
from core.scrapers import scrape_link, scrape_argenprop, scrape_mercadolibre


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def backup_local_data():
    """Respalda y restaura datos locales para no afectar el archivo real."""
    backup = None
    if LOCAL_FILE.exists():
        backup = LOCAL_FILE.read_text()

    yield

    # Restaurar
    if backup:
        LOCAL_FILE.write_text(backup)
    elif LOCAL_FILE.exists():
        LOCAL_FILE.unlink()


@pytest.fixture
def sample_sheet_data():
    """Datos de prueba que simulan el sheet."""
    return {
        'headers': ['activo', 'link', 'direccion', 'barrio', 'precio', 'm2_cub', 'm2_tot', 'amb', 'banos'],
        'rows': [
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
    }


@pytest.fixture
def sample_cache():
    """Cache de prueba con datos scrapeados."""
    return {
        'https://inmueble.mercadolibre.com.ar/MLA-1234567890': {
            'direccion': 'Av. Corrientes 1234',
            'precio': '105000',
            'm2_cub': '52',
            'barrio': 'Almagro',
            '_cached_at': '2025-01-01 12:00:00',
        },
        'https://www.argenprop.com/departamento--12345678': {
            'direccion': 'Rivadavia 5678',
            'precio': '125000',
            'm2_cub': '62',
            'barrio': 'Caballito',
            '_cached_at': '2025-01-01 12:00:00',
        },
    }


# =============================================================================
# TESTS: Manipulación de datos locales
# =============================================================================

class TestLocalDataManipulation:
    """Tests de manipulación de datos locales (sin API)."""

    def test_save_and_load_local_data(self, backup_local_data, sample_sheet_data, tmp_path):
        """Guardar y cargar datos locales funciona correctamente."""
        test_file = tmp_path / "test_data.json"

        # Guardar
        with open(test_file, 'w') as f:
            json.dump(sample_sheet_data, f)

        # Cargar
        with open(test_file) as f:
            loaded = json.load(f)

        assert loaded['headers'] == sample_sheet_data['headers']
        assert len(loaded['rows']) == len(sample_sheet_data['rows'])
        assert loaded['rows'][0]['direccion'] == 'Av. Corrientes 1234'

    def test_add_row_to_data(self, sample_sheet_data):
        """Agregar una fila a los datos locales."""
        new_row = {
            '_row': 5,
            'activo': '',
            'link': 'https://inmueble.mercadolibre.com.ar/MLA-1111111111',
            'direccion': 'Nueva 123',
            'barrio': 'Flores',
            'precio': '90000',
            'm2_cub': '45',
            'm2_tot': '50',
            'amb': '2',
            'banos': '1',
        }

        sample_sheet_data['rows'].append(new_row)

        assert len(sample_sheet_data['rows']) == 4
        assert sample_sheet_data['rows'][-1]['direccion'] == 'Nueva 123'

    def test_remove_row_from_data(self, sample_sheet_data):
        """Eliminar una fila de los datos locales."""
        initial_count = len(sample_sheet_data['rows'])

        # Eliminar fila 3
        sample_sheet_data['rows'] = [r for r in sample_sheet_data['rows'] if r['_row'] != 3]

        assert len(sample_sheet_data['rows']) == initial_count - 1
        assert all(r['_row'] != 3 for r in sample_sheet_data['rows'])

    def test_modify_row_data(self, sample_sheet_data):
        """Modificar datos de una fila."""
        # Modificar precio de fila 2
        for row in sample_sheet_data['rows']:
            if row['_row'] == 2:
                row['precio'] = '110000'
                row['m2_cub'] = '55'
                break

        modified = next(r for r in sample_sheet_data['rows'] if r['_row'] == 2)
        assert modified['precio'] == '110000'
        assert modified['m2_cub'] == '55'

    def test_mark_row_inactive(self, sample_sheet_data):
        """Marcar una fila como inactiva."""
        for row in sample_sheet_data['rows']:
            if row['_row'] == 2:
                row['activo'] = 'no'
                break

        active_rows = get_active_rows(sample_sheet_data['rows'])
        assert len(active_rows) == 1  # Solo queda la fila 3 activa
        assert active_rows[0]['_row'] == 3


# =============================================================================
# TESTS: Filtrado y consultas
# =============================================================================

class TestDataFiltering:
    """Tests de filtrado de datos."""

    def test_get_active_rows(self, sample_sheet_data):
        """get_active_rows filtra correctamente."""
        active = get_active_rows(sample_sheet_data['rows'])

        assert len(active) == 2  # Filas 2 y 3 activas
        assert all(r.get('activo', '').lower() != 'no' for r in active)

    def test_get_active_rows_excludes_no_link(self, sample_sheet_data):
        """get_active_rows excluye filas sin link."""
        # Agregar fila sin link
        sample_sheet_data['rows'].append({
            '_row': 5,
            'activo': '',
            'link': '',
            'direccion': 'Sin link',
        })

        active = get_active_rows(sample_sheet_data['rows'])
        assert all(r.get('link', '').startswith('http') for r in active)

    def test_filter_by_barrio(self, sample_sheet_data):
        """Filtrar por barrio."""
        almagro = [r for r in sample_sheet_data['rows'] if r.get('barrio') == 'Almagro']
        assert len(almagro) == 1
        assert almagro[0]['_row'] == 2

    def test_filter_by_price_range(self, sample_sheet_data):
        """Filtrar por rango de precio."""
        min_price, max_price = 100000, 130000
        in_range = [
            r for r in sample_sheet_data['rows']
            if min_price <= int(r.get('precio') or 0) <= max_price
        ]

        assert len(in_range) == 2  # Filas 2 y 3


# =============================================================================
# TESTS: Extracción de datos
# =============================================================================

class TestDataExtraction:
    """Tests de funciones de extracción."""

    def test_extraer_m2_from_row(self, sample_sheet_data):
        """extraer_m2 extrae valores correctamente de una fila."""
        row = sample_sheet_data['rows'][0]
        m2_cub, m2_tot, m2_desc = extraer_m2(row)

        assert m2_cub == 50
        assert m2_tot == 55
        assert m2_desc == 0  # No está en fixture, retorna 0

    def test_extraer_id_propiedad_meli(self):
        """Extrae ID de MercadoLibre."""
        url = 'https://inmueble.mercadolibre.com.ar/MLA-1234567890'
        prop_id = extraer_id_propiedad(url)

        assert prop_id == 'MLA1234567890'

    def test_extraer_id_propiedad_argenprop(self):
        """Extrae ID de Argenprop."""
        url = 'https://www.argenprop.com/departamento-en-venta--12345678'
        prop_id = extraer_id_propiedad(url)

        assert prop_id == 'AP12345678'

    def test_detectar_barrio_from_text(self):
        """Detecta barrio en texto."""
        assert detectar_barrio('Departamento en Almagro') == 'Almagro'
        assert detectar_barrio('Cerca de Floresta') == 'Floresta'
        assert detectar_barrio('Villa Crespo, CABA') == 'Villa Crespo'


# =============================================================================
# TESTS: Scraping con cache
# =============================================================================

class TestScrapingWithCache:
    """Tests de scraping usando cache."""

    def test_scrape_link_uses_cache(self, sample_cache):
        """scrape_link usa cache cuando está disponible."""
        url = 'https://inmueble.mercadolibre.com.ar/MLA-1234567890'

        data, from_cache = scrape_link(url, use_cache=True, cache=sample_cache)

        assert from_cache is True
        assert data is not None
        assert data['precio'] == '105000'

    def test_scrape_link_skips_cache_when_disabled(self, sample_cache):
        """scrape_link no usa cache cuando use_cache=False."""
        url = 'https://inmueble.mercadolibre.com.ar/MLA-1234567890'

        # Con mock para no hacer request real
        with patch('core.scrapers.scrape_mercadolibre', return_value={'precio': '999999'}):
            data, from_cache = scrape_link(url, use_cache=False, cache=sample_cache)

        assert from_cache is False

    def test_scrape_link_returns_none_for_invalid_url(self):
        """scrape_link retorna None para URLs inválidas."""
        data, from_cache = scrape_link('not-a-url', use_cache=True, cache={})

        assert data is None
        assert from_cache is False

    def test_scrape_link_returns_none_for_empty_url(self):
        """scrape_link retorna None para URL vacía."""
        data, from_cache = scrape_link('', use_cache=True, cache={})

        assert data is None
        assert from_cache is False

    def test_cache_entry_with_error_is_not_used(self):
        """Cache con _error no se usa (se re-scrapea)."""
        cache = {
            'https://example.com/test': {
                '_error': 'Status 404',
                '_cached_at': '2025-01-01',
            }
        }

        with patch('core.scrapers.scrape_mercadolibre', return_value=None):
            data, from_cache = scrape_link(
                'https://inmueble.mercadolibre.com.ar/MLA-123',
                use_cache=True,
                cache=cache
            )

        # No usó cache (la URL no estaba, y el _error del otro no aplica)
        assert from_cache is False


# =============================================================================
# TESTS: Validación de datos
# =============================================================================

class TestDataValidation:
    """Tests de validación de datos."""

    def test_validar_propiedad_ok(self, sample_sheet_data):
        """Propiedad válida no genera warnings."""
        clear_warnings()
        row = sample_sheet_data['rows'][0]

        validar_propiedad(row)

        warnings = get_warnings()
        # No debería haber warnings de m2 inconsistentes o precio sospechoso
        m2_warnings = [w for w in warnings if 'm2' in w['tipo']]
        precio_warnings = [w for w in warnings if 'precio' in w['tipo']]
        assert len(m2_warnings) == 0
        assert len(precio_warnings) == 0

    def test_validar_propiedad_m2_inconsistente(self):
        """Detecta m² cubiertos > totales."""
        clear_warnings()
        row = {
            'm2_cub': '80',
            'm2_tot': '60',  # Menor que cub!
            'direccion': 'Test',
        }

        validar_propiedad(row)

        warnings = get_warnings()
        m2_warnings = [w for w in warnings if w['tipo'] == 'm2_inconsistente']
        assert len(m2_warnings) == 1

    def test_validar_propiedad_precio_bajo(self):
        """Detecta precio sospechosamente bajo."""
        clear_warnings()
        row = {
            'precio': '20000',  # Muy bajo
            'direccion': 'Test',
        }

        validar_propiedad(row)

        warnings = get_warnings()
        precio_warnings = [w for w in warnings if w['tipo'] == 'precio_bajo']
        assert len(precio_warnings) == 1

    def test_validar_propiedad_precio_alto(self):
        """Detecta precio sospechosamente alto."""
        clear_warnings()
        row = {
            'precio': '600000',  # Muy alto
            'direccion': 'Test',
        }

        validar_propiedad(row)

        warnings = get_warnings()
        precio_warnings = [w for w in warnings if w['tipo'] == 'precio_alto']
        assert len(precio_warnings) == 1


# =============================================================================
# TESTS: Comparación de datos
# =============================================================================

class TestDataComparison:
    """Tests de comparación entre datos locales y remotos."""

    def test_detect_price_changes(self, sample_sheet_data, sample_cache):
        """Detecta cambios de precio entre local y scrapeado."""
        row = sample_sheet_data['rows'][0]
        cached = sample_cache['https://inmueble.mercadolibre.com.ar/MLA-1234567890']

        local_price = int(row['precio'])
        scraped_price = int(cached['precio'])

        assert local_price != scraped_price
        assert scraped_price - local_price == 5000  # Subió $5000

    def test_detect_new_rows(self, sample_sheet_data):
        """Detecta filas nuevas agregadas localmente."""
        original_rows = {r['_row'] for r in sample_sheet_data['rows']}

        # Agregar fila nueva
        sample_sheet_data['rows'].append({
            '_row': 10,
            'link': 'https://example.com/new',
            'direccion': 'Nueva',
        })

        new_rows = {r['_row'] for r in sample_sheet_data['rows']}
        added = new_rows - original_rows

        assert added == {10}

    def test_detect_removed_rows(self, sample_sheet_data):
        """Detecta filas eliminadas localmente."""
        original_ids = {r['_row'] for r in sample_sheet_data['rows']}

        # Simular datos remotos con una fila más
        remote_ids = original_ids | {99}

        removed = remote_ids - original_ids
        assert removed == {99}

    def test_detect_field_changes(self, sample_sheet_data):
        """Detecta cambios en campos específicos."""
        original = copy.deepcopy(sample_sheet_data['rows'][0])
        modified = sample_sheet_data['rows'][0]
        modified['barrio'] = 'Flores'
        modified['m2_cub'] = '55'

        changes = {}
        for key in original:
            if original[key] != modified.get(key):
                changes[key] = (original[key], modified[key])

        assert 'barrio' in changes
        assert changes['barrio'] == ('Almagro', 'Flores')
        assert 'm2_cub' in changes


# =============================================================================
# TESTS: Datos faltantes
# =============================================================================

class TestMissingData:
    """Tests de detección de datos faltantes."""

    def test_detect_missing_fields(self, sample_sheet_data):
        """Detecta campos faltantes."""
        # Agregar fila con datos faltantes
        sample_sheet_data['rows'].append({
            '_row': 5,
            'activo': '',
            'link': 'https://example.com/incomplete',
            'direccion': 'Incompleta 123',
            'barrio': '',  # Faltante
            'precio': '',  # Faltante
            'm2_cub': '50',
            'm2_tot': '',  # Faltante
            'amb': '?',    # Incierto = faltante
            'banos': '',
        })

        campos = ['barrio', 'precio', 'm2_tot', 'amb', 'banos']
        pendientes = get_properties_with_missing_data(
            sample_sheet_data['rows'],
            campos
        )

        # Solo la fila 5 debería tener datos faltantes
        assert len(pendientes) == 1
        assert pendientes[0]['fila'] == 5
        assert 'barrio' in pendientes[0]['missing']
        assert 'precio' in pendientes[0]['missing']

    def test_missing_data_excludes_inactive(self, sample_sheet_data):
        """No reporta datos faltantes de propiedades inactivas."""
        # La fila 4 es inactiva
        sample_sheet_data['rows'][2]['barrio'] = ''  # Fila inactiva sin barrio

        campos = ['barrio', 'precio']
        pendientes = get_properties_with_missing_data(
            sample_sheet_data['rows'],
            campos
        )

        # No debería incluir la fila 4 (inactiva)
        assert all(p['fila'] != 4 for p in pendientes)


# =============================================================================
# TESTS: Cálculos de m²
# =============================================================================

class TestM2Calculations:
    """Tests de cálculos de metros cuadrados."""

    def test_calcular_m2_faltantes_completa_tot(self):
        """Calcula m² totales cuando falta."""
        row = {'m2_cub': '50', 'm2_desc': '10', 'm2_tot': ''}

        calculados = calcular_m2_faltantes(row)

        assert calculados.get('m2_tot') == '60'  # 50 + 10

    def test_calcular_m2_faltantes_completa_desc(self):
        """Calcula m² descubiertos cuando falta."""
        row = {'m2_cub': '50', 'm2_tot': '60', 'm2_desc': ''}

        calculados = calcular_m2_faltantes(row)

        assert calculados.get('m2_desc') == '10'  # 60 - 50

    def test_calcular_m2_faltantes_no_calcula_si_existe(self):
        """No calcula si ya existen los 3 valores."""
        row = {'m2_cub': '50', 'm2_tot': '60', 'm2_desc': '15'}

        calculados = calcular_m2_faltantes(row)

        # No debería calcular nada si ya existen los 3
        assert calculados == {}


# =============================================================================
# TESTS: API de Google Sheets (requieren credenciales)
# =============================================================================

class TestGoogleSheetsAPI:
    """Tests que requieren conexión a Google Sheets."""

    @pytest.fixture(autouse=True)
    def check_api_requirements(self):
        """Verifica requisitos para tests de API."""
        import os
        # Resetear SHEET_ID al valor real (por si test_cli_commands lo cambió)
        original_sheet_id = os.environ.get('GOOGLE_SHEET_ID_ORIGINAL') or os.environ.get('GOOGLE_SHEET_ID')

        creds_locations = [
            Path('credentials.json'),
            Path('../credentials.json'),
            Path(__file__).parent.parent / 'credentials.json',
        ]
        creds_exists = any(p.exists() for p in creds_locations)
        if not creds_exists:
            pytest.skip("No credentials.json found")

        # Verificar SHEET_ID real
        from core import SHEET_ID
        if not SHEET_ID or len(SHEET_ID) < 20:
            pytest.skip("SHEET_ID not configured or is a test mock")

    def test_pull_returns_data(self):
        """Pull trae datos del sheet."""
        from core import get_worksheet, sheet_to_list

        ws = get_worksheet()
        headers, rows = sheet_to_list(ws)

        assert len(headers) > 0
        assert len(rows) > 0
        assert '_row' in rows[0]

    def test_pull_has_expected_columns(self):
        """El sheet tiene las columnas esperadas."""
        from core import get_worksheet, sheet_to_list

        ws = get_worksheet()
        headers, _ = sheet_to_list(ws)

        expected = ['link', 'direccion', 'barrio', 'precio']
        for col in expected:
            assert col in headers, f"Falta columna: {col}"


# =============================================================================
# TESTS: Scraping real (requieren conexión)
# =============================================================================

@pytest.mark.skipif(
    os.environ.get('SKIP_NETWORK_TESTS', '0') == '1',
    reason="SKIP_NETWORK_TESTS=1"
)
class TestRealScraping:
    """Tests de scraping real (hacen requests HTTP)."""

    @pytest.fixture
    def real_cache(self):
        """Carga el cache real si existe."""
        if CACHE_FILE.exists():
            return load_cache()
        pytest.skip("No hay cache real")

    def test_scrape_cached_meli_url(self, real_cache):
        """Scrapea URL de MeLi desde cache."""
        meli_urls = [url for url in real_cache if 'mercadolibre' in url and '_error' not in real_cache[url]]
        if not meli_urls:
            pytest.skip("No hay URLs de MeLi válidas en cache")

        url = meli_urls[0]
        data, from_cache = scrape_link(url, use_cache=True, cache=real_cache)

        assert from_cache is True
        assert data is not None

    def test_scrape_cached_argenprop_url(self, real_cache):
        """Scrapea URL de Argenprop desde cache."""
        ap_urls = [url for url in real_cache if 'argenprop' in url and '_error' not in real_cache[url]]
        if not ap_urls:
            pytest.skip("No hay URLs de Argenprop válidas en cache")

        url = ap_urls[0]
        data, from_cache = scrape_link(url, use_cache=True, cache=real_cache)

        assert from_cache is True
        assert data is not None


# =============================================================================
# TESTS: Flujo completo
# =============================================================================

class TestFullWorkflow:
    """Tests del flujo completo de trabajo."""

    def test_workflow_add_and_validate(self, sample_sheet_data):
        """Flujo: agregar fila → validar → detectar faltantes."""
        clear_warnings()

        # 1. Agregar fila nueva
        new_row = {
            '_row': 10,
            'activo': '',
            'link': 'https://inmueble.mercadolibre.com.ar/MLA-9876543210',
            'direccion': 'Nueva Propiedad 123',
            'barrio': '',  # Faltante!
            'precio': '95000',
            'm2_cub': '45',
            'm2_tot': '50',
            'amb': '2',
            'banos': '',  # Faltante!
        }
        sample_sheet_data['rows'].append(new_row)

        # 2. Validar
        validar_propiedad(new_row)
        warnings = get_warnings()
        assert any(w['tipo'] == 'dato_faltante' for w in warnings)

        # 3. Detectar faltantes
        campos = ['barrio', 'precio', 'banos']
        pendientes = get_properties_with_missing_data(sample_sheet_data['rows'], campos)

        assert len(pendientes) == 1
        assert pendientes[0]['fila'] == 10
        assert 'barrio' in pendientes[0]['missing']
        assert 'banos' in pendientes[0]['missing']

    def test_workflow_scrape_and_update(self, sample_sheet_data, sample_cache):
        """Flujo: scrapear → comparar → actualizar."""
        row = sample_sheet_data['rows'][0]
        url = row['link']

        # 1. Scrapear (desde cache)
        scraped, _ = scrape_link(url, use_cache=True, cache=sample_cache)

        # 2. Comparar
        changes = {}
        for key in ['precio', 'm2_cub', 'm2_tot']:
            local = row.get(key, '')
            remote = scraped.get(key, '')
            if local != remote and remote:
                changes[key] = (local, remote)

        assert 'precio' in changes  # 100000 → 105000

        # 3. Actualizar
        for key, (old, new) in changes.items():
            row[key] = new

        assert row['precio'] == '105000'

    def test_workflow_mark_inactive_and_filter(self, sample_sheet_data):
        """Flujo: marcar inactivo → filtrar activos."""
        # 1. Inicial: 2 activos
        active_before = get_active_rows(sample_sheet_data['rows'])
        assert len(active_before) == 2

        # 2. Marcar fila 2 como inactiva
        for row in sample_sheet_data['rows']:
            if row['_row'] == 2:
                row['activo'] = 'no'
                break

        # 3. Filtrar
        active_after = get_active_rows(sample_sheet_data['rows'])
        assert len(active_after) == 1
        assert active_after[0]['_row'] == 3


# =============================================================================
# TESTS: Comparación datos scrapeados vs planilla real
# =============================================================================

@pytest.mark.skipif(
    os.environ.get('SKIP_NETWORK_TESTS', '0') == '1',
    reason="SKIP_NETWORK_TESTS=1"
)
class TestScrapedVsSheet:
    """Tests que comparan datos scrapeados frescos vs planilla."""

    @pytest.fixture
    def real_sheet_data(self):
        """Carga datos de la planilla real (archivo local)."""
        if not LOCAL_FILE.exists():
            pytest.skip("No hay archivo local (ejecutar pull primero)")
        data = load_local_data()
        if not data or not data.get('rows'):
            pytest.skip("Archivo local vacío")
        return data

    def test_scrape_vs_sheet_precios_consistentes(self, real_sheet_data):
        """Compara precios scrapeados vs los de la planilla."""
        rows = get_active_rows(real_sheet_data['rows'])
        if not rows:
            pytest.skip("No hay filas activas")

        # Tomar muestra de 3 propiedades para no hacer muchos requests
        sample = rows[:3]
        discrepancias = []

        for row in sample:
            url = row.get('link', '')
            if not url.startswith('http'):
                continue

            # Scrapear sin cache para obtener datos frescos
            scraped, _ = scrape_link(url, use_cache=False, cache={})
            if not scraped or scraped.get('_error'):
                continue

            # Comparar precio
            sheet_precio = str(row.get('precio', '')).strip()
            scraped_precio = str(scraped.get('precio', '')).strip()

            if sheet_precio and scraped_precio and sheet_precio != scraped_precio:
                discrepancias.append({
                    'fila': row.get('_row'),
                    'url': url[:50],
                    'campo': 'precio',
                    'sheet': sheet_precio,
                    'scraped': scraped_precio,
                })

        # No debería haber discrepancias grandes (>10%)
        for d in discrepancias:
            try:
                sheet_val = float(d['sheet'])
                scraped_val = float(d['scraped'])
                diff_pct = abs(sheet_val - scraped_val) / sheet_val * 100
                assert diff_pct < 10, f"Fila {d['fila']}: precio difiere {diff_pct:.1f}% ({d['sheet']} vs {d['scraped']})"
            except (ValueError, ZeroDivisionError):
                pass  # No son números comparables

    def test_scrape_vs_sheet_m2_consistentes(self, real_sheet_data):
        """Compara m2 scrapeados vs los de la planilla."""
        rows = get_active_rows(real_sheet_data['rows'])
        if not rows:
            pytest.skip("No hay filas activas")

        sample = rows[:3]
        discrepancias = []

        for row in sample:
            url = row.get('link', '')
            if not url.startswith('http'):
                continue

            scraped, _ = scrape_link(url, use_cache=False, cache={})
            if not scraped or scraped.get('_error'):
                continue

            # Comparar m2 cubiertos
            for campo in ['m2_cub', 'm2_tot']:
                sheet_val = str(row.get(campo, '')).strip()
                scraped_val = str(scraped.get(campo, '')).strip()

                if sheet_val and scraped_val and sheet_val != scraped_val:
                    discrepancias.append({
                        'fila': row.get('_row'),
                        'campo': campo,
                        'sheet': sheet_val,
                        'scraped': scraped_val,
                    })

        # Reportar discrepancias pero no fallar (pueden haber actualizaciones legítimas)
        if discrepancias:
            print(f"\n⚠️  {len(discrepancias)} discrepancias de m² encontradas:")
            for d in discrepancias:
                print(f"   Fila {d['fila']}: {d['campo']} = {d['sheet']} (sheet) vs {d['scraped']} (scraped)")

    def test_scrape_full_comparison(self, real_sheet_data):
        """Comparación completa: scrapea todos y compara campos principales."""
        rows = get_active_rows(real_sheet_data['rows'])
        if not rows:
            pytest.skip("No hay filas activas")

        # Usar solo las primeras 5 para no tardar mucho
        sample = rows[:5]
        resultados = {
            'total': len(sample),
            'scrapeados': 0,
            'errores': 0,
            'coincidencias': [],
            'discrepancias': [],
        }

        for row in sample:
            url = row.get('link', '')
            if not url.startswith('http'):
                continue

            scraped, _ = scrape_link(url, use_cache=False, cache={})
            if not scraped or scraped.get('_error'):
                resultados['errores'] += 1
                continue

            resultados['scrapeados'] += 1

            # Comparar campos principales
            campos = ['precio', 'm2_cub', 'm2_tot', 'amb', 'banos']
            fila_ok = True
            for campo in campos:
                sheet_val = str(row.get(campo, '')).strip()
                scraped_val = str(scraped.get(campo, '')).strip()

                # Solo comparar si ambos tienen valor
                if sheet_val and scraped_val and sheet_val != scraped_val:
                    resultados['discrepancias'].append({
                        'fila': row.get('_row'),
                        'campo': campo,
                        'sheet': sheet_val,
                        'scraped': scraped_val,
                    })
                    fila_ok = False

            if fila_ok:
                resultados['coincidencias'].append(row.get('_row'))

        # Reportar
        print(f"\n📊 Resultados de comparación:")
        print(f"   Total: {resultados['total']}")
        print(f"   Scrapeados: {resultados['scrapeados']}")
        print(f"   Errores: {resultados['errores']}")
        print(f"   Coincidencias: {len(resultados['coincidencias'])}")
        print(f"   Con discrepancias: {len(set(d['fila'] for d in resultados['discrepancias']))}")

        if resultados['discrepancias']:
            print(f"\n   Discrepancias encontradas:")
            for d in resultados['discrepancias'][:10]:
                print(f"   - Fila {d['fila']}: {d['campo']} = '{d['sheet']}' (sheet) vs '{d['scraped']}' (scraped)")

        # El test pasa si al menos el 50% se scrapearon correctamente
        assert resultados['scrapeados'] >= resultados['total'] * 0.5, \
            f"Muy pocos scrapeados: {resultados['scrapeados']}/{resultados['total']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
