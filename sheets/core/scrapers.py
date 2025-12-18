"""
Scrapers para portales inmobiliarios argentinos.

Incluye:
- scrape_argenprop: Scraper para Argenprop
- scrape_mercadolibre: Scraper para MercadoLibre
- scrape_link: Dispatcher que elige el scraper correcto
"""

import re
import time
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

from .helpers import (
    BARRIOS_CABA,
    detectar_barrio,
    detectar_atributo,
    extraer_numero,
    calcular_m2_faltantes,
)


# =============================================================================
# HEADERS HTTP
# =============================================================================

HEADERS_SIMPLE = {
    'User-Agent': 'Mozilla/5.0'
}

HEADERS_BROWSER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.google.com/',
    'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}


# =============================================================================
# SCRAPER: ARGENPROP - Funciones auxiliares
# =============================================================================

def _argenprop_extract_features(soup):
    """Extrae datos de la lista de features de Argenprop."""
    data = {}
    for li in soup.select('.property-features li, .property-features-item'):
        txt = li.text.strip().lower()
        if 'm² cub' in txt or 'm2 cub' in txt or 'sup. cubierta' in txt:
            num = extraer_numero(txt)
            if num:
                data['m2_cub'] = num
        elif 'm² tot' in txt or 'm2 tot' in txt or 'sup. total' in txt:
            num = extraer_numero(txt)
            if num:
                data['m2_tot'] = num
        elif 'descubierta' in txt or 'm² desc' in txt or 'terraza' in txt and 'm²' in txt:
            num = extraer_numero(txt)
            if num:
                data['m2_terr'] = num
        elif 'ambiente' in txt and 'cant' in txt:
            num = extraer_numero(txt)
            if num:
                data['amb'] = num
        elif 'antigüedad' in txt or 'antiguedad' in txt:
            num = extraer_numero(txt)
            if num:
                data['antiguedad'] = num
        elif 'balcón' in txt or 'balcon' in txt:
            # "tipo de balcón: terraza" = balcón, NO terraza
            if 'tipo' in txt and 'terraza' in txt:
                data['balcon'] = 'si'
            else:
                result = detectar_atributo(txt, 'balcon')
                if result:
                    data['balcon'] = result
        elif 'terraza' in txt:
            if 'balc' not in txt and 'tipo' not in txt:
                result = detectar_atributo(txt, 'terraza')
                if result:
                    data['terraza'] = result
        elif 'cochera' in txt:
            result = detectar_atributo(txt, 'cochera')
            if result == 'no':
                data['cocheras'] = '0'
            elif result == 'si':
                data['cocheras'] = extraer_numero(txt) or '1'
        elif 'baño' in txt:
            num = extraer_numero(txt)
            if num:
                data['banos'] = num
        elif 'expensas' in txt:
            num = extraer_numero(txt, quitar_miles=True)
            if num:
                exp_val = int(num)
                if exp_val < 1000:
                    exp_val = exp_val * 1000
                data['expensas'] = str(exp_val)
        elif 'estado' in txt:
            txt_clean = txt.replace('estado del inmueble', '').replace('estado:', '').replace('estado', '').strip()
            txt_clean = txt_clean.strip(': ').title()
            if txt_clean and txt_clean.lower() not in ['si', 'no', '']:
                data['estado'] = txt_clean
    return data


def _argenprop_validate_m2(data):
    """Valida consistencia de m² en datos de Argenprop. Modifica data in-place."""
    m2_cub = int(data.get('m2_cub') or 0)
    m2_tot = int(data.get('m2_tot') or 0)
    m2_desc = int(data.get('m2_terr') or 0)

    if m2_cub > 0 and m2_tot > 0 and m2_desc > 0:
        esperado = m2_cub + m2_desc
        if abs(esperado - m2_tot) > 1:
            data['_inconsistencia'] = f'cub({m2_cub}) + desc({m2_desc}) = {esperado} ≠ tot({m2_tot})'

    if m2_cub > 0 and m2_tot > 0 and m2_cub > m2_tot:
        msg = f'm2_cub({m2_cub}) > m2_tot({m2_tot}) - probable inversión'
        if '_inconsistencia' in data:
            data['_inconsistencia'] += f'; {msg}'
        else:
            data['_inconsistencia'] = msg


# =============================================================================
# SCRAPER: ARGENPROP
# =============================================================================

