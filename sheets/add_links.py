#!/usr/bin/env python3
"""
Agrega links nuevos a Google Sheets y los scrapea.

Uso:
    python add_links.py URL1 URL2 URL3 ...
    python add_links.py "URL1 - nota para este link" "URL2"

    # O desde archivo (un link por línea):
    python add_links.py --file links.txt
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent))

import gspread
from google.oauth2.service_account import Credentials
from sync_sheet import scrape_mercadolibre, scrape_argenprop, SCRAPEABLE_COLS

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = '16n92ghEe8Vr1tiLdqbccF3i97kiwhHin9OPWY-O50L4'


def parse_link_with_note(text):
    """Parse 'URL - nota' or just 'URL'"""
    text = text.strip()
    if ' - ' in text:
        parts = text.split(' - ', 1)
        url = parts[0].strip()
        nota = parts[1].strip()
    else:
        url = text
        nota = ''

    # Clean URL (remove tracking params)
    url = url.split('#')[0].split('?')[0]
    return url, nota


def scrape_url(url):
    """Scrape data from URL based on domain"""
    if 'mercadolibre' in url:
        return scrape_mercadolibre(url)
    elif 'argenprop' in url:
        return scrape_argenprop(url)
    else:
        return {'_error': 'Dominio no soportado'}


def add_links(links_with_notes):
    """Add links to sheet with scraped data"""
    # Auth
    creds = Credentials.from_service_account_file(
        Path(__file__).parent.parent / 'credentials.json',
        scopes=SCOPES
    )
    gc = gspread.authorize(creds)

    # Open sheet
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.sheet1

    # Get headers - use range A1:AD1 to get exactly 30 columns
    headers = ws.row_values(1)[:30]  # Limit to first 30 headers

    # Get existing data (only first 30 columns)
    all_data = ws.get('A:AD')
    link_idx = headers.index('link') if 'link' in headers else 0
    existing_links = [row[link_idx] if len(row) > link_idx else ''
                      for row in all_data[1:] if row]

    col_idx = {h: i for i, h in enumerate(headers)}
    today = datetime.now().strftime('%Y-%m-%d')

    # Find next empty row (after last row with data)
    next_row = len([r for r in all_data if any(r)]) + 1

    added = 0
    for url, nota in links_with_notes:
        # Check if already exists
        if any(url in str(e) for e in existing_links):
            print(f"⏭️  Ya existe: {url}")
            continue

        print(f"\n🔍 Scrapeando: {url}")

        # Scrape data
        data = scrape_url(url)
        if '_error' in data:
            print(f"   ⚠️  Error: {data['_error']}")
            # Si hay error, marcamos como activo='?' para revisar
            data['activo'] = '?'
        else:
            print(f"   📍 {data.get('direccion', '?')} - {data.get('barrio', '?')} - ${data.get('precio', '?')}")
            # Si scrapeó bien, el link está activo
            data['activo'] = 'si'

        # Prepare row (exactly 30 columns)
        new_row = [''] * 30
        new_row[col_idx.get('link', 0)] = url

        # Fill scraped data
        for key, value in data.items():
            if key.startswith('_'):
                continue
            if key in col_idx:
                new_row[col_idx[key]] = value

        # Add nota
        if nota and 'notas' in col_idx:
            new_row[col_idx['notas']] = nota

        # Add fecha_agregado
        if 'fecha_agregado' in col_idx:
            new_row[col_idx['fecha_agregado']] = today

        # Write to specific row using update (more reliable than append_row)
        # Range A{next_row}:AD{next_row} = columns 1-30
        cell_range = f'A{next_row}:AD{next_row}'
        ws.update(values=[new_row], range_name=cell_range, value_input_option='USER_ENTERED')

        existing_links.append(url)
        next_row += 1
        added += 1
        print(f"   ✅ Agregado!")

    print(f"\n🎉 {added} links agregados")
    return added


def main():
    parser = argparse.ArgumentParser(description='Agregar links a Google Sheets')
    parser.add_argument('links', nargs='*', help='Links a agregar (puede incluir "URL - nota")')
    parser.add_argument('--file', '-f', help='Archivo con links (uno por línea)')

    args = parser.parse_args()

    links = []

    # From arguments
    for link in args.links:
        links.append(parse_link_with_note(link))

    # From file
    if args.file:
        with open(args.file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    links.append(parse_link_with_note(line))

    if not links:
        print("❌ No hay links para agregar")
        print("Uso: python add_links.py URL1 URL2 ...")
        print("     python add_links.py --file links.txt")
        return

    print(f"📋 {len(links)} links a procesar")
    add_links(links)


if __name__ == '__main__':
    main()
