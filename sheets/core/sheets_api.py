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
