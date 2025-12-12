#!/usr/bin/env python3
"""Google Sheets manager for Casita Chiquis"""

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

HEADERS = [
    'id', 'direccion', 'barrio', 'precio', 'm2_cub', 'm2_tot', 'm2_terr',
    'amb', 'apto_credito', 'terraza', 'expensas', 'inmobiliaria',
    'status', 'notas', 'link', 'online'
]

SAMPLE_DATA = [
    [1, 'Av Juan B Alberdi 4600', 'Parque Avellaneda', 105000, 70, 140, 70, 3, 'si', 'si', '', 'GOLDEN HAUS', 'Por ver', '40 años sin expensas', 'https://www.argenprop.com/ficha--17094976', 'online'],
    [2, 'Segurola 1700', 'Monte Castro', 89000, 70, '', '', 3, 'si', 'si', '', '', 'Por ver', '95 años apto crédito', '', '?meli'],
    [3, 'Gualeguaychú 985', 'Floresta', 95000, 79, '', '', 4, 'si', 'si', 15000, '', 'Por ver', 'Terraza con parrilla', '', '?meli'],
]


def get_client():
    """Get authenticated gspread client"""
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    return gspread.authorize(creds)


def create_spreadsheet(title="Casita Chiquis - Propiedades"):
    """Create a new spreadsheet with headers and sample data"""
    client = get_client()

    # Create spreadsheet
    spreadsheet = client.create(title)
    worksheet = spreadsheet.sheet1
    worksheet.update_title("Propiedades")

    # Add headers
    worksheet.update('A1', [HEADERS])

    # Format headers (bold)
    worksheet.format('A1:P1', {
        'textFormat': {'bold': True},
        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
    })

    # Add sample data
    worksheet.update('A2', SAMPLE_DATA)

    # Freeze header row
    worksheet.freeze(rows=1)

    print(f"Spreadsheet creado!")
    print(f"URL: {spreadsheet.url}")
    print(f"ID: {spreadsheet.id}")
    print(f"\nPara que funcione el dashboard, publicá el sheet como CSV:")
    print(f"  Archivo → Compartir → Publicar en la web → CSV")

    return spreadsheet


def share_with_user(spreadsheet_id, email):
    """Share spreadsheet with a user"""
    client = get_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    spreadsheet.share(email, perm_type='user', role='writer')
    print(f"Compartido con {email}")


def get_csv_url(spreadsheet_id):
    """Get the public CSV URL for a spreadsheet"""
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'create':
        spreadsheet = create_spreadsheet()

        # Ask if want to share
        print("\n¿Con qué email querés compartir el sheet?")
        print("(dejá vacío para saltar)")
        email = input("> ").strip()
        if email:
            share_with_user(spreadsheet.id, email)
    else:
        print("Uso:")
        print("  python sheets.py create    - Crear nuevo spreadsheet")
