#!/usr/bin/env python3
"""Fix direcciones that are actually descriptions"""

import gspread
from google.oauth2.service_account import Credentials
import re

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SHEET_ID = '16n92ghEe8Vr1tiLdqbccF3i97kiwhHin9OPWY-O50L4'

# Patterns that indicate a real address (has street number)
ADDRESS_PATTERN = re.compile(r'\d{2,5}')  # Has a number with 2-5 digits

# Keywords that indicate it's a description, not an address
DESCRIPTION_KEYWORDS = ['amb', 'ph ', 'depto', 'casa', 'cochera', 'patio',
                        'terraza', 'luminoso', 'reciclado', 'permuta', 'crédito',
                        'm²', 'm2']

def is_description(text):
    """Check if text looks like a description rather than an address"""
    if not text:
        return False

    text_lower = text.lower()

    # If it has description keywords and doesn't start with a street name pattern
    has_keywords = any(kw in text_lower for kw in DESCRIPTION_KEYWORDS)

    # Real addresses usually have a number early on
    has_number = bool(ADDRESS_PATTERN.search(text))

    # Starts with "PH", "3 amb", "Depto", etc = description
    starts_with_desc = any(text_lower.startswith(kw) for kw in ['ph ', 'ph', '3 ', '4 ', '5 ', 'depto', 'casa'])

    if starts_with_desc:
        return True

    if has_keywords and not has_number:
        return True

    return False

def fix_direcciones():
    """Fix direccion field - move descriptions to notas"""
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(SHEET_ID)
    ws = spreadsheet.sheet1

    # Get all data
    all_data = ws.get_all_records()
    print(f"Found {len(all_data)} rows\n")

    changes = []

    for i, row in enumerate(all_data):
        direccion = row.get('direccion', '').strip()
        notas = row.get('notas', '').strip()

        if is_description(direccion):
            # Check if this description is already in notas
            if direccion.lower() not in notas.lower():
                # Add to notas
                if notas:
                    new_notas = f"{direccion}. {notas}"
                else:
                    new_notas = direccion
            else:
                new_notas = notas

            print(f"Row {i+2}: '{direccion}' -> ''")
            print(f"         Notas: '{notas}' -> '{new_notas}'\n")

            row['direccion'] = ''
            row['notas'] = new_notas
            changes.append(i+2)

    if not changes:
        print("No changes needed!")
        return

    print(f"\n{len(changes)} rows to fix. Updating sheet...")

    # Get headers
    headers = ws.row_values(1)

    # Prepare all rows
    rows_data = []
    for row in all_data:
        row_values = [row.get(h, '') for h in headers]
        rows_data.append(row_values)

    # Update sheet
    ws.update(values=rows_data, range_name='A2')

    print(f"✓ Done! Fixed {len(changes)} rows.")
    print(f"URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}")

if __name__ == '__main__':
    fix_direcciones()
