#!/usr/bin/env python3
import gspread
from google.oauth2.service_account import Credentials
import openpyxl

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SHEET_ID = '16n92ghEe8Vr1tiLdqbccF3i97kiwhHin9OPWY-O50L4'

NEW_HEADERS = [
    'direccion', 'barrio', 'precio', 'm2_cub', 'm2_tot', 'm2_terr', 'amb',
    'apto_credito', 'terraza', 'expensas', 'inmobiliaria', 'status', 'notas',
    'link', 'activo', 'contacto', 'fecha_contacto', 'fecha_visita',
    'antiguedad', 'estado', 'luminosidad', 'rating'
]

# Map Excel columns to new Sheet columns
# Excel: ID, Status, Online?, Data?, Dirección, Barrio, Precio, m²c, Amb, Apto?, Terraza, ...
# Excel indices (0-based): 4=Dirección, 5=Barrio, 6=Precio, 7=m²c, 8=Amb, 9=Apto?, 10=Terraza,
# 17=m²t, 18=Terr(m²terr), 19=Exp, 20=Estado, 21=Luz, 30=Contacto, 31=Fecha, 35=Notas, 36=Link

def load_excel_data():
    """Load data from Excel file"""
    wb = openpyxl.load_workbook('docs/seguimiento_propiedades_v3.xlsx', data_only=True)
    ws = wb['Propiedades']

    data = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        # Skip empty rows
        if not row[4]:  # Dirección is column 5 (index 4)
            continue

        # Map to new structure
        record = {
            'direccion': row[4],
            'barrio': row[5],
            'precio': row[6] if row[6] else '',
            'm2_cub': row[7] if row[7] else '',
            'm2_tot': row[17] if row[17] else '',
            'm2_terr': row[18] if row[18] else '',
            'amb': row[8] if row[8] else '',
            'apto_credito': 'si' if row[9] == 'Sí' else ('no' if row[9] == 'No' else ''),
            'terraza': 'si' if row[10] and 'Propia' in str(row[10]) else ('no' if row[10] else ''),
            'expensas': str(row[19]).replace('Sin exp', '0') if row[19] else '',
            'inmobiliaria': row[30] if row[30] else '',
            'status': row[1] if row[1] else 'Por ver',
            'notas': row[35] if row[35] else '',
            'link': row[36] if row[36] else '',
            'activo': 'si' if row[2] and '✓' in str(row[2]) else 'no',
            'contacto': '',
            'fecha_contacto': str(row[31]) if row[31] else '',
            'fecha_visita': '',
            'antiguedad': '',
            'estado': row[20] if row[20] else '',
            'luminosidad': row[21] if row[21] else '',
            'rating': '',
        }
        data.append(record)

    return data

def update_sheet():
    """Update Google Sheet with new headers and data"""
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.sheet1

    # Clear existing data
    worksheet.clear()

    # Add new headers
    worksheet.update(values=[NEW_HEADERS], range_name='A1')

    # Format headers
    worksheet.format('A1:V1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })

    # Load Excel data
    print("Cargando datos del Excel...")
    data = load_excel_data()
    print(f"Encontradas {len(data)} propiedades")

    # Convert to rows
    rows = []
    for record in data:
        row = [record.get(h, '') for h in NEW_HEADERS]
        rows.append(row)

    # Add data
    if rows:
        worksheet.update(values=rows, range_name='A2')

    # Freeze header row
    worksheet.freeze(rows=1)

    print(f"Sheet actualizado con {len(rows)} propiedades")
    print(f"Headers: {', '.join(NEW_HEADERS)}")

if __name__ == '__main__':
    update_sheet()
