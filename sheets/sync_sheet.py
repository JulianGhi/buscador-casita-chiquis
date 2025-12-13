#!/usr/bin/env python3
"""
Sincroniza Google Sheets con datos scrapeados de los links.

Flujo en 3 pasos:
    1. python sync_sheet.py pull      # Descarga a data/sheet_data.json
    2. python sync_sheet.py scrape    # Scrapea links y actualiza el JSON
    3. python sync_sheet.py push      # Sube cambios a Google Sheets

Opciones de push:
    --force     Sobrescribe todo el sheet
    --merge     Solo actualiza celdas vacías (default)
    --dry-run   Muestra cambios sin aplicar
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

import httpx
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Leer de variable de entorno (más seguro que hardcodear)
SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
if not SHEET_ID:
    raise ValueError("GOOGLE_SHEET_ID environment variable is required. Set it in .env or export it.")
WORKSHEET_NAME = 'Propiedades'
LOCAL_FILE = Path('data/sheet_data.json')
CACHE_FILE = Path('data/scrape_cache.json')

# Columnas que el scraper puede llenar
SCRAPEABLE_COLS = ['precio', 'm2_cub', 'm2_tot', 'm2_terr', 'amb', 'barrio', 'direccion',
                   'expensas', 'terraza', 'antiguedad', 'apto_credito', 'tipo', 'activo',
                   'cocheras', 'disposicion', 'piso', 'ascensor', 'balcon', 'luminosidad',
                   'fecha_publicado', 'banos', 'inmobiliaria', 'dormitorios']


def get_client():
    """Get authenticated gspread client"""
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    return gspread.authorize(creds)


# =============================================================================
# PULL - Descarga de Google Sheets a archivo local
# =============================================================================

def cmd_pull():
    """Descarga datos de Google Sheets a archivo local JSON"""
    print("📥 Descargando datos de Google Sheets...")

    client = get_client()
    spreadsheet = client.open_by_key(SHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.sheet1

    all_values = worksheet.get_all_values()

    if not all_values:
        print("❌ Sheet vacío")
        return

    headers = [h.lower().strip() for h in all_values[0]]
    rows = []

    for i, row_values in enumerate(all_values[1:], start=2):
        row = {'_row': i}  # Guardar número de fila original
        for h, v in zip(headers, row_values):
            row[h] = v
        rows.append(row)

    # Guardar a archivo
    LOCAL_FILE.parent.mkdir(exist_ok=True)

    data = {
        'headers': headers,
        'rows': rows,
        'source': f'Google Sheet {SHEET_ID}',
        'pulled_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(LOCAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(rows)} filas guardadas en {LOCAL_FILE}")

    # Stats
    with_price = sum(1 for r in rows if r.get('precio', '').strip())
    with_m2 = sum(1 for r in rows if r.get('m2_cub', '').strip())
    with_link = sum(1 for r in rows if r.get('link', '').strip())
    print(f"\n📊 Estadísticas:")
    print(f"   Con precio: {with_price}/{len(rows)}")
    print(f"   Con m²: {with_m2}/{len(rows)}")
    print(f"   Con link: {with_link}/{len(rows)}")


# =============================================================================
# SCRAPE - Scrapea links y actualiza archivo local
# =============================================================================

def scrape_argenprop(url):
    """Scrapea Argenprop"""
    try:
        resp = httpx.get(url, follow_redirects=True,
                        headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if resp.status_code != 200:
            return {'_error': f'Status {resp.status_code}'}

        soup = BeautifulSoup(resp.text, 'lxml')
        data = {}

        # Precio
        precio = soup.select_one('.titlebar__price, .property-price')
        if precio:
            txt = precio.text.strip()
            match = re.search(r'[\d.]+', txt.replace('.', ''))
            if match:
                data['precio'] = match.group()

        # Dirección
        ubicacion = soup.select_one('.titlebar__address, .property-main h1')
        if ubicacion:
            data['direccion'] = ubicacion.text.strip()

        # Descripción principal (tipo, m2, dormitorios, antigüedad)
        desc = soup.select_one('.property-description, .property-main-features')
        if desc:
            desc_text = desc.text.lower()
            # Tipo
            if 'ph' in desc_text.split():
                data['tipo'] = 'ph'
            elif 'departamento' in desc_text or 'depto' in desc_text:
                data['tipo'] = 'depto'
            elif 'casa' in desc_text:
                data['tipo'] = 'casa'
            elif 'local' in desc_text:
                data['tipo'] = 'local'
            # m2 cubiertos
            m2_match = re.search(r'(\d+)\s*m[²2]\s*cub', desc_text)
            if m2_match:
                data['m2_cub'] = m2_match.group(1)
            # Dormitorios -> ambientes aproximado
            dorm_match = re.search(r'(\d+)\s*dormitorio', desc_text)
            if dorm_match:
                data['amb'] = str(int(dorm_match.group(1)) + 1)  # +1 por living
            # Antigüedad
            ant_match = re.search(r'(\d+)\s*años', desc_text)
            if ant_match:
                data['antiguedad'] = ant_match.group(1)

        # Features detallados
        for li in soup.select('.property-features li, .property-features-item'):
            txt = li.text.strip().lower()
            if 'm² cub' in txt or 'm2 cub' in txt or 'sup. cubierta' in txt:
                match = re.search(r'(\d+)', txt)
                if match:
                    data['m2_cub'] = match.group(1)
            elif 'm² tot' in txt or 'm2 tot' in txt or 'sup. total' in txt:
                match = re.search(r'(\d+)', txt)
                if match:
                    data['m2_tot'] = match.group(1)
            elif 'descubierta' in txt or 'm² desc' in txt or 'terraza' in txt and 'm²' in txt:
                match = re.search(r'(\d+)', txt)
                if match:
                    data['m2_terr'] = match.group(1)
            elif 'ambiente' in txt and 'cant' in txt:
                match = re.search(r'(\d+)', txt)
                if match:
                    data['amb'] = match.group(1)
            elif 'antigüedad' in txt or 'antiguedad' in txt:
                match = re.search(r'(\d+)', txt)
                if match:
                    data['antiguedad'] = match.group(1)
            elif 'terraza' in txt:
                # Verificar si dice "no" o solo es el label
                if 'no' in txt:
                    data['terraza'] = 'no'
                elif 'si' in txt or 'sí' in txt or txt == 'terraza':
                    data['terraza'] = 'si'
            elif 'balcón' in txt or 'balcon' in txt:
                if 'no' in txt:
                    data['balcon'] = 'no'
                elif 'si' in txt or 'sí' in txt or txt == 'balcón' or txt == 'balcon':
                    data['balcon'] = 'si'
            elif 'cochera' in txt:
                match = re.search(r'(\d+)', txt)
                data['cocheras'] = match.group(1) if match else '1'
            elif 'baño' in txt:
                match = re.search(r'(\d+)', txt)
                if match:
                    data['banos'] = match.group(1)
            elif 'expensas' in txt:
                match = re.search(r'(\d+)', txt.replace('.', ''))
                if match:
                    data['expensas'] = match.group(1)

        # Inmobiliaria
        inmob = soup.select_one('.property-contact__title, .property-sidebar h3, [class*="contact"] h3')
        if inmob:
            data['inmobiliaria'] = inmob.text.strip()

        # Barrio (del breadcrumb o container)
        location = soup.select_one('.property-container')
        if location:
            txt = location.text
            # Buscar barrio en texto como "Capital Federal, Parque Avellaneda"
            barrios_conocidos = ['Floresta', 'Flores', 'Caballito', 'Parque Chacabuco', 'Parque Avellaneda',
                                 'Villa Luro', 'Liniers', 'Mataderos', 'Villa Crespo', 'Paternal',
                                 'Villa del Parque', 'Villa Devoto', 'Monte Castro', 'Velez Sarsfield',
                                 'Vélez Sarsfield', 'Boedo', 'Almagro', 'Palermo', 'Belgrano']
            for barrio in barrios_conocidos:
                if barrio.lower() in txt.lower():
                    data['barrio'] = barrio
                    break

        return data
    except Exception as e:
        return {'_error': str(e)}


def scrape_mercadolibre(url):
    """Scrapea MercadoLibre"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
        }
        resp = httpx.get(url, follow_redirects=True, headers=headers, timeout=15)
        if resp.status_code != 200:
            return {'_error': f'Status {resp.status_code}'}

        # Detectar si redirigió a página de búsqueda (publicación no disponible)
        final_url = str(resp.url)
        if 'redirectedFromVip' in final_url or ('MLA-' in url and 'MLA-' not in final_url):
            return {'_error': 'Publicación no disponible (redirect)', '_offline': True}

        soup = BeautifulSoup(resp.text, 'lxml')

        # Detectar "Publicación finalizada" (ML muestra página completa pero con warning)
        # Buscar en el mensaje de warning visible o en el JSON embebido
        warning_text = soup.select_one('.andes-message__text--orange')
        if warning_text and 'finalizada' in warning_text.text.lower():
            return {'_error': 'Publicación finalizada', '_offline': True}

        # También buscar en el HTML raw por si el selector no funciona
        if '"text":"Publicación finalizada"' in resp.text:
            return {'_error': 'Publicación finalizada', '_offline': True}

        # Verificar si tiene precio - si no tiene, probablemente no está disponible
        precio = soup.select_one('.andes-money-amount__fraction')
        if not precio:
            # Buscar mensajes específicos de no disponible (no en toda la página)
            warning = soup.select_one('.ui-pdp-message-warning, .ui-vip-error')
            if warning:
                return {'_error': 'Publicación no disponible', '_offline': True}
            # Si no hay precio ni warning, puede ser un problema de parseo
            return {'_error': 'No se pudo extraer precio'}

        data = {}

        # Precio
        precio = soup.select_one('.andes-money-amount__fraction')
        if precio:
            data['precio'] = precio.text.strip().replace('.', '')

        # Ubicación completa (puede tener dirección)
        location = soup.select_one('.ui-vip-location')
        if location:
            loc_text = location.text.strip()
            # Limpiar prefijos comunes
            for prefix in ['Ubicación', 'Ver mapa', 'e información de la zona']:
                loc_text = loc_text.replace(prefix, '')
            loc_text = loc_text.strip()
            # Formato: "Calle 123, Barrio, Ciudad, Provincia"
            parts = [p.strip() for p in loc_text.split(',') if p.strip()]
            if len(parts) >= 1 and any(c.isdigit() for c in parts[0]):
                # Si el primer elemento tiene números, es una dirección
                direccion_raw = parts[0]

                # Limpiar direcciones mal formadas (ej: "4 Amb Almagro - Mario Bravo 200")
                # Si tiene " - ", probablemente la dirección real está después
                if ' - ' in direccion_raw:
                    partes = direccion_raw.split(' - ')
                    # Buscar la parte que parece dirección (tiene número de calle)
                    for p in partes:
                        # Patrón: palabra(s) + número (ej: "Mario Bravo 200", "Av. Rivadavia 6100")
                        if re.search(r'[A-Za-záéíóúÁÉÍÓÚñÑ\.\s]+\d+', p.strip()):
                            direccion_raw = p.strip()
                            break

                # Remover prefijos como "4 Amb", "3 Ambientes", etc.
                direccion_raw = re.sub(r'^\d+\s*(Amb|Ambientes?)\s*', '', direccion_raw, flags=re.IGNORECASE).strip()

                # Remover barrios que quedaron pegados al inicio
                barrios_limpiar = ['Floresta', 'Flores', 'Caballito', 'Almagro', 'Villa Crespo', 'Paternal']
                for b in barrios_limpiar:
                    if direccion_raw.lower().startswith(b.lower()):
                        direccion_raw = direccion_raw[len(b):].strip(' -')

                data['direccion'] = direccion_raw
            if len(parts) >= 2:
                # Buscar barrio (no Capital Federal/Buenos Aires)
                for part in parts[1:]:
                    if part not in ['Capital Federal', 'Buenos Aires', 'GBA Norte', 'GBA Sur', 'GBA Oeste']:
                        data['barrio'] = part
                        break

        # Barrio del link alternativo
        if 'barrio' not in data:
            ubicacion = soup.select_one('.ui-vip-location a')
            if ubicacion:
                data['barrio'] = ubicacion.text.strip()

        # Características de la tabla
        for row in soup.select('tr.andes-table__row'):
            header = row.select_one('th')
            value = row.select_one('td')
            if header and value:
                h = header.text.strip().lower()
                v = value.text.strip()
                if 'superficie cubierta' in h:
                    match = re.search(r'(\d+)', v)
                    if match:
                        data['m2_cub'] = match.group(1)
                elif 'superficie total' in h:
                    match = re.search(r'(\d+)', v)
                    if match:
                        data['m2_tot'] = match.group(1)
                elif 'superficie descubierta' in h or 'sup. descubierta' in h:
                    match = re.search(r'(\d+)', v)
                    if match:
                        data['m2_terr'] = match.group(1)
                elif 'ambientes' in h:
                    match = re.search(r'(\d+)', v)
                    if match:
                        data['amb'] = match.group(1)
                elif 'dormitorio' in h:
                    match = re.search(r'(\d+)', v)
                    if match:
                        data['dormitorios'] = match.group(1)
                elif 'baño' in h:
                    match = re.search(r'(\d+)', v)
                    if match:
                        data['banos'] = match.group(1)
                elif 'antigüedad' in h or 'antiguedad' in h:
                    match = re.search(r'(\d+)', v)
                    if match:
                        data['antiguedad'] = match.group(1)
                elif 'expensas' in h:
                    match = re.search(r'(\d+)', v)
                    if match:
                        data['expensas'] = match.group(1)
                elif 'apto cr' in h or 'apto_cr' in h:
                    # "Apto crédito: Sí/No"
                    data['apto_credito'] = 'si' if 'sí' in v.lower() or 'si' in v.lower() else 'no'
                elif 'tipo de' in h:
                    # "Tipo de departamento", "Tipo de casa", etc.
                    data['tipo'] = v.lower()
                elif 'cochera' in h:
                    match = re.search(r'(\d+)', v)
                    if match:
                        data['cocheras'] = match.group(1)
                elif 'disposición' in h or 'disposicion' in h:
                    data['disposicion'] = v.lower()
                elif 'número de piso' in h or 'piso de la unidad' in h:
                    match = re.search(r'(\d+)', v)
                    if match:
                        data['piso'] = match.group(1)
                elif 'ascensor' in h:
                    data['ascensor'] = 'si' if 'sí' in v.lower() or 'si' in v.lower() else 'no'
                elif h == 'balcón' or h == 'balcon':
                    data['balcon'] = 'si' if 'sí' in v.lower() or 'si' in v.lower() else 'no'
                elif h == 'terraza':
                    data['terraza'] = 'si' if 'sí' in v.lower() or 'si' in v.lower() else 'no'

        # Info del título y URL
        title = soup.select_one('h1.ui-pdp-title')
        title_text = title.text if title else ''
        title_lower = title_text.lower()
        url_lower = url.lower()
        # Combinar título y URL para buscar tipo
        search_text = title_lower + ' ' + url_lower

        # Barrios conocidos de CABA
        barrios_conocidos = [
            'Floresta', 'Flores', 'Caballito', 'Almagro', 'Villa Crespo',
            'Paternal', 'Monte Castro', 'Parque Chacabuco', 'Parque Avellaneda',
            'Villa del Parque', 'Villa Devoto', 'Villa Santa Rita', 'Vélez Sársfield',
            'Villa Luro', 'Liniers', 'Mataderos', 'Villa Real', 'Versalles',
            'Villa Pueyrredón', 'Agronomía', 'Villa Ortúzar', 'Chacarita',
            'Colegiales', 'Belgrano', 'Núñez', 'Saavedra', 'Villa Urquiza',
            'Coghlan', 'Palermo', 'Recoleta', 'Retiro', 'San Nicolás',
            'Monserrat', 'San Telmo', 'Constitución', 'Barracas', 'La Boca',
            'Boedo', 'San Cristóbal', 'Balvanera', 'Once', 'Abasto'
        ]

        # Extraer barrio de múltiples fuentes
        barrio_fuentes = {}

        # 1. Del título (alta prioridad - el vendedor lo puso explícitamente)
        for barrio in barrios_conocidos:
            if barrio.lower() in title_lower:
                barrio_fuentes['titulo'] = barrio
                break

        # 2. De la ubicación (ya extraído antes, si existe)
        if 'barrio' in data:
            barrio_fuentes['ubicacion'] = data['barrio']

        # 3. De la URL (algunos tienen el barrio)
        for barrio in barrios_conocidos:
            if barrio.lower().replace(' ', '-') in url_lower:
                barrio_fuentes['url'] = barrio
                break

        # Decidir el barrio final (prioridad: titulo > ubicacion > url)
        if 'titulo' in barrio_fuentes:
            data['barrio'] = barrio_fuentes['titulo']
        elif 'ubicacion' in barrio_fuentes:
            data['barrio'] = barrio_fuentes['ubicacion']
        elif 'url' in barrio_fuentes:
            data['barrio'] = barrio_fuentes['url']

        # Marcar si hay conflicto (para debug)
        if len(set(barrio_fuentes.values())) > 1:
            data['_barrio_conflicto'] = str(barrio_fuentes)

        # Descripción completa
        desc_elem = soup.select_one('.ui-pdp-description__content')
        desc_text = desc_elem.text.lower() if desc_elem else ''

        # Combinar título y descripción para búsquedas
        full_text = title_lower + ' ' + desc_text

        if title_lower:
            # Solo marcar terraza/balcon si NO dice "sin" antes
            if 'terraza' in title_lower and 'sin terraza' not in title_lower:
                data['terraza'] = 'si'
            if ('balcon' in title_lower or 'balcón' in title_lower) and 'sin balcon' not in title_lower and 'sin balcón' not in title_lower:
                data['balcon'] = 'si'
            if 'sin expensas' in title_lower or 'sin exp' in title_lower:
                data['expensas'] = '0'

        # Luminosidad (de título o descripción)
        if 'luminoso' in full_text or 'muy luminoso' in full_text or 'luz natural' in full_text:
            data['luminosidad'] = 'si'

        # Tipo de propiedad (del título o URL) - orden de prioridad
        if '-ph-' in search_text or ' ph ' in search_text or 'p.h' in search_text:
            data['tipo'] = 'ph'
        elif 'duplex' in search_text or 'dúplex' in search_text:
            data['tipo'] = 'duplex'
        elif 'triplex' in search_text:
            data['tipo'] = 'triplex'
        elif 'loft' in search_text:
            data['tipo'] = 'loft'
        elif '/casa.' in url_lower or '-casa-' in search_text:
            data['tipo'] = 'casa'
        elif 'piso' in search_text:
            data['tipo'] = 'piso'
        elif '/departamento.' in url_lower or 'depto' in title_lower:
            data['tipo'] = 'depto'

        # Fecha de publicación ("Publicado hace X días")
        from datetime import datetime, timedelta
        pub_match = re.search(r'Publicado hace (\d+) día', resp.text)
        if pub_match:
            dias = int(pub_match.group(1))
            fecha_pub = datetime.now() - timedelta(days=dias)
            data['fecha_publicado'] = fecha_pub.strftime('%Y-%m-%d')
        else:
            # Buscar "Publicado ayer" o "Publicado hoy"
            if 'Publicado ayer' in resp.text:
                fecha_pub = datetime.now() - timedelta(days=1)
                data['fecha_publicado'] = fecha_pub.strftime('%Y-%m-%d')
            elif 'Publicado hoy' in resp.text:
                data['fecha_publicado'] = datetime.now().strftime('%Y-%m-%d')

        return data
    except Exception as e:
        return {'_error': str(e)}


