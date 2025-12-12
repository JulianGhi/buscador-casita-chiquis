#!/usr/bin/env python3
"""Clean data and add dropdown validation to Google Sheet"""

import gspread
from google.oauth2.service_account import Credentials
from gspread_formatting import DataValidationRule, BooleanCondition, set_data_validation_for_cell_range

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SHEET_ID = '16n92ghEe8Vr1tiLdqbccF3i97kiwhHin9OPWY-O50L4'

# Dropdown values for each field
DROPDOWNS = {
    'barrio': [
        'Caballito', 'Flores', 'Floresta', 'Liniers', 'Mataderos',
        'Monte Castro', 'Parque Avellaneda', 'Parque Chacabuco', 'Paternal',
        'Vélez Sarsfield', 'Villa Crespo', 'Villa del Parque', 'Villa Devoto',
        'Villa Luro', 'Boedo'
    ],
    'amb': ['1', '2', '3', '4', '5'],
    'apto_credito': ['si', 'no'],
    'terraza': ['si', 'no'],
    'status': ['Por ver', 'Contactado', 'Visitado', 'Interesado', 'Descartado'],
    'activo': ['si', 'no'],
    'estado': ['Estrenar', 'Excelente', 'Bueno', 'Regular', 'A reciclar'],
    'luminosidad': ['Excelente', 'Buena', 'Regular', 'Poca'],
    'rating': ['1', '2', '3', '4', '5']
}

# Column positions (1-indexed for gspread)
HEADERS = [
    'direccion', 'barrio', 'precio', 'm2_cub', 'm2_tot', 'm2_terr', 'amb',
    'apto_credito', 'terraza', 'expensas', 'inmobiliaria', 'status', 'notas',
    'link', 'activo', 'contacto', 'fecha_contacto', 'fecha_visita',
    'antiguedad', 'estado', 'luminosidad', 'rating'
]

def get_col_letter(idx):
    """Convert 0-indexed column to letter (A, B, ... Z, AA, AB...)"""
    result = ""
    idx += 1
    while idx > 0:
        idx, remainder = divmod(idx - 1, 26)
        result = chr(65 + remainder) + result
    return result

def clean_data():
    """Clean the sheet data and add dropdowns"""
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(SHEET_ID)
    ws = spreadsheet.sheet1

    # Get all data
    all_data = ws.get_all_records()
    print(f"Found {len(all_data)} rows")

    # Clean each row
    cleaned = []
    for i, row in enumerate(all_data):
        direccion = row.get('direccion', '')

        # Skip rows that are clearly not real addresses
        skip_keywords = ['Ituzaingó', 'provincia', 'PROVINCIA']
        if any(kw.lower() in str(row.get('notas', '')).lower() or kw.lower() in direccion.lower()
               for kw in ['ituzaingó', 'provincia']):
            if 'provincia' in str(row.get('notas', '')).lower() or 'ituzaingó' in direccion.lower():
                print(f"  Skipping (provincia): {direccion}")
                continue

        # Clean direccion - extract actual address from descriptions
        clean_dir = direccion

        # If direccion looks like a description, try to extract or mark for review
        description_indicators = ['PH ', 'Casa ', 'Depto ', '3 amb', '4 amb', ' amb ', 'luminoso', 'cochera', 'permuta', 'reciclado']
        is_description = any(ind.lower() in direccion.lower() for ind in description_indicators)

        if is_description and not any(c.isdigit() for c in direccion[:20]):
            # Likely a description, not an address - mark as needs review
            print(f"  Needs address: {direccion}")
            # Keep as is but will need manual fix

        # Normalize apto_credito, terraza, activo to lowercase si/no
        for field in ['apto_credito', 'terraza', 'activo']:
            val = str(row.get(field, '')).strip().lower()
            if val in ['sí', 'si', 'yes', '1', 'true']:
                row[field] = 'si'
            elif val in ['no', '0', 'false']:
                row[field] = 'no'
            elif val == '':
                row[field] = ''
            else:
                row[field] = val

        # Normalize status
        status = str(row.get('status', '')).strip()
        if status:
            status_map = {
                'por ver': 'Por ver',
                'visitado': 'Visitado',
                'interesado': 'Interesado',
                'descartado': 'Descartado',
                'contactado': 'Contactado'
            }
            row['status'] = status_map.get(status.lower(), status)

        # Normalize estado
        estado = str(row.get('estado', '')).strip()
        if estado:
            estado_map = {
                'estrenar': 'Estrenar',
                'excelente': 'Excelente',
                'bueno': 'Bueno',
                'regular': 'Regular',
                'a reciclar': 'A reciclar'
            }
            row['estado'] = estado_map.get(estado.lower(), estado)

        # Normalize luminosidad
        luz = str(row.get('luminosidad', '')).strip()
        if luz:
            luz_map = {
                'excelente': 'Excelente',
                'buena': 'Buena',
                'regular': 'Regular',
                'poca': 'Poca'
            }
            row['luminosidad'] = luz_map.get(luz.lower(), luz)

        # Normalize expensas - convert "Bajas" to empty, keep numbers
        expensas = str(row.get('expensas', '')).strip()
        if expensas.lower() in ['bajas', 'sin exp', 'sin', '-']:
            row['expensas'] = '0'
        elif not expensas.replace('.', '').replace(',', '').isdigit():
            row['expensas'] = ''

        cleaned.append(row)

    print(f"\nCleaned to {len(cleaned)} rows")

    # Prepare rows for update
    rows_data = []
    for row in cleaned:
        row_values = [row.get(h, '') for h in HEADERS]
        rows_data.append(row_values)

    # Clear and update
    ws.clear()
    ws.update(values=[HEADERS], range_name='A1')
    if rows_data:
        ws.update(values=rows_data, range_name='A2')

    # Format headers
    ws.format('A1:V1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })
    ws.freeze(rows=1)

    print("\nData updated!")

    # Add dropdown validation
    print("\nAdding dropdown validation...")
    num_rows = len(cleaned) + 100  # Add buffer for future rows

    for col_name, values in DROPDOWNS.items():
        if col_name in HEADERS:
            col_idx = HEADERS.index(col_name)
            col_letter = get_col_letter(col_idx)
            range_str = f'{col_letter}2:{col_letter}{num_rows}'

            # Create validation rule
            rule = DataValidationRule(
                BooleanCondition('ONE_OF_LIST', values),
                showCustomUi=True
            )
            set_data_validation_for_cell_range(ws, range_str, rule)
            print(f"  {col_name} ({col_letter}): {values}")

    print("\n✓ Done! Sheet cleaned and dropdowns added.")
    print(f"URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}")

if __name__ == '__main__':
    clean_data()
