"""
API de Google Sheets.

Incluye:
- Conexión y autenticación
- Funciones para obtener worksheet
- Conversión de datos
"""

import os

import gspread
from google.oauth2.service_account import Credentials

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Leer de variable de entorno
SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
WORKSHEET_NAME = 'Propiedades'


# =============================================================================
# CONEXIÓN
# =============================================================================

def get_client():
    """Get authenticated gspread client."""
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    return gspread.authorize(creds)


def get_worksheet():
    """Obtiene el worksheet del Google Sheet.

    Returns:
        gspread.Worksheet: El worksheet configurado
    """
    client = get_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    try:
        return spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        return spreadsheet.sheet1


# =============================================================================
# CONVERSIÓN DE DATOS
# =============================================================================

def sheet_to_dict(worksheet):
    """Convierte datos de Google Sheet a dict indexado por fila.

    Args:
        worksheet: gspread.Worksheet

    Returns:
        (headers, rows_dict): Headers y dict {row_num: {col: value}}
    """
    all_values = worksheet.get_all_values()
    if not all_values:
        return [], {}

    headers = [h.lower().strip() for h in all_values[0]]
    rows = {}
    for i, row_values in enumerate(all_values[1:], start=2):
        rows[i] = dict(zip(headers, row_values))
    return headers, rows


def sheet_to_list(worksheet):
    """Convierte datos de Google Sheet a lista de dicts.

    Args:
        worksheet: gspread.Worksheet

    Returns:
        (headers, rows_list): Headers y lista de dicts con _row
    """
    all_values = worksheet.get_all_values()
    if not all_values:
        return [], []

    headers = [h.lower().strip() for h in all_values[0]]
    rows = []
    for i, row_values in enumerate(all_values[1:], start=2):
        row = {'_row': i}
        for h, v in zip(headers, row_values):
            row[h] = v
        rows.append(row)
    return headers, rows


# =============================================================================
# FUNCIONES DE PUSH
# =============================================================================

def get_cells_to_update(rows, current_values, headers, update_cols):
    """
    Calcula celdas que necesitan actualizacion (merge mode).

    Args:
        rows: Lista de filas locales con _row
        current_values: Valores actuales del sheet (lista de listas)
        headers: Lista de headers del sheet
        update_cols: Columnas que se pueden actualizar

    Returns:
        Lista de gspread.Cell para actualizar
    """
    cells = []
    for row in rows:
        row_num = row.get('_row', 0)
        if row_num < 2:
            continue

        for col_name in update_cols:
            if col_name not in headers:
                continue

            col_idx = headers.index(col_name) + 1
            new_val = str(row.get(col_name, '') or '').strip()

            # Obtener valor actual
            if row_num <= len(current_values) and col_idx <= len(current_values[row_num - 1]):
                current_val = current_values[row_num - 1][col_idx - 1].strip()
            else:
                current_val = ''

            # Actualizar si hay valor nuevo y es diferente
            if new_val and (not current_val or current_val != new_val):
                cells.append(gspread.Cell(row_num, col_idx, new_val))

    return cells


def build_sheet_data(headers, rows):
    """
    Construye datos para sobrescribir el sheet completo (force mode).

    Args:
        headers: Lista de headers
        rows: Lista de filas (dicts)

    Returns:
        Lista de listas para worksheet.update()
    """
    all_data = [headers]
    for row in rows:
        row_values = [row.get(h, '') for h in headers]
        all_data.append(row_values)
    return all_data


def format_header_row(worksheet):
    """Formatea la fila de headers (bold, background gris)."""
    worksheet.format('A1:Z1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })
    worksheet.freeze(rows=1)