# =============================================================================
# CACHE - Guarda resultados de scraping localmente
# =============================================================================

def load_cache():
    """Carga el cache de scraping"""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Guarda el cache de scraping"""
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def scrape_link(url, use_cache=True, cache=None):
    """Scrapea un link según su dominio. Usa cache si está disponible."""
    if not url or not url.startswith('http'):
        return None, False  # data, from_cache

    # Verificar cache
    if use_cache and cache and url in cache:
        cached = cache[url]
        # Cache válido si no tiene error o tiene _offline
        if '_error' not in cached or cached.get('_offline'):
            return cached, True

    # Scrapear
    data = None
    if 'argenprop.com' in url:
        data = scrape_argenprop(url)
    elif 'mercadolibre' in url:
        data = scrape_mercadolibre(url)

    # Guardar en cache si hay resultado
    if data and cache is not None:
        data['_cached_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        cache[url] = data

    return data, False


def cmd_scrape(check_all=False, no_cache=False):
    """Scrapea links del archivo local y actualiza los datos"""
    if not LOCAL_FILE.exists():
        print(f"❌ No existe {LOCAL_FILE}")
        print("   Ejecutá primero: python sync_sheet.py pull")
        return

    with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    headers = data['headers']
    rows = data['rows']

    # Cargar cache
    cache = load_cache() if not no_cache else {}
    cache_hits = 0

    # Encontrar filas que necesitan scraping
    to_scrape = []
    for i, row in enumerate(rows):
        link = row.get('link', '').strip()
        if not link:
            continue

        precio = row.get('precio', '').strip()
        m2 = row.get('m2_cub', '').strip()

        # Scrapear si faltan datos O si se pidió check_all (para verificar activo)
        if check_all or not precio or not m2:
            to_scrape.append((i, row))

    if not to_scrape:
        print("✅ No hay filas que necesiten scraping")
        return

    print(f"🔍 Scrapeando {len(to_scrape)} links...")
    if not no_cache:
        print(f"   (usando cache de {len(cache)} links)")
    updated = 0
    offline = 0

    for idx, row in to_scrape:
        link = row.get('link', '')
        direccion = row.get('direccion', '(sin dirección)')[:35]
        row_num = row.get('_row', idx + 2)
        print(f"   Fila {row_num}: {direccion}...")

        scraped, from_cache = scrape_link(link, use_cache=not no_cache, cache=cache)

        if scraped is None:
            print(f"      ⏭️  Dominio no soportado")
            continue

        if from_cache:
            cache_hits += 1
            print(f"      📦 Cache", end='')

        if '_error' in scraped:
            error = scraped['_error']
            print(f"      ❌ {error}")
            # Si es 404, 410 o marcado como offline, marcar como no activo
            if '404' in error or '410' in error or scraped.get('_offline'):
                if 'activo' in headers:
                    rows[idx]['activo'] = 'no'
                    offline += 1
                    print(f"      📴 Marcado como NO activo")
            continue

        # Si llegamos acá, el link está activo - siempre marcar como activo
        if 'activo' in headers:
            rows[idx]['activo'] = 'si'

        # Actualizar campos vacíos
        changes = []
        for col in SCRAPEABLE_COLS:
            if col in scraped and col in headers:
                current = row.get(col, '').strip()
                new_val = str(scraped[col]).strip()
                if not current and new_val:
                    rows[idx][col] = new_val
                    changes.append(f'{col}={new_val}')

        if changes:
            print(f"      ✅ {', '.join(changes)}")
            updated += 1
        else:
            print(f"      ⚪ Sin datos nuevos")

        # Validación: m2_tot debería ser >= m2_cub
        m2_cub = int(rows[idx].get('m2_cub') or 0)
        m2_tot = int(rows[idx].get('m2_tot') or 0)
        m2_terr = int(rows[idx].get('m2_terr') or 0)
        if m2_cub > 0 and m2_tot > 0:
            if m2_cub > m2_tot:
                print(f"      ⚠️  m² cub ({m2_cub}) > m² tot ({m2_tot}) - posible error")
            elif m2_terr > 0 and m2_cub + m2_terr != m2_tot:
                expected = m2_cub + m2_terr
                print(f"      ℹ️  m² cub({m2_cub}) + desc({m2_terr}) = {expected} ≠ tot({m2_tot})")

        time.sleep(0.5)

    # Guardar cambios
    data['rows'] = rows
    data['scraped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')

    with open(LOCAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Guardar cache
    if not no_cache:
        save_cache(cache)

    print(f"\n✅ {updated} filas actualizadas en {LOCAL_FILE}")
    if cache_hits:
        print(f"📦 {cache_hits} desde cache, {len(to_scrape) - cache_hits} scrapeados")
    if offline:
        print(f"📴 {offline} links marcados como NO activos")
    print(f"   Revisá con: python sync_sheet.py view")
    print(f"   Subí con: python sync_sheet.py push")


# =============================================================================
# PUSH - Sube archivo local a Google Sheets
# =============================================================================

def cmd_push(force=False, dry_run=False):
    """Sube los datos locales a Google Sheets"""
    if not LOCAL_FILE.exists():
        print(f"❌ No existe {LOCAL_FILE}")
        print("   Ejecutá primero: python sync_sheet.py pull")
        return

    with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    headers = data['headers']
    rows = data['rows']

    mode = "FORCE (sobrescribe todo)" if force else "MERGE (solo celdas vacías)"
    print(f"📤 {'[DRY RUN] ' if dry_run else ''}Push en modo {mode}...")
    print(f"   {len(rows)} filas a procesar")

    if dry_run:
        print("\n   Esto es un dry-run, no se aplicarán cambios.")
        return

    client = get_client()
    spreadsheet = client.open_by_key(SHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.sheet1

    if force:
        # Force: sobrescribir todo
        all_data = [headers]
        for row in rows:
            row_values = [row.get(h, '') for h in headers]
            all_data.append(row_values)

        worksheet.clear()
        worksheet.update(values=all_data, range_name='A1')

        # Formatear headers
        worksheet.format('A1:Z1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        worksheet.freeze(rows=1)

        print(f"✅ Sheet sobrescrito con {len(rows)} filas")
    else:
        # Merge: solo actualizar celdas que cambiaron
        # Descargar datos actuales para comparar
        current_values = worksheet.get_all_values()
        current_headers = [h.lower().strip() for h in current_values[0]] if current_values else []

        cells_to_update = []
        for row in rows:
            row_num = row.get('_row', 0)
            if row_num < 2:
                continue

            for col_name in SCRAPEABLE_COLS:
                if col_name not in headers:
                    continue

                col_idx = headers.index(col_name) + 1
                new_val = row.get(col_name, '').strip()

                # Obtener valor actual
                if row_num <= len(current_values) and col_idx <= len(current_values[row_num - 1]):
                    current_val = current_values[row_num - 1][col_idx - 1].strip()
                else:
                    current_val = ''

                # Solo actualizar si hay valor nuevo y celda vacía (o valores diferentes)
                if new_val and (not current_val or current_val != new_val):
                    cells_to_update.append(gspread.Cell(row_num, col_idx, new_val))

        if cells_to_update:
            worksheet.update_cells(cells_to_update)
            print(f"✅ {len(cells_to_update)} celdas actualizadas")
        else:
            print("✅ No hay cambios para aplicar")


# =============================================================================
# DIFF - Muestra diferencias entre local y cloud
# =============================================================================

# ANSI colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'


def cmd_diff():
    """Muestra diferencias entre datos locales y Google Sheets"""
    if not LOCAL_FILE.exists():
        print(f"❌ No existe {LOCAL_FILE}")
        print("   Ejecutá primero: python sync_sheet.py pull")
        return

    with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
        local_data = json.load(f)

    print("📊 Descargando datos actuales de Google Sheets para comparar...")

    client = get_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    try:
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.sheet1

    cloud_values = worksheet.get_all_values()
    cloud_headers = [h.lower().strip() for h in cloud_values[0]]
    cloud_rows = {}
    for i, row in enumerate(cloud_values[1:], start=2):
        cloud_rows[i] = dict(zip(cloud_headers, row))

    local_rows = local_data['rows']
    headers = local_data['headers']

    # Campos a comparar
    DIFF_COLS = ['precio', 'm2_cub', 'm2_tot', 'amb', 'direccion', 'barrio']

    def fmt_val(local_val, cloud_val, width=8):
        """Formatea valor con color según el cambio"""
        local_val = str(local_val or '').strip()
        cloud_val = str(cloud_val or '').strip()

        if not cloud_val and local_val:
            return f"{GREEN}{local_val:<{width}}{RESET}"  # Agregado
        elif cloud_val and local_val and local_val != cloud_val:
            return f"{YELLOW}{local_val:<{width}}{RESET}"  # Modificado
        elif not local_val:
            return f"{DIM}{'-':<{width}}{RESET}"  # Vacío
        return f"{local_val:<{width}}"  # Sin cambio

    print()
    print(f"{BOLD}Comparación: Local vs Google Sheets{RESET}")
    print(f"{GREEN}■ Verde = Nuevo{RESET}  {YELLOW}■ Amarillo = Modificado{RESET}  Sin color = Sin cambio")
    print()
    print(f"{'Fila':>4} │ {'Dirección':<20} │ {'Barrio':<12} │ {'Precio':>8} │ {'m²c':>4} │ {'m²t':>4} │ {'Amb':>3}")
    print('─' * 78)

    added_cells = 0
    modified_cells = 0

    for row in local_rows:
        fila = row.get('_row', 0)
        if fila < 2:
            continue

        cloud = cloud_rows.get(fila, {})

        # Solo mostrar filas con algún dato
        has_data = any(row.get(c) for c in DIFF_COLS)
        if not has_data:
            continue

        # Contar cambios
        for col in ['precio', 'm2_cub', 'm2_tot', 'amb']:
            local_val = str(row.get(col, '') or '').strip()
            cloud_val = str(cloud.get(col, '') or '').strip()
            if local_val and not cloud_val:
                added_cells += 1
            elif local_val and cloud_val and local_val != cloud_val:
                modified_cells += 1

        dir_val = fmt_val(row.get('direccion', '')[:20], cloud.get('direccion', ''), 20)
        barrio_val = fmt_val(row.get('barrio', '')[:12], cloud.get('barrio', ''), 12)
        precio_val = fmt_val(row.get('precio', ''), cloud.get('precio', ''), 8)
        m2c_val = fmt_val(row.get('m2_cub', ''), cloud.get('m2_cub', ''), 4)
        m2t_val = fmt_val(row.get('m2_tot', ''), cloud.get('m2_tot', ''), 4)
        amb_val = fmt_val(row.get('amb', ''), cloud.get('amb', ''), 3)

        print(f"{fila:>4} │ {dir_val} │ {barrio_val} │ {precio_val} │ {m2c_val} │ {m2t_val} │ {amb_val}")

    print()
    print(f"{BOLD}Resumen:{RESET}")
    print(f"  {GREEN}+ {added_cells} celdas nuevas{RESET}")
    print(f"  {YELLOW}~ {modified_cells} celdas modificadas{RESET}")

    if added_cells or modified_cells:
        print(f"\n  Ejecutá {BOLD}python sync_sheet.py push{RESET} para aplicar cambios")


# =============================================================================
# VIEW - Genera HTML para visualizar en browser
# =============================================================================

def check_link_status(url):
    """Verifica si un link está online"""
    if not url or not url.startswith('http'):
        return None
    try:
        resp = httpx.head(url, follow_redirects=True,
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        # Detectar redirect de MercadoLibre a búsqueda
        final_url = str(resp.url)
        if 'redirectedFromVip' in final_url:
            return 410  # Marcar como dado de baja
        if 'mercadolibre' in url and 'MLA-' in url and 'MLA-' not in final_url:
            return 410  # Redirect a búsqueda = no disponible
        return resp.status_code
    except:
        return 0


def cmd_view(check_links=False):
    """Genera un HTML con los datos locales vs cloud para ver en browser"""
    if not LOCAL_FILE.exists():
        print(f"❌ No existe {LOCAL_FILE}")
        print("   Ejecutá primero: python sync_sheet.py pull")
        return

    with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
        local_data = json.load(f)

    print("📊 Descargando datos actuales de Google Sheets...")

    client = get_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    try:
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.sheet1

    cloud_values = worksheet.get_all_values()
    cloud_headers = [h.lower().strip() for h in cloud_values[0]]
    cloud_rows = {}
    for i, row in enumerate(cloud_values[1:], start=2):
        cloud_rows[i] = dict(zip(cloud_headers, row))

    local_rows = local_data['rows']
    headers = local_data['headers']

    # Verificar links si se pidió
    link_status = {}
    if check_links:
        links_to_check = [(row.get('_row'), row.get('link', ''))
                         for row in local_rows if row.get('link', '').startswith('http')]
        print(f"🔍 Verificando {len(links_to_check)} links...")
        for i, (row_num, url) in enumerate(links_to_check):
            status = check_link_status(url)
            link_status[row_num] = status
            icon = '✓' if status == 200 else '✗' if status in [404, 410] else '?'
            print(f"   [{i+1}/{len(links_to_check)}] {icon} {status} - {url[:50]}...")
            time.sleep(0.3)

    # Columnas a mostrar
    SHOW_COLS = ['direccion', 'barrio', 'precio', 'm2_cub', 'm2_tot', 'amb', 'expensas', 'terraza', 'apto_credito', 'status', 'activo', 'notas']
    DIFF_COLS = ['precio', 'm2_cub', 'm2_tot', 'amb']

    # Generar HTML
    html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Preview - Sync Sheet</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .legend { margin-bottom: 20px; }
        .legend span { padding: 4px 12px; border-radius: 4px; margin-right: 10px; font-size: 14px; }
        .new { background: #d4edda; color: #155724; }
        .modified { background: #fff3cd; color: #856404; }
        .offline { background: #f8d7da; color: #721c24; }
        table { border-collapse: collapse; width: 100%; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 13px; }
        th { background: #333; color: white; padding: 10px 6px; text-align: left; position: sticky; top: 0; white-space: nowrap; }
        td { padding: 6px; border-bottom: 1px solid #eee; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
        tr:hover { background: #f9f9f9; }
        .new-cell { background: #d4edda; }
        .modified-cell { background: #fff3cd; }
        .offline-row { background: #fff5f5; }
        .empty-cell { color: #ccc; }
        .online { color: #28a745; }
        .offline { color: #dc3545; }
        .unknown { color: #6c757d; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .notes { max-width: 300px; font-size: 11px; color: #666; }
        .summary { margin-top: 20px; padding: 15px; background: white; border-radius: 8px; }
        .badge { padding: 2px 6px; border-radius: 3px; font-size: 11px; }
        .badge-yes { background: #d4edda; color: #155724; }
        .badge-no { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>📊 Preview: Local vs Google Sheets</h1>
    <div class="legend">
        <span class="new">Verde = Nuevo</span>
        <span class="modified">Amarillo = Modificado</span>
        <span class="offline">Rojo = Offline (404/410)</span>
    </div>
    <table>
        <thead>
            <tr>
                <th>Fila</th>
                <th>Link</th>
"""
    for col in SHOW_COLS:
        label = col.replace('_', ' ').replace('m2', 'm²').title()
        html += f"                <th>{label}</th>\n"
    html += """            </tr>
        </thead>
        <tbody>
"""

    added_cells = 0
    modified_cells = 0
    offline_count = 0

    for row in local_rows:
        fila = row.get('_row', 0)
        if fila < 2:
            continue

        cloud = cloud_rows.get(fila, {})

        # Solo mostrar filas con algún dato
        has_data = any(row.get(c) for c in SHOW_COLS if c not in ['notas'])
        if not has_data:
            continue

        # Verificar estado del link
        link_url = row.get('link', '')
        status = link_status.get(fila)
        is_offline = status in [404, 410, 0] if status is not None else False
        if is_offline:
            offline_count += 1

        row_class = 'offline-row' if is_offline else ''
        html += f"            <tr class=\"{row_class}\">\n                <td>{fila}</td>\n"

        # Columna de link con estado
        if link_url:
            if status is not None:
                if status == 200:
                    link_icon = '<span class="online">✓</span>'
                elif status in [404, 410]:
                    link_icon = f'<span class="offline">✗ {status}</span>'
                else:
                    link_icon = f'<span class="unknown">? {status}</span>'
            else:
                link_icon = ''
            html += f'                <td><a href="{link_url}" target="_blank">🔗</a> {link_icon}</td>\n'
        else:
            html += '                <td class="empty-cell">-</td>\n'

        for col in SHOW_COLS:
            local_val = str(row.get(col, '') or '').strip()
            cloud_val = str(cloud.get(col, '') or '').strip()

            css_class = ''
            if col in DIFF_COLS:
                if local_val and not cloud_val:
                    css_class = 'new-cell'
                    added_cells += 1
                elif local_val and cloud_val and local_val != cloud_val:
                    css_class = 'modified-cell'
                    modified_cells += 1

            # Formatear valores especiales
            if col == 'notas':
                css_class += ' notes'
                local_val = local_val[:100] + '...' if len(local_val) > 100 else local_val
            elif col in ['terraza', 'apto_credito', 'activo']:
                if local_val.lower() == 'si':
                    local_val = '<span class="badge badge-yes">Sí</span>'
                elif local_val.lower() == 'no':
                    local_val = '<span class="badge badge-no">No</span>'

            if not local_val:
                css_class = 'empty-cell'
                local_val = '-'

            html += f"                <td class=\"{css_class}\">{local_val}</td>\n"

        html += "            </tr>\n"

    html += f"""        </tbody>
    </table>
    <div class="summary">
        <strong>Resumen:</strong>
        <span class="new">+{added_cells} celdas nuevas</span>
        <span class="modified">~{modified_cells} celdas modificadas</span>
        {'<span class="offline">⚠️ ' + str(offline_count) + ' links offline</span>' if offline_count else ''}
    </div>
</body>
</html>
"""

    # Guardar HTML
    html_path = LOCAL_FILE.parent / 'preview.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Preview generado: {html_path}")

    # Abrir en browser
    import subprocess
    subprocess.run(['xdg-open', str(html_path)])


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Sincroniza Google Sheets con datos scrapeados',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Flujo de trabajo:
    python sync_sheet.py pull          # 1. Descargar de Google Sheets
    python sync_sheet.py scrape        # 2. Scrapear links faltantes
    python sync_sheet.py view          # 3. Ver preview en browser
    python sync_sheet.py diff          # 3. Ver cambios en terminal
    python sync_sheet.py push          # 4. Subir cambios (merge)
    python sync_sheet.py push --force  # 4. Subir sobrescribiendo todo
        """
    )

    parser.add_argument('command', choices=['pull', 'scrape', 'view', 'diff', 'push'],
                       help='Comando a ejecutar')
    parser.add_argument('--force', action='store_true',
                       help='[push] Sobrescribe todo el sheet')
    parser.add_argument('--dry-run', action='store_true',
                       help='[push] Muestra cambios sin aplicar')
    parser.add_argument('--check-links', action='store_true',
                       help='[view] Verifica si los links están online')
    parser.add_argument('--all', action='store_true',
                       help='[scrape] Scrapea todos los links (no solo los que faltan datos)')
    parser.add_argument('--no-cache', action='store_true',
                       help='[scrape] Ignora el cache y re-scrapea todo')

    args = parser.parse_args()

    if args.command == 'pull':
        cmd_pull()
    elif args.command == 'scrape':
        cmd_scrape(check_all=args.all, no_cache=args.no_cache)
    elif args.command == 'view':
        cmd_view(check_links=args.check_links)
    elif args.command == 'diff':
        cmd_diff()
    elif args.command == 'push':
        cmd_push(force=args.force, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
