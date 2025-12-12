#!/usr/bin/env python3
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SHEET_ID = '16n92ghEe8Vr1tiLdqbccF3i97kiwhHin9OPWY-O50L4'

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

creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
client = gspread.authorize(creds)

spreadsheet = client.open_by_key(SHEET_ID)
worksheet = spreadsheet.sheet1

# Add headers
worksheet.update('A1', [HEADERS])

# Format headers
worksheet.format('A1:P1', {
    'textFormat': {'bold': True},
    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
})

# Add sample data
worksheet.update('A2', SAMPLE_DATA)

# Freeze header row
worksheet.freeze(rows=1)

print("Sheet configurado!")
print(f"URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}")
print(f"\nCSV público: https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv")
