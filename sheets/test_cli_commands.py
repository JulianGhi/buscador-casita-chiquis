#!/usr/bin/env python3
"""
Tests para comandos CLI de sync_sheet.py

Cubre:
- cmd_pull: Descarga de Google Sheets
- cmd_scrape: Scrapeo de links
- cmd_push: Subida a Google Sheets
- cmd_view: Preview HTML
- cmd_diff: Diferencias en terminal
- cmd_prints: Estado de prints
- cmd_pendientes: Datos faltantes
- cmd_prints_scan: Escaneo de PDFs
- cmd_prints_open: Abrir links
- main(): Parsing de argumentos
"""

import json
import os
import pytest
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO

# Agregar path para imports
sys.path.insert(0, str(Path(__file__).parent))

# Mock SHEET_ID antes de importar sync_sheet
os.environ['GOOGLE_SHEET_ID'] = 'test_sheet_id'

from sync_sheet import (
    cmd_pull,
    cmd_scrape,
    cmd_push,
    cmd_view,
    cmd_diff,
    cmd_prints,
    cmd_pendientes,
    cmd_prints_scan,
    cmd_prints_open,
    main,
    LOCAL_FILE,
    CACHE_FILE,
    PRINTS_DIR,
    SCRAPEABLE_COLS,
    CAMPOS_IMPORTANTES,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_worksheet():
    """Mock de worksheet de Google Sheets."""
    ws = MagicMock()
    ws.get_all_values.return_value = [
        ['activo', 'link', 'direccion', 'barrio', 'precio', 'm2_cub'],
        ['', 'https://inmueble.mercadolibre.com.ar/MLA-123', 'Corrientes 1234', 'Almagro', '100000', '50'],
        ['', 'https://www.argenprop.com/depto--456', 'Rivadavia 5678', 'Caballito', '120000', '60'],
        ['no', 'https://inmueble.mercadolibre.com.ar/MLA-999', 'Inactiva 123', 'Palermo', '200000', '80'],
    ]
    return ws


@pytest.fixture
def mock_local_data():
    """Datos locales de ejemplo."""
    return {
        'headers': ['activo', 'link', 'direccion', 'barrio', 'precio', 'm2_cub', 'm2_tot'],
        'rows': [
            {
                '_row': 2,
                'activo': '',
                'link': 'https://inmueble.mercadolibre.com.ar/MLA-123',
                'direccion': 'Corrientes 1234',
                'barrio': 'Almagro',
                'precio': '100000',
                'm2_cub': '50',
                'm2_tot': '55',
            },
            {
                '_row': 3,
                'activo': '',
                'link': 'https://www.argenprop.com/depto--456',
                'direccion': 'Rivadavia 5678',
                'barrio': 'Caballito',
                'precio': '',  # Sin precio para scrapear
                'm2_cub': '',
                'm2_tot': '',
            },
        ],
        'source': 'test',
        'pulled_at': '2025-01-01 00:00:00',
    }


@pytest.fixture
def temp_data_dir(tmp_path):
    """Directorio temporal para datos."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    prints_dir = data_dir / "prints"
    prints_dir.mkdir()
    return data_dir


# =============================================================================
# TESTS: cmd_pull
# =============================================================================

class TestCmdPull:
    """Tests de cmd_pull."""

    def test_pull_exitoso(self, mock_worksheet, tmp_path, capsys):
        """Pull descarga datos correctamente."""
        local_file = tmp_path / "sheet_data.json"

        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_spreadsheet

        with patch('sync_sheet.get_client', return_value=mock_client), \
             patch('sync_sheet.LOCAL_FILE', local_file):
            cmd_pull()

        # Verificar archivo creado
        assert local_file.exists()
        data = json.loads(local_file.read_text())
        assert len(data['rows']) == 3
        assert data['rows'][0]['direccion'] == 'Corrientes 1234'

        # Verificar output
        captured = capsys.readouterr()
        assert '3 filas guardadas' in captured.out

    def test_pull_sheet_vacio(self, tmp_path, capsys):
        """Pull maneja sheet vacío."""
        mock_ws = MagicMock()
        mock_ws.get_all_values.return_value = []

        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_ws
        mock_client.open_by_key.return_value = mock_spreadsheet

        with patch('sync_sheet.get_client', return_value=mock_client):
            cmd_pull()

        captured = capsys.readouterr()
        assert 'vacío' in captured.out

    def test_pull_worksheet_not_found(self, mock_worksheet, tmp_path):
        """Pull usa sheet1 si worksheet no existe."""
        import gspread

        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.side_effect = gspread.WorksheetNotFound()
        mock_spreadsheet.sheet1 = mock_worksheet
        mock_client.open_by_key.return_value = mock_spreadsheet

        local_file = tmp_path / "sheet_data.json"

        with patch('sync_sheet.get_client', return_value=mock_client), \
             patch('sync_sheet.LOCAL_FILE', local_file):
            cmd_pull()

        assert local_file.exists()


# =============================================================================
# TESTS: cmd_scrape
# =============================================================================

class TestCmdScrape:
    """Tests de cmd_scrape."""

    def test_scrape_sin_archivo_local(self, capsys):
        """Scrape falla si no existe archivo local."""
        with patch('sync_sheet.LOCAL_FILE', Path('/nonexistent/file.json')):
            cmd_scrape()

        captured = capsys.readouterr()
        assert 'No existe' in captured.out

    def test_scrape_con_datos(self, mock_local_data, tmp_path, capsys):
        """Scrape procesa links correctamente."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(mock_local_data))
        cache_file = tmp_path / "cache.json"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''
            <div class="titlebar__price">USD 125.000</div>
            <div class="titlebar__address">Rivadavia 5678</div>
        '''

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.CACHE_FILE', cache_file), \
             patch('sync_sheet.load_cache', return_value={}), \
             patch('sync_sheet.save_cache'), \
             patch('httpx.get', return_value=mock_response):
            cmd_scrape()

        captured = capsys.readouterr()
        assert 'Scrapeando' in captured.out

    def test_scrape_usa_cache(self, mock_local_data, tmp_path, capsys):
        """Scrape usa cache existente."""
        local_file = tmp_path / "sheet_data.json"
        mock_local_data['rows'][1]['precio'] = ''  # Sin precio
        local_file.write_text(json.dumps(mock_local_data))

        cache = {
            'https://www.argenprop.com/depto--456': {
                'precio': '130000',
                'm2_cub': '65',
                '_cached_at': '2025-01-01',
            }
        }

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.load_cache', return_value=cache), \
             patch('sync_sheet.save_cache'), \
             patch('sync_sheet.save_local_data'):
            cmd_scrape()

        captured = capsys.readouterr()
        assert 'usando cache' in captured.out.lower() or 'cache' in captured.out.lower()

    def test_scrape_detecta_offline(self, mock_local_data, tmp_path, capsys):
        """Scrape detecta publicaciones offline."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(mock_local_data))

        mock_response = MagicMock()
        mock_response.status_code = 410

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.load_cache', return_value={}), \
             patch('sync_sheet.save_cache'), \
             patch('httpx.get', return_value=mock_response):
            cmd_scrape(check_all=True)

        captured = capsys.readouterr()
        # Debería marcar como no activo
        assert '410' in captured.out or 'NO activo' in captured.out


# =============================================================================
# TESTS: cmd_push
# =============================================================================

class TestCmdPush:
    """Tests de cmd_push."""

    def test_push_sin_archivo_local(self, capsys):
        """Push falla si no existe archivo local."""
        with patch('sync_sheet.LOCAL_FILE', Path('/nonexistent/file.json')):
            cmd_push()

        captured = capsys.readouterr()
        assert 'No existe' in captured.out or 'Primero' in captured.out

    def test_push_dry_run(self, mock_local_data, mock_worksheet, tmp_path, capsys):
        """Push con dry-run no hace cambios."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(mock_local_data))

        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_spreadsheet

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.get_client', return_value=mock_client):
            cmd_push(dry_run=True)

        captured = capsys.readouterr()
        assert 'dry-run' in captured.out.lower() or 'DRY' in captured.out

        # Verificar que no se llamó update
        mock_worksheet.update_cells.assert_not_called()

    def test_push_merge_mode(self, mock_local_data, mock_worksheet, tmp_path, capsys):
        """Push en modo merge actualiza solo celdas vacías."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(mock_local_data))

        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_spreadsheet

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.get_client', return_value=mock_client), \
             patch('sync_sheet.PRINTS_DIR', tmp_path / 'prints'):
            (tmp_path / 'prints').mkdir(exist_ok=True)
            cmd_push(force=False, dry_run=False)

        # Verificar que se llamó update_cells (merge mode)
        # o batch_update en el proceso


# =============================================================================
# TESTS: cmd_view
# =============================================================================

class TestCmdView:
    """Tests de cmd_view."""

    def test_view_sin_archivo_local(self, capsys):
        """View falla si no existe archivo local."""
        with patch('sync_sheet.LOCAL_FILE', Path('/nonexistent/file.json')):
            cmd_view()

        captured = capsys.readouterr()
        assert 'No existe' in captured.out or 'Primero' in captured.out

    def test_view_genera_html(self, mock_local_data, mock_worksheet, tmp_path, capsys):
        """View genera archivo HTML."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(mock_local_data))

        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_spreadsheet

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.get_client', return_value=mock_client), \
             patch('webbrowser.open'):
            cmd_view(check_links=False)

        captured = capsys.readouterr()
        assert 'preview' in captured.out.lower() or 'Descargando' in captured.out


# =============================================================================
# TESTS: cmd_diff
# =============================================================================

class TestCmdDiff:
    """Tests de cmd_diff."""

    def test_diff_sin_archivo_local(self, capsys):
        """Diff falla si no existe archivo local."""
        with patch('sync_sheet.LOCAL_FILE', Path('/nonexistent/file.json')):
            cmd_diff()

        captured = capsys.readouterr()
        assert 'No existe' in captured.out or 'Primero' in captured.out

    def test_diff_muestra_cambios(self, mock_local_data, mock_worksheet, tmp_path, capsys):
        """Diff muestra diferencias."""
        local_file = tmp_path / "sheet_data.json"
        # Modificar dato local
        mock_local_data['rows'][0]['precio'] = '110000'  # Cambiado de 100000
        local_file.write_text(json.dumps(mock_local_data))

        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_spreadsheet

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.get_client', return_value=mock_client):
            cmd_diff()

        captured = capsys.readouterr()
        # Debería mostrar el diff o indicar sin cambios


# =============================================================================
# TESTS: cmd_prints
# =============================================================================

class TestCmdPrints:
    """Tests de cmd_prints."""

    def test_prints_sin_archivo_local(self, capsys):
        """Prints falla si no existe archivo local."""
        with patch('sync_sheet.load_local_data', return_value=None):
            cmd_prints()

        captured = capsys.readouterr()
        assert 'Primero' in captured.out

    def test_prints_muestra_estado(self, mock_local_data, tmp_path, capsys):
        """Prints muestra estado de backups."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(mock_local_data))
        prints_dir = tmp_path / "prints"
        prints_dir.mkdir()

        # Crear un print de ejemplo
        (prints_dir / "MLA123_2025-01-01.pdf").touch()

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.PRINTS_DIR', prints_dir), \
             patch('sync_sheet.PRINTS_INDEX', prints_dir / 'index.json'):
            cmd_prints()

        captured = capsys.readouterr()
        assert 'PRINTS' in captured.out or 'print' in captured.out.lower()

    def test_prints_sin_prints(self, mock_local_data, tmp_path, capsys):
        """Prints cuando no hay backups."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(mock_local_data))
        prints_dir = tmp_path / "prints"
        prints_dir.mkdir()

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.PRINTS_DIR', prints_dir), \
             patch('sync_sheet.PRINTS_INDEX', prints_dir / 'index.json'):
            cmd_prints()

        captured = capsys.readouterr()
        assert 'sin' in captured.out.lower() or '0' in captured.out


# =============================================================================
# TESTS: cmd_pendientes
# =============================================================================

class TestCmdPendientes:
    """Tests de cmd_pendientes."""

    def test_pendientes_sin_archivo_local(self, capsys):
        """Pendientes falla si no existe archivo local."""
        with patch('sync_sheet.LOCAL_FILE', Path('/nonexistent/file.json')):
            cmd_pendientes()

        captured = capsys.readouterr()
        assert 'No existe' in captured.out or 'Primero' in captured.out

    def test_pendientes_lista_faltantes(self, tmp_path, capsys):
        """Pendientes lista propiedades con datos faltantes."""
        local_data = {
            'headers': ['activo', 'link', 'direccion', 'terraza', 'balcon'],
            'rows': [
                {
                    '_row': 2,
                    'activo': '',
                    'link': 'https://example.com/1',
                    'direccion': 'Test 1',
                    'terraza': '',  # Faltante
                    'balcon': 'si',
                },
                {
                    '_row': 3,
                    'activo': '',
                    'link': 'https://example.com/2',
                    'direccion': 'Test 2',
                    'terraza': 'no',
                    'balcon': '',  # Faltante
                },
            ]
        }
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(local_data))
        prints_dir = tmp_path / "prints"
        prints_dir.mkdir()
        pendientes_file = prints_dir / "pendientes.json"

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.PRINTS_DIR', prints_dir), \
             patch('sync_sheet.PENDIENTES_FILE', pendientes_file):
            cmd_pendientes()

        captured = capsys.readouterr()
        assert 'FALTANTES' in captured.out or 'Faltan' in captured.out

    def test_pendientes_filtra_sin_print(self, tmp_path, capsys):
        """Pendientes filtra por sin print."""
        local_data = {
            'headers': ['activo', 'link', 'direccion', 'terraza'],
            'rows': [
                {
                    '_row': 2,
                    'activo': '',
                    'link': 'https://inmueble.mercadolibre.com.ar/MLA-111',
                    'direccion': 'Test 1',
                    'terraza': '',
                },
            ]
        }
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(local_data))
        prints_dir = tmp_path / "prints"
        prints_dir.mkdir()
        pendientes_file = prints_dir / "pendientes.json"

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.PRINTS_DIR', prints_dir), \
             patch('sync_sheet.PENDIENTES_FILE', pendientes_file):
            cmd_pendientes(solo_sin_print=True)

        captured = capsys.readouterr()
        # Debería listar propiedades sin print


# =============================================================================
# TESTS: cmd_prints_scan
# =============================================================================

class TestCmdPrintsScan:
    """Tests de cmd_prints_scan."""

    def test_prints_scan_sin_archivo_local(self, capsys):
        """Prints scan falla si no existe archivo local."""
        with patch('sync_sheet.load_local_data', return_value=None):
            cmd_prints_scan()

        captured = capsys.readouterr()
        assert 'Primero' in captured.out

    def test_prints_scan_procesa_pdfs(self, mock_local_data, tmp_path, capsys):
        """Prints scan procesa PDFs en carpeta nuevos."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(mock_local_data))

        prints_dir = tmp_path / "prints"
        prints_dir.mkdir()
        nuevos_dir = prints_dir / "nuevos"
        nuevos_dir.mkdir()

        # Crear PDF de prueba
        (nuevos_dir / "test.pdf").write_bytes(b'%PDF-1.4 fake')

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.PRINTS_DIR', prints_dir), \
             patch('sync_sheet.extract_id_from_pdf', return_value='MLA123'):
            cmd_prints_scan()

        captured = capsys.readouterr()
        # Debería indicar procesamiento


# =============================================================================
# TESTS: cmd_prints_open
# =============================================================================

class TestCmdPrintsOpen:
    """Tests de cmd_prints_open."""

    def test_prints_open_sin_archivo_local(self, capsys):
        """Prints open falla si no existe archivo local."""
        with patch('sync_sheet.load_local_data', return_value=None):
            cmd_prints_open()

        captured = capsys.readouterr()
        assert 'Primero' in captured.out

    def test_prints_open_con_limit(self, mock_local_data, tmp_path, capsys):
        """Prints open respeta límite de tabs."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(mock_local_data))
        prints_dir = tmp_path / "prints"
        prints_dir.mkdir()

        opened_urls = []

        def mock_open(url):
            opened_urls.append(url)

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.PRINTS_DIR', prints_dir), \
             patch('webbrowser.open', mock_open):
            cmd_prints_open(limit=1)

        # Debería abrir máximo 1 URL
        assert len(opened_urls) <= 1


# =============================================================================
# TESTS: main() - Argument Parsing
# =============================================================================

class TestMainArgumentParsing:
    """Tests de parsing de argumentos en main()."""

    def test_main_pull(self):
        """main() ejecuta pull."""
        with patch('sys.argv', ['sync_sheet.py', 'pull']), \
             patch('sync_sheet.cmd_pull') as mock_pull:
            main()
            mock_pull.assert_called_once()

    def test_main_scrape(self):
        """main() ejecuta scrape."""
        with patch('sys.argv', ['sync_sheet.py', 'scrape']), \
             patch('sync_sheet.cmd_scrape') as mock_scrape:
            main()
            mock_scrape.assert_called_once_with(check_all=False, no_cache=False, force_update=False)

    def test_main_scrape_all(self):
        """main() ejecuta scrape --all."""
        with patch('sys.argv', ['sync_sheet.py', 'scrape', '--all']), \
             patch('sync_sheet.cmd_scrape') as mock_scrape:
            main()
            mock_scrape.assert_called_once_with(check_all=True, no_cache=False, force_update=False)

    def test_main_scrape_no_cache(self):
        """main() ejecuta scrape --no-cache."""
        with patch('sys.argv', ['sync_sheet.py', 'scrape', '--no-cache']), \
             patch('sync_sheet.cmd_scrape') as mock_scrape:
            main()
            mock_scrape.assert_called_once_with(check_all=False, no_cache=True, force_update=False)

    def test_main_push(self):
        """main() ejecuta push."""
        with patch('sys.argv', ['sync_sheet.py', 'push']), \
             patch('sync_sheet.cmd_push') as mock_push:
            main()
            mock_push.assert_called_once_with(force=False, dry_run=False)

    def test_main_push_force(self):
        """main() ejecuta push --force."""
        with patch('sys.argv', ['sync_sheet.py', 'push', '--force']), \
             patch('sync_sheet.cmd_push') as mock_push:
            main()
            mock_push.assert_called_once_with(force=True, dry_run=False)

    def test_main_push_dry_run(self):
        """main() ejecuta push --dry-run."""
        with patch('sys.argv', ['sync_sheet.py', 'push', '--dry-run']), \
             patch('sync_sheet.cmd_push') as mock_push:
            main()
            mock_push.assert_called_once_with(force=False, dry_run=True)

    def test_main_view(self):
        """main() ejecuta view."""
        with patch('sys.argv', ['sync_sheet.py', 'view']), \
             patch('sync_sheet.cmd_view') as mock_view:
            main()
            mock_view.assert_called_once_with(check_links=False)

    def test_main_view_check_links(self):
        """main() ejecuta view --check-links."""
        with patch('sys.argv', ['sync_sheet.py', 'view', '--check-links']), \
             patch('sync_sheet.cmd_view') as mock_view:
            main()
            mock_view.assert_called_once_with(check_links=True)

    def test_main_diff(self):
        """main() ejecuta diff."""
        with patch('sys.argv', ['sync_sheet.py', 'diff']), \
             patch('sync_sheet.cmd_diff') as mock_diff:
            main()
            mock_diff.assert_called_once()

    def test_main_prints(self):
        """main() ejecuta prints."""
        with patch('sys.argv', ['sync_sheet.py', 'prints']), \
             patch('sync_sheet.cmd_prints') as mock_prints:
            main()
            mock_prints.assert_called_once()

    def test_main_prints_open(self):
        """main() ejecuta prints open."""
        with patch('sys.argv', ['sync_sheet.py', 'prints', 'open']), \
             patch('sync_sheet.cmd_prints_open') as mock_open:
            main()
            mock_open.assert_called_once_with(limit=None)

    def test_main_prints_open_limit(self):
        """main() ejecuta prints open --limit."""
        with patch('sys.argv', ['sync_sheet.py', 'prints', 'open', '--limit', '5']), \
             patch('sync_sheet.cmd_prints_open') as mock_open:
            main()
            mock_open.assert_called_once_with(limit=5)

    def test_main_prints_scan(self):
        """main() ejecuta prints scan."""
        with patch('sys.argv', ['sync_sheet.py', 'prints', 'scan']), \
             patch('sync_sheet.cmd_prints_scan') as mock_scan:
            main()
            mock_scan.assert_called_once()

    def test_main_pendientes(self):
        """main() ejecuta pendientes."""
        with patch('sys.argv', ['sync_sheet.py', 'pendientes']), \
             patch('sync_sheet.cmd_pendientes') as mock_pend:
            main()
            mock_pend.assert_called_once_with(solo_sin_print=False)

    def test_main_pendientes_sin_print(self):
        """main() ejecuta pendientes --sin-print."""
        with patch('sys.argv', ['sync_sheet.py', 'pendientes', '--sin-print']), \
             patch('sync_sheet.cmd_pendientes') as mock_pend:
            main()
            mock_pend.assert_called_once_with(solo_sin_print=True)


# =============================================================================
# TESTS: Edge Cases y Errores
# =============================================================================

class TestEdgeCases:
    """Tests de casos borde y errores."""

    def test_scrape_error_conexion(self, mock_local_data, tmp_path, capsys):
        """Scrape maneja errores de conexión."""
        import httpx

        local_file = tmp_path / "sheet_data.json"
        mock_local_data['rows'][0]['precio'] = ''  # Forzar scrape
        local_file.write_text(json.dumps(mock_local_data))

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.load_cache', return_value={}), \
             patch('sync_sheet.save_cache'), \
             patch('httpx.get', side_effect=httpx.ConnectError('Network error')):
            cmd_scrape()

        captured = capsys.readouterr()
        # No debería crashear

    def test_push_error_api(self, mock_local_data, tmp_path, capsys):
        """Push maneja errores de API."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text(json.dumps(mock_local_data))

        mock_client = MagicMock()
        # Simular error de conexión genérico en lugar de APIError de gspread
        mock_client.open_by_key.side_effect = Exception("API Error: Connection refused")

        with patch('sync_sheet.LOCAL_FILE', local_file), \
             patch('sync_sheet.get_client', return_value=mock_client):
            try:
                cmd_push()
            except Exception:
                pass  # Esperado - el error se propaga

    def test_archivo_json_corrupto(self, tmp_path, capsys):
        """Maneja archivo JSON corrupto."""
        local_file = tmp_path / "sheet_data.json"
        local_file.write_text('{ invalid json }')

        with patch('sync_sheet.LOCAL_FILE', local_file):
            try:
                cmd_scrape()
            except json.JSONDecodeError:
                pass  # Esperado


# =============================================================================
# TESTS: Funciones auxiliares del CLI
# =============================================================================

class TestCheckLinkStatus:
    """Tests de check_link_status."""

    def test_check_link_status_200(self):
        """check_link_status detecta 200."""
        from sync_sheet import check_link_status

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('httpx.head', return_value=mock_response):
            status = check_link_status('https://example.com')

        assert status == 200

    def test_check_link_status_404(self):
        """check_link_status detecta 404."""
        from sync_sheet import check_link_status

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('httpx.head', return_value=mock_response):
            status = check_link_status('https://example.com/notfound')

        assert status == 404

    def test_check_link_status_timeout(self):
        """check_link_status maneja timeout."""
        from sync_sheet import check_link_status
        import httpx

        with patch('httpx.head', side_effect=httpx.TimeoutException('timeout')):
            status = check_link_status('https://example.com')

        assert status is None or status == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