def scrape_argenprop(url):
    """Scrapea una publicación de Argenprop."""
    try:
        resp = httpx.get(url, follow_redirects=True, headers=HEADERS_SIMPLE, timeout=10)
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

        # Features detallados (usando función auxiliar)
        data.update(_argenprop_extract_features(soup))

        # Luminosidad (buscar en descripción completa)
        desc_full = soup.select_one('.property-description-container, .property-description')
        if desc_full:
            full_text = desc_full.text.lower()
            result_luz = detectar_atributo(full_text, 'luminosidad')
            if result_luz == 'si':
                data['luminosidad'] = 'si'

        # Inmobiliaria
        inmob = soup.select_one('.property-contact__title, .property-sidebar h3, [class*="contact"] h3')
        if inmob:
            data['inmobiliaria'] = inmob.text.strip()

        # Barrio (del breadcrumb o container)
        location = soup.select_one('.property-container')
        if location:
            barrio = detectar_barrio(location.text)
            if barrio:
                data['barrio'] = barrio

        # Validar consistencia de m²
        _argenprop_validate_m2(data)

        return data
    except Exception as e:
        return {'_error': str(e)}


# =============================================================================
# SCRAPER: MERCADOLIBRE - Funciones auxiliares
# =============================================================================

def _meli_extract_location(soup):
    """Extrae ubicación, dirección y barrio del HTML de MercadoLibre."""
    data = {}
    location = soup.select_one('.ui-vip-location')
    if not location:
        return data

    loc_text = location.text.strip()
    for prefix in ['Ubicación', 'Ver mapa', 'e información de la zona']:
        loc_text = loc_text.replace(prefix, '')
    loc_text = loc_text.strip()

    parts = [p.strip() for p in loc_text.split(',') if p.strip()]
    if len(parts) >= 1 and any(c.isdigit() for c in parts[0]):
        direccion_raw = parts[0]

        # Limpiar direcciones mal formadas
        if ' - ' in direccion_raw:
            partes = direccion_raw.split(' - ')
            for p in partes:
                if re.search(r'[A-Za-záéíóúÁÉÍÓÚñÑ\.\s]+\d+', p.strip()):
                    direccion_raw = p.strip()
                    break

        # Remover prefijos como "4 Amb"
        direccion_raw = re.sub(r'^\d+\s*(Amb|Ambientes?)\s*', '', direccion_raw, flags=re.IGNORECASE).strip()

        # Remover barrios pegados al inicio
        for b in BARRIOS_CABA:
            if direccion_raw.lower().startswith(b.lower()):
                direccion_raw = direccion_raw[len(b):].strip(' -')
                break

        data['direccion'] = direccion_raw

    if len(parts) >= 2:
        for part in parts[1:]:
            if part not in ['Capital Federal', 'Buenos Aires', 'GBA Norte', 'GBA Sur', 'GBA Oeste']:
                data['barrio'] = part
                break

    # Barrio del link alternativo
    if 'barrio' not in data:
        ubicacion = soup.select_one('.ui-vip-location a')
        if ubicacion:
            data['barrio'] = ubicacion.text.strip()

    return data


