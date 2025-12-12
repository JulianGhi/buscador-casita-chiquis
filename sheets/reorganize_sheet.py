#!/usr/bin/env python3
"""Reorganize sheet columns, add colors, and complete missing data"""

import gspread
from google.oauth2.service_account import Credentials
from gspread_formatting import (
    CellFormat, Color, TextFormat,
    format_cell_range, set_column_width
)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SHEET_ID = '16n92ghEe8Vr1tiLdqbccF3i97kiwhHin9OPWY-O50L4'

# New column order grouped logically
NEW_ORDER = [
    # Identificación
    'direccion', 'barrio', 'link',
    # Precio
    'precio', 'm2_cub', 'm2_tot', 'expensas',
    # Características
    'amb', 'm2_terr', 'terraza', 'apto_credito',
    # Estado inmueble
    'antiguedad', 'estado', 'luminosidad',
    # Gestión
    'status', 'activo', 'inmobiliaria', 'contacto',
    # Fechas
    'fecha_contacto', 'fecha_visita',
    # Evaluación
    'rating', 'notas'
]

# Column groups with colors (cream/pastel tones)
COLUMN_GROUPS = {
    'Identificación': {
        'cols': ['direccion', 'barrio', 'link'],
        'color': Color(1, 0.95, 0.85),  # Cream/beige
    },
    'Precio': {
        'cols': ['precio', 'm2_cub', 'm2_tot', 'expensas'],
        'color': Color(0.85, 0.95, 0.85),  # Light green
    },
    'Características': {
        'cols': ['amb', 'm2_terr', 'terraza', 'apto_credito'],
        'color': Color(0.85, 0.92, 1),  # Light blue
    },
    'Estado': {
        'cols': ['antiguedad', 'estado', 'luminosidad'],
        'color': Color(1, 0.92, 0.85),  # Light orange
    },
    'Gestión': {
        'cols': ['status', 'activo', 'inmobiliaria', 'contacto'],
        'color': Color(0.95, 0.85, 0.95),  # Light purple
    },
    'Fechas': {
        'cols': ['fecha_contacto', 'fecha_visita'],
        'color': Color(0.9, 0.9, 0.9),  # Light gray
    },
    'Evaluación': {
        'cols': ['rating', 'notas'],
        'color': Color(1, 0.95, 0.88),  # Light yellow
    },
}

# Known barrios for streets
BARRIO_LOOKUP = {
    'donato álvarez': 'Floresta',
    'ñanduti': 'Villa del Parque',
    'av la plata': 'Boedo',
}

def get_col_letter(idx):
    """Convert 0-indexed column to letter"""
    result = ""
    idx += 1
    while idx > 0:
        idx, remainder = divmod(idx - 1, 26)
        result = chr(65 + remainder) + result
    return result

def reorganize_sheet():
    """Reorganize columns and add formatting"""
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(SHEET_ID)
    ws = spreadsheet.sheet1

    # Get current data
    all_data = ws.get_all_records()
    print(f"Found {len(all_data)} rows")

    # Complete missing barrios
    print("\nCompleting barrios...")
    for row in all_data:
        if not row.get('barrio'):
            direccion = row.get('direccion', '').lower()
            for street, barrio in BARRIO_LOOKUP.items():
                if street in direccion:
                    row['barrio'] = barrio
                    print(f"  {row.get('direccion', '?')} -> {barrio}")
                    break

    # Reorder columns
    print("\nReordering columns...")
    rows_data = []
    for row in all_data:
        new_row = [row.get(col, '') for col in NEW_ORDER]
        rows_data.append(new_row)

    # Clear and update
    ws.clear()
    ws.update(values=[NEW_ORDER], range_name='A1')
    if rows_data:
        ws.update(values=rows_data, range_name='A2')

    # Format headers - dark gray background, white bold text
    num_cols = len(NEW_ORDER)
    last_col = get_col_letter(num_cols - 1)

    header_format = CellFormat(
        backgroundColor=Color(0.3, 0.3, 0.3),
        textFormat=TextFormat(bold=True, foregroundColor=Color(1, 1, 1)),
    )
    format_cell_range(ws, f'A1:{last_col}1', header_format)

    # Freeze header row
    ws.freeze(rows=1)

    # Apply colors to data columns
    print("\nApplying column colors...")
    num_rows = len(all_data) + 50  # Buffer for new rows

    for group_name, group_info in COLUMN_GROUPS.items():
        color = group_info['color']
        for col_name in group_info['cols']:
            if col_name in NEW_ORDER:
                col_idx = NEW_ORDER.index(col_name)
                col_letter = get_col_letter(col_idx)
                range_str = f'{col_letter}2:{col_letter}{num_rows}'

                fmt = CellFormat(backgroundColor=color)
                format_cell_range(ws, range_str, fmt)

        print(f"  {group_name}: {group_info['cols']}")

    # Set column widths
    print("\nAdjusting column widths...")
    widths = {
        'direccion': 180,
        'barrio': 120,
        'link': 80,
        'precio': 80,
        'm2_cub': 60,
        'm2_tot': 60,
        'expensas': 70,
        'amb': 40,
        'm2_terr': 60,
        'terraza': 60,
        'apto_credito': 80,
        'antiguedad': 70,
        'estado': 80,
        'luminosidad': 80,
        'status': 90,
        'activo': 50,
        'inmobiliaria': 100,
        'contacto': 100,
        'fecha_contacto': 100,
        'fecha_visita': 90,
        'rating': 50,
        'notas': 250,
    }

    for col_name, width in widths.items():
        if col_name in NEW_ORDER:
            col_idx = NEW_ORDER.index(col_name)
            set_column_width(ws, get_col_letter(col_idx), width)

    print(f"\n✓ Done!")
    print(f"URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}")

if __name__ == '__main__':
    reorganize_sheet()