def _meli_extract_table_data(soup):
    """Extrae datos de la tabla de características de MercadoLibre."""
    data = {}
    for row in soup.select('tr.andes-table__row'):
        header = row.select_one('th')
        value = row.select_one('td')
        if not header or not value:
            continue

        h = header.text.strip().lower()
        v = value.text.strip()

        if 'superficie cubierta' in h:
            num = extraer_numero(v)
            if num:
                data['m2_cub'] = num
        elif 'superficie total' in h:
            num = extraer_numero(v)
            if num:
                data['m2_tot'] = num
        elif 'superficie descubierta' in h or 'sup. descubierta' in h or 'superficie de balc' in h:
            num = extraer_numero(v)
            if num:
                data['m2_terr'] = num
        elif 'ambientes' in h:
            num = extraer_numero(v)
            if num:
                data['amb'] = num
        elif 'dormitorio' in h:
            num = extraer_numero(v)
            if num:
                data['dormitorios'] = num
        elif 'baño' in h:
            num = extraer_numero(v)
            if num:
                data['banos'] = num
        elif 'antigüedad' in h or 'antiguedad' in h:
            num = extraer_numero(v)
            if num:
                data['antiguedad'] = num
        elif 'expensas' in h:
            num = extraer_numero(v)
            if num:
                exp_val = int(num)
                if exp_val < 1000:
                    exp_val = exp_val * 1000
                data['expensas'] = str(exp_val)
        elif 'apto cr' in h or 'apto_cr' in h:
            data['apto_credito'] = 'si' if 'sí' in v.lower() or 'si' in v.lower() else 'no'
        elif 'tipo de' in h:
            data['tipo'] = v.lower()
        elif 'cochera' in h:
            num = extraer_numero(v)
            if num:
                data['cocheras'] = num
        elif 'disposición' in h or 'disposicion' in h:
            data['disposicion'] = v.lower()
        elif 'número de piso' in h or 'piso de la unidad' in h:
            num = extraer_numero(v)
            if num:
                data['piso'] = num
        elif 'ascensor' in h:
            result = detectar_atributo(f"{h}: {v}", 'ascensor')
            if result:
                data['ascensor'] = result
            else:
                data['ascensor'] = 'si' if 'sí' in v.lower() or v.lower() == 'si' else 'no'
        elif h == 'balcón' or h == 'balcon':
            result = detectar_atributo(f"{h}: {v}", 'balcon')
            if result:
                data['balcon'] = result
            else:
                data['balcon'] = 'si' if 'sí' in v.lower() or v.lower() == 'si' else 'no'
        elif h == 'terraza':
            result = detectar_atributo(f"{h}: {v}", 'terraza')
            if result:
                data['terraza'] = result
            else:
                data['terraza'] = 'si' if 'sí' in v.lower() or v.lower() == 'si' else 'no'
        elif 'estado' in h or 'condición' in h or 'condicion' in h:
            if v and v.lower() not in ['si', 'sí', 'no']:
                data['estado'] = v.title()

    return data


def _meli_resolve_barrio(soup, url, title_text, current_barrio):
    """Resuelve el barrio de múltiples fuentes, retorna dict con barrio y conflicto."""
    data = {}
    barrio_fuentes = {}

    barrio_titulo = detectar_barrio(title_text)
    if barrio_titulo:
        barrio_fuentes['titulo'] = barrio_titulo

    if current_barrio:
        barrio_fuentes['ubicacion'] = current_barrio

    barrio_url = detectar_barrio(url.replace('-', ' '))
    if barrio_url:
        barrio_fuentes['url'] = barrio_url

    # Prioridad: titulo > ubicacion > url
    if 'titulo' in barrio_fuentes:
        data['barrio'] = barrio_fuentes['titulo']
    elif 'ubicacion' in barrio_fuentes:
        data['barrio'] = barrio_fuentes['ubicacion']
    elif 'url' in barrio_fuentes:
        data['barrio'] = barrio_fuentes['url']

    if len(set(barrio_fuentes.values())) > 1:
        data['_barrio_conflicto'] = str(barrio_fuentes)

    return data


def _meli_extract_from_text(title_lower, desc_text, current_data):
    """Extrae datos del título y descripción que complementan la tabla."""
    data = {}
    full_text = title_lower + ' ' + desc_text

    if title_lower:
        result_terraza = detectar_atributo(title_lower, 'terraza')
        if result_terraza == 'si':
            data['terraza'] = 'si'
        result_balcon = detectar_atributo(title_lower, 'balcon')
        if result_balcon == 'si':
            data['balcon'] = 'si'
        if 'sin expensas' in title_lower or 'sin exp' in title_lower:
            data['expensas'] = '0'

    # Luminosidad
    result_luz = detectar_atributo(full_text, 'luminosidad')
    if result_luz == 'si':
        data['luminosidad'] = 'si'

    # Apto crédito (si no se encontró en campos estructurados)
    if 'apto_credito' not in current_data:
        result_apto = detectar_atributo(full_text, 'apto_credito')
        if result_apto:
            data['apto_credito'] = result_apto

    return data


def _meli_extract_tipo(search_text, url_lower, title_lower):
    """Detecta el tipo de propiedad del texto."""
    if '-ph-' in search_text or ' ph ' in search_text or 'p.h' in search_text:
        return {'tipo': 'ph'}
    elif 'duplex' in search_text or 'dúplex' in search_text:
        return {'tipo': 'duplex'}
    elif 'triplex' in search_text:
        return {'tipo': 'triplex'}
    elif 'loft' in search_text:
        return {'tipo': 'loft'}
    elif '/casa.' in url_lower or '-casa-' in search_text:
        return {'tipo': 'casa'}
    elif 'piso' in search_text:
        return {'tipo': 'piso'}
    elif '/departamento.' in url_lower or 'depto' in title_lower:
        return {'tipo': 'depto'}
    return {}


def _meli_extract_fecha_publicado(resp_text):
    """Extrae la fecha de publicación del texto de respuesta."""
    pub_match = re.search(r'Publicado hace (\d+)\s*(día|semana|mes|año)', resp_text, re.IGNORECASE)
    if pub_match:
        cantidad = int(pub_match.group(1))
        unidad = pub_match.group(2).lower()
        if 'día' in unidad:
            fecha_pub = datetime.now() - timedelta(days=cantidad)
        elif 'semana' in unidad:
            fecha_pub = datetime.now() - timedelta(weeks=cantidad)
        elif 'mes' in unidad:
            fecha_pub = datetime.now() - timedelta(days=cantidad * 30)
        elif 'año' in unidad:
            fecha_pub = datetime.now() - timedelta(days=cantidad * 365)
        else:
            return {}
        return {'fecha_publicado': fecha_pub.strftime('%Y-%m-%d')}

    if 'Publicado ayer' in resp_text:
        fecha_pub = datetime.now() - timedelta(days=1)
        return {'fecha_publicado': fecha_pub.strftime('%Y-%m-%d')}
    if 'Publicado hoy' in resp_text:
        return {'fecha_publicado': datetime.now().strftime('%Y-%m-%d')}

    return {}


def _meli_validate_m2(data):
    """Valida y corrige inconsistencias de m2. Modifica data in-place."""
    m2_cub = int(data.get('m2_cub') or 0)
    m2_tot = int(data.get('m2_tot') or 0)
    m2_desc = int(data.get('m2_terr') or data.get('m2_desc') or 0)

    if m2_tot == 0 and m2_cub > 0:
        data['m2_tot'] = m2_cub + m2_desc
        data['_inconsistencia'] = 'm2_tot=0 en publicación, calculado desde m2_cub+m2_desc'

    # Detectar m2_desc sospechosamente grande
    if m2_desc > 0 and m2_cub > 0 and m2_desc > m2_cub * 0.5:
        msg = f'm2_desc={m2_desc} muy grande vs m2_cub={m2_cub}'
        if '_inconsistencia' in data:
            data['_inconsistencia'] += f'; {msg}'
        else:
            data['_inconsistencia'] = msg

    # Detectar m2_cub > m2_tot
    m2_tot_final = int(data.get('m2_tot') or 0)
    if m2_cub > 0 and m2_tot_final > 0 and m2_cub > m2_tot_final:
        msg = f'm2_cub({m2_cub}) > m2_tot({m2_tot_final}) - probable inversión'
        if '_inconsistencia' in data:
            data['_inconsistencia'] += f'; {msg}'
        else:
            data['_inconsistencia'] = msg


# =============================================================================
# SCRAPER: MERCADOLIBRE
# =============================================================================

def scrape_mercadolibre(url):
    """Scrapea una publicación de MercadoLibre Inmuebles."""
    try:
        resp = httpx.get(url, follow_redirects=True, headers=HEADERS_BROWSER, timeout=15)
        if resp.status_code != 200:
            return {'_error': f'Status {resp.status_code}'}

        # Detectar si redirigió a página de búsqueda (publicación no disponible)
        final_url = str(resp.url)
        if 'redirectedFromVip' in final_url or ('MLA-' in url and 'MLA-' not in final_url):
            return {'_error': 'Publicación no disponible (redirect)', '_offline': True}

        soup = BeautifulSoup(resp.text, 'lxml')

        # Detectar "Publicación finalizada"
        warning_text = soup.select_one('.andes-message__text--orange')
        if warning_text and 'finalizada' in warning_text.text.lower():
            return {'_error': 'Publicación finalizada', '_offline': True}

        if '"text":"Publicación finalizada"' in resp.text:
            return {'_error': 'Publicación finalizada', '_offline': True}

        # Verificar si tiene precio
        precio_elem = soup.select_one('.andes-money-amount__fraction')
        if not precio_elem:
            warning = soup.select_one('.ui-pdp-message-warning, .ui-vip-error')
            if warning:
                return {'_error': 'Publicación no disponible', '_offline': True}
            return {'_error': 'No se pudo extraer precio'}

        # Extraer datos usando funciones auxiliares
        data = {'precio': precio_elem.text.strip().replace('.', '')}
        data.update(_meli_extract_location(soup))
        data.update(_meli_extract_table_data(soup))

        # Título y textos para búsqueda
        title = soup.select_one('h1.ui-pdp-title')
        title_text = title.text if title else ''
        title_lower = title_text.lower()
        url_lower = url.lower()
        search_text = title_lower + ' ' + url_lower

        # Resolver barrio de múltiples fuentes
        barrio_data = _meli_resolve_barrio(soup, url, title_text, data.get('barrio'))
        data.update(barrio_data)

        # Extraer de descripción
        desc_elem = soup.select_one('.ui-pdp-description__content')
        desc_text = desc_elem.text.lower() if desc_elem else ''
        data.update(_meli_extract_from_text(title_lower, desc_text, data))

        # Tipo de propiedad (solo si no vino de tabla)
        if 'tipo' not in data:
            data.update(_meli_extract_tipo(search_text, url_lower, title_lower))

        # Fecha de publicación
        data.update(_meli_extract_fecha_publicado(resp.text))

        # Validar y corregir m2
        _meli_validate_m2(data)

        return data
    except Exception as e:
        return {'_error': str(e)}


# =============================================================================
# DISPATCHER
# =============================================================================

def scrape_link(url, use_cache=True, cache=None):
    """Scrapea un link según su dominio. Usa cache si está disponible.

    Args:
        url: URL a scrapear
        use_cache: Si usar cache
        cache: Dict de cache (se modifica in-place)

    Returns:
        (data, from_cache): Tupla con datos y si vino del cache
    """
    if not url or not url.startswith('http'):
        return None, False

    # Verificar cache
    if use_cache and cache and url in cache:
        cached = cache[url]
        if '_error' not in cached or cached.get('_offline'):
            return cached, True

    # Scrapear
    data = None
    if 'argenprop.com' in url:
        data = scrape_argenprop(url)
    elif 'mercadolibre' in url:
        data = scrape_mercadolibre(url)

    # Guardar en cache
    if data and cache is not None:
        data['_cached_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        cache[url] = data

    return data, False


# =============================================================================
# FUNCIONES HELPER PARA PROCESO DE SCRAPING
# =============================================================================

def get_rows_to_scrape(rows, check_all=False):
    """
    Filtra filas que necesitan scraping.

    Args:
        rows: Lista de filas del sheet
        check_all: Si True, incluye todas las filas con link (para verificar activo)

    Returns:
        Lista de tuplas (indice, fila) que necesitan scraping
    """
    to_scrape = []
    for i, row in enumerate(rows):
        link = row.get('link', '').strip()
        if not link:
            continue

        precio = row.get('precio', '').strip()
        m2 = row.get('m2_cub', '').strip()

        # Scrapear si faltan datos O si se pidio check_all
        if check_all or not precio or not m2:
            to_scrape.append((i, row))

    return to_scrape


def apply_scraped_data(row, scraped, scrapeable_cols, headers, force_update=False):
    """
    Aplica datos scrapeados a una fila.

    Args:
        row: Dict de la fila a actualizar (se modifica in-place)
        scraped: Dict con datos scrapeados
        scrapeable_cols: Lista de columnas que se pueden actualizar
        headers: Lista de headers del sheet
        force_update: Si True, sobrescribe valores existentes

    Returns:
        Dict con listas 'changes' (nuevos) y 'updates' (modificados)
    """
    changes = []
    updates = []

    for col in scrapeable_cols:
        if col not in scraped or col not in headers:
            continue

        current = row.get(col, '').strip() if row.get(col) else ''
        new_val = str(scraped[col]).strip()

        # Llenar vacios siempre
        if not current and new_val:
            row[col] = new_val
            changes.append(f'{col}={new_val}')
        # Sobrescribir existentes solo si force_update
        elif force_update and current and new_val and current != new_val:
            row[col] = new_val
            updates.append(f'{col}: {current}->{new_val}')

    # Calcular m2 faltantes si tenemos 2 de 3
    m2_calculados = calcular_m2_faltantes(row)
    for col, val in m2_calculados.items():
        if col in headers and not row.get(col, '').strip():
            row[col] = val
            changes.append(f'{col}={val} (calc)')

    return {'changes': changes, 'updates': updates}


def is_offline_error(scraped):
    """
    Determina si el resultado del scraping indica que el aviso esta offline.

    Args:
        scraped: Dict con resultado del scraping

    Returns:
        bool: True si el aviso esta offline
    """
    if not scraped or '_error' not in scraped:
        return False

    error = scraped.get('_error', '')
    if scraped.get('_offline'):
        return True
    if '404' in error or '410' in error:
        return True

    return False
