"""
Sistema de prints - Backup de publicaciones en PDF/PNG.

Funciones para gestionar screenshots/PDFs de avisos inmobiliarios.
"""

import re
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path

from .helpers import extraer_id_propiedad
from .storage import PRINTS_DIR

# =============================================================================
# CONSTANTES
# =============================================================================

# Dias antes de considerar un print como vencido
PRINT_DIAS_VENCIMIENTO = 30

# Formato estandar: {ID}_{YYYY-MM-DD}.ext donde ID es MLA123456 o AP123456
# Ejemplos: MLA1513702911_2025-12-15.pdf, AP17094976_2025-12-15.png
PRINT_PATTERN_ID = re.compile(
    r'^(MLA\d+|AP\d+|ZP\d+)(?:_(\d{4}-\d{2}-\d{2}))?\.(?:pdf|png|jpg|jpeg)$',
    re.IGNORECASE
)

# Formato legacy: fila_XX_YYYY-MM-DD.ext (mantener compatibilidad)
PRINT_PATTERN_FILA = re.compile(
    r'^fila_(\d+)(?:_(\d{4}-\d{2}-\d{2}))?\.(?:pdf|png|jpg|jpeg)$',
    re.IGNORECASE
)

# Extensiones de archivo validas para prints
PRINT_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg']

# Longitud mínima de contenido antes de cortar texto del PDF
# Evita cortar prematuramente si hay secciones irrelevantes al inicio
PDF_MIN_CONTENT_LENGTH = 500


# =============================================================================
# FUNCIONES HELPER
# =============================================================================

def generar_nombre_print(link_or_id, extension='pdf'):
    """
    Genera nombre estandar para un print: {ID}_YYYY-MM-DD.ext

    Args:
        link_or_id: URL del aviso o ID de propiedad (MLA123, AP456)
        extension: Extension del archivo (default: pdf)

    Returns:
        str: Nombre del archivo (ej: MLA123456_2025-12-15.pdf) o None si no se puede generar
    """
    fecha = datetime.now().strftime('%Y-%m-%d')
    if link_or_id.startswith('http'):
        prop_id = extraer_id_propiedad(link_or_id)
    else:
        prop_id = link_or_id
    if not prop_id:
        return None
    return f"{prop_id}_{fecha}.{extension}"


def normalizar_texto(texto):
    """
    Normaliza texto para comparacion (minusculas, sin acentos, sin espacios extras).

    Args:
        texto: Texto a normalizar

    Returns:
        str: Texto normalizado (solo letras y numeros)
    """
    if not texto:
        return ''
    texto = unicodedata.normalize('NFD', texto.lower())
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-z0-9]', '', texto)
    return texto


# =============================================================================
# FUNCIONES PRINCIPALES
# =============================================================================

def get_prints_index(rows, prints_dir=None):
    """
    Construye indice de prints asociando archivos con propiedades.

    Detecta por: ID del portal (MLA/AP), fila_XX (legacy), o ID en nombre.

    Args:
        rows: Lista de filas del sheet (cada una con _row, link, etc.)
        prints_dir: Directorio de prints (default: PRINTS_DIR)

    Returns:
        dict: {fila: {archivo, fecha, dias, vencido, prop_id, historial}}
    """
    if prints_dir is None:
        prints_dir = PRINTS_DIR

    if not prints_dir.exists():
        return {}

    # Construir lookup de propiedades por ID unico
    props_by_id = {}      # {MLA123: fila}
    props_by_fila = {}    # {fila: row}

    for row in rows:
        fila = int(row.get('_row') or 0)
        if fila < 2:
            continue

        link = row.get('link', '')
        props_by_fila[fila] = row

        # Indexar por ID unico del portal
        prop_id = extraer_id_propiedad(link)
        if prop_id:
            props_by_id[prop_id.upper()] = fila

    # Escanear archivos de prints
    prints_index = {}      # {fila: info_del_print_mas_reciente}
    prints_historial = {}  # {fila: [lista de todos los prints]}

    for f in prints_dir.iterdir():
        if not f.is_file():
            continue
        if f.suffix.lower() not in PRINT_EXTENSIONS:
            continue
        if f.name.startswith('.'):
            continue

        # Obtener fecha de modificacion
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        dias_antiguedad = (datetime.now() - mtime).days
        vencido = dias_antiguedad > PRINT_DIAS_VENCIMIENTO

        archivo_info = {
            'archivo': f.name,
            'fecha': mtime.strftime('%Y-%m-%d'),
            'dias': dias_antiguedad,
            'vencido': vencido,
            'prop_id': None
        }

        fila_asociada = None

        # 1. Detectar por patron nuevo: {ID}_YYYY-MM-DD.ext (MLA123_2025-12-15.pdf)
        match = PRINT_PATTERN_ID.match(f.name)
        if match:
            prop_id = match.group(1).upper()
            archivo_info['prop_id'] = prop_id
            if match.group(2):
                archivo_info['fecha_nombre'] = match.group(2)
            if prop_id in props_by_id:
                fila_asociada = props_by_id[prop_id]

        # 2. Detectar por patron legacy: fila_XX_YYYY-MM-DD.ext
        if not fila_asociada:
            match = PRINT_PATTERN_FILA.match(f.name)
            if match:
                fila_asociada = int(match.group(1))
                if match.group(2):
                    archivo_info['fecha_nombre'] = match.group(2)

        # 3. Detectar por ID en cualquier parte del nombre
        if not fila_asociada:
            # Buscar MLA o AP seguido de numeros
            for prop_id, fila in props_by_id.items():
                if prop_id in f.name.upper():
                    fila_asociada = fila
                    archivo_info['prop_id'] = prop_id
                    break

        if fila_asociada and fila_asociada in props_by_fila:
            # Agregar al historial
            if fila_asociada not in prints_historial:
                prints_historial[fila_asociada] = []
            prints_historial[fila_asociada].append(archivo_info)

            # Guardar solo el mas reciente en el indice principal
            if fila_asociada not in prints_index:
                prints_index[fila_asociada] = archivo_info
            elif prints_index[fila_asociada]['dias'] > dias_antiguedad:
                prints_index[fila_asociada] = archivo_info

    # Agregar historial al indice (evitar referencia circular)
    for fila, info in prints_index.items():
        historial = prints_historial.get(fila, [])
        if len(historial) > 1:
            # Copiar historial sin el item actual para evitar ref circular
            historial_otros = [
                {k: v for k, v in h.items() if k != 'historial'}
                for h in historial if h['archivo'] != info['archivo']
            ]
            if historial_otros:
                info['historial'] = sorted(historial_otros, key=lambda x: x['fecha'], reverse=True)
            info['versiones'] = len(historial)

    return prints_index


def clasificar_prints(rows, prints_dir=None):
    """
    Clasifica propiedades segun estado de sus prints.

    Args:
        rows: Lista de filas del sheet
        prints_dir: Directorio de prints (opcional)

    Returns:
        dict con listas: activas, con_print, sin_print, vencidos, actualizados
    """
    prints_index = get_prints_index(rows, prints_dir)

    # Filtrar propiedades activas
    activas = []
    for row in rows:
        fila = int(row.get('_row') or 0)
        if fila < 2:
            continue

        activo = (row.get('activo') or '').lower()
        if activo == 'no':
            continue

        link = row.get('link', '')
        if not link.startswith('http'):
            continue

        prop_id = extraer_id_propiedad(link)
        print_info = prints_index.get(fila)

        activas.append({
            'fila': fila,
            'prop_id': prop_id,
            'direccion': row.get('direccion', ''),
            'barrio': row.get('barrio', ''),
            'precio': row.get('precio', ''),
            'link': link,
            'print': print_info,
            'nombre_sugerido': generar_nombre_print(link) if prop_id else None
        })

    con_print = [p for p in activas if p['print']]
    sin_print = [p for p in activas if not p['print']]
    vencidos = [p for p in con_print if p['print']['vencido']]
    actualizados = [p for p in con_print if not p['print']['vencido']]

    return {
        'activas': activas,
        'con_print': con_print,
        'sin_print': sin_print,
        'vencidos': vencidos,
        'actualizados': actualizados,
        'prints_index': prints_index
    }


def sync_print_dates(rows, prints_dir=None):
    """
    Sincroniza fechas de prints en las filas.

    Actualiza el campo 'fecha_print' de cada fila con la fecha
    del print mas reciente asociado.

    Args:
        rows: Lista de filas (se modifican in-place)
        prints_dir: Directorio de prints (opcional)

    Returns:
        int: Cantidad de filas actualizadas
    """
    prints_index = get_prints_index(rows, prints_dir)
    updated = 0

    for row in rows:
        fila = int(row.get('_row') or 0)
        if fila in prints_index:
            fecha_print = prints_index[fila].get('fecha', '')
            if fecha_print and row.get('fecha_print', '') != fecha_print:
                row['fecha_print'] = fecha_print
                updated += 1

    return updated


# =============================================================================
# FUNCIONES PARA SCAN DE PRINTS
# =============================================================================

def build_property_index(rows):
    """
    Construye indices de propiedades por ID y por fila.

    Args:
        rows: Lista de filas del sheet

    Returns:
        tuple: (id_to_fila, fila_to_info)
            - id_to_fila: {prop_id: fila}
            - fila_to_info: {fila: {direccion, barrio, link, prop_id}}
    """
    id_to_fila = {}
    fila_to_info = {}

    for row in rows:
        fila = int(row.get('_row') or 0)
        link = row.get('link', '')
        if fila >= 2 and link.startswith('http'):
            prop_id = extraer_id_propiedad(link)
            if prop_id:
                id_to_fila[prop_id] = fila
                fila_to_info[fila] = {
                    'direccion': row.get('direccion', ''),
                    'barrio': row.get('barrio', ''),
                    'link': link,
                    'prop_id': prop_id,
                }

    return id_to_fila, fila_to_info


def extract_id_from_pdf(filepath):
    """
    Extrae ID de propiedad del contenido de un PDF.

    Usa pdftotext para extraer texto y busca patrones de MercadoLibre y Argenprop.

    Args:
        filepath: Path al archivo PDF

    Returns:
        str o None: ID extraido (MLA123 o AP123) o None si no se encontro
    """
    try:
        result = subprocess.run(
            ['pdftotext', '-l', '2', str(filepath), '-'],
            capture_output=True, text=True, timeout=10
        )
        contenido = result.stdout

        # MercadoLibre: MLA-123456789 o MLA123456789
        meli_match = re.search(r'MLA-?(\d{8,12})', contenido, re.IGNORECASE)
        if meli_match:
            return f"MLA{meli_match.group(1)}"

        # MercadoLibre alternativo: "Publicación #2539332096"
        pub_match = re.search(r'[Pp]ublicaci[oó]n\s*#\s*(\d{8,12})', contenido)
        if pub_match:
            return f"MLA{pub_match.group(1)}"

        # Argenprop: URLs con --123456
        argenprop_match = re.search(r'argenprop\.com[^\s]*--(\d+)', contenido)
        if argenprop_match:
            return f"AP{argenprop_match.group(1)}"

        # Buscar por URL directa
        url_match = re.search(r'(https?://[^\s]+(?:mercadolibre|argenprop)[^\s]+)', contenido)
        if url_match:
            return extraer_id_propiedad(url_match.group(1))

        return None

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_pending_print_files(nuevos_dir):
    """
    Lista archivos de print pendientes de procesar.

    Args:
        nuevos_dir: Path al directorio de archivos nuevos

    Returns:
        list: Lista de Paths a archivos validos
    """
    if not nuevos_dir.exists():
        return []

    archivos = []
    for f in nuevos_dir.iterdir():
        if not f.is_file():
            continue
        if f.suffix.lower() not in PRINT_EXTENSIONS:
            continue
        if f.name.startswith('.'):
            continue
        archivos.append(f)

    return archivos


def process_print_file(archivo, id_to_fila, fila_to_info, prints_dir=None):
    """
    Procesa un archivo de print: extrae ID, busca match y renombra.

    Args:
        archivo: Path al archivo a procesar
        id_to_fila: Dict {prop_id: fila}
        fila_to_info: Dict {fila: info}
        prints_dir: Directorio destino (default: PRINTS_DIR)

    Returns:
        dict o None: Info del archivo procesado o None si no hubo match
            - archivo_original: nombre original
            - archivo_nuevo: nombre nuevo
            - fila: numero de fila
            - prop_id: ID de propiedad
            - direccion: direccion de la propiedad
    """
    if prints_dir is None:
        prints_dir = PRINTS_DIR

    prop_id = None

    # Extraer ID del PDF
    if archivo.suffix.lower() == '.pdf':
        prop_id = extract_id_from_pdf(archivo)

    # Buscar fila correspondiente
    if prop_id and prop_id in id_to_fila:
        fila = id_to_fila[prop_id]
        info = fila_to_info[fila]

        # Generar nuevo nombre y mover
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        nuevo_nombre = f"{prop_id}_{fecha_hoy}{archivo.suffix.lower()}"
        nuevo_path = prints_dir / nuevo_nombre
        archivo.rename(nuevo_path)

        return {
            'archivo_original': archivo.name,
            'archivo_nuevo': nuevo_nombre,
            'fila': fila,
            'prop_id': prop_id,
            'direccion': info['direccion'],
        }

    return None


def get_orphan_prints(prints_index, filas_activas, prints_dir=None):
    """
    Detecta prints huerfanos (de propiedades inactivas o sin asociar).

    Args:
        prints_index: Indice de prints {fila: info}
        filas_activas: Set de filas activas
        prints_dir: Directorio de prints

    Returns:
        list: Lista de nombres de archivos huerfanos
    """
    if prints_dir is None:
        prints_dir = PRINTS_DIR

    if not prints_dir.exists():
        return []

    huerfanos = []
    for f in prints_dir.iterdir():
        if not f.is_file() or f.suffix.lower() not in PRINT_EXTENSIONS:
            continue
        if f.name.startswith('.') or f.name in ['index.json', 'pendientes.json']:
            continue

        # Ver si esta asociado a alguna fila activa
        asociado = False
        for fila, info in prints_index.items():
            if info.get('archivo') == f.name and fila in filas_activas:
                asociado = True
                break

        if not asociado:
            huerfanos.append(f.name)

    return huerfanos


def save_prints_index(clasificacion, prints_index, huerfanos, prints_index_path):
    """
    Guarda el indice de prints en formato JSON.

    Args:
        clasificacion: Dict de clasificar_prints()
        prints_index: Indice de prints
        huerfanos: Lista de prints huerfanos
        prints_index_path: Path donde guardar el JSON
    """
    import json

    prints_index_path.parent.mkdir(parents=True, exist_ok=True)

    index_output = {
        'generado': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total_activas': len(clasificacion['activas']),
        'con_print': len(clasificacion['con_print']),
        'sin_print': len(clasificacion['sin_print']),
        'vencidos': len(clasificacion['vencidos']),
        'huerfanos': len(huerfanos),
        'dias_vencimiento': PRINT_DIAS_VENCIMIENTO,
        'prints': {str(k): v for k, v in prints_index.items()}
    }

    with open(prints_index_path, 'w', encoding='utf-8') as f:
        json.dump(index_output, f, ensure_ascii=False, indent=2)


# =============================================================================
# EXTRACCIÓN DE DATOS DE PDFs
# =============================================================================

def extraer_texto_pdf(filepath, max_pages=5):
    """
    Extrae texto de un PDF usando pdftotext.

    Args:
        filepath: Path al archivo PDF
        max_pages: Máximo de páginas a extraer (default: 3)

    Returns:
        str: Texto extraído o string vacío si falla
    """
    try:
        result = subprocess.run(
            ['pdftotext', '-l', str(max_pages), str(filepath), '-'],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ''


def extraer_numero(texto):
    """
    Extrae número de un texto (maneja puntos y comas como separadores).

    Args:
        texto: String con número (ej: "1.500.000", "75,5", "USD 180000")

    Returns:
        float o None
    """
    if not texto:
        return None
    # Quitar todo excepto dígitos, puntos, comas
    limpio = re.sub(r'[^\d.,]', '', texto)
    if not limpio:
        return None

    # Si tiene coma decimal (ej: 75,5)
    if ',' in limpio and '.' not in limpio:
        limpio = limpio.replace(',', '.')
    # Si tiene puntos como separador de miles (ej: 1.500.000)
    elif '.' in limpio:
        partes = limpio.split('.')
        if len(partes) > 2 or (len(partes) == 2 and len(partes[-1]) == 3):
            limpio = limpio.replace('.', '')

    try:
        return float(limpio)
    except ValueError:
        return None


# =============================================================================
# EXTRACTORES DE DATOS PDF - Funciones auxiliares
# =============================================================================

def _extraer_precio_pdf(texto_lower, texto_original):
    """Extrae precio y moneda del texto del PDF."""
    data = {}
    # USD 180.000 / U$S 180000 / US$ 180.000
    precio_usd = re.search(
        r'(?:u[s$]+|usd)\s*[\$]?\s*([\d.,]+)',
        texto_lower
    )
    if precio_usd:
        data['precio'] = extraer_numero(precio_usd.group(1))
        data['moneda'] = 'USD'
    else:
        # $ 180.000.000 (pesos)
        precio_ars = re.search(r'\$\s*([\d.,]+)', texto_original)
        if precio_ars:
            num = extraer_numero(precio_ars.group(1))
            if num and num > 50000:  # Probablemente pesos
                data['precio'] = num
                data['moneda'] = 'ARS'
    return data


def _extraer_m2_pdf(texto_lower):
    """Extrae metros cuadrados (cubiertos, descubiertos, totales) del texto."""
    data = {}
    # Sup. Cubierta: 58 m2 / Superficie cubierta: 58m²
    m2_cub_match = re.search(
        r'(?:sup(?:\.|erficie)?\.?\s*)?cubierta[:\s]*([\d.,]+)\s*m',
        texto_lower
    )
    if m2_cub_match:
        data['m2_cub'] = extraer_numero(m2_cub_match.group(1))

    # Sup. Descubierta: 4,50 m2
    m2_desc_match = re.search(
        r'(?:sup(?:\.|erficie)?\.?\s*)?descubierta[:\s]*([\d.,]+)\s*m',
        texto_lower
    )
    if m2_desc_match:
        data['m2_desc'] = extraer_numero(m2_desc_match.group(1))

    # Sup. Total: 59,50 m2 / Superficie total: 62m²
    m2_tot_match = re.search(
        r'(?:sup(?:\.|erficie)?\.?\s*)?total[:\s]*([\d.,]+)\s*m',
        texto_lower
    )
    if m2_tot_match:
        data['m2_tot'] = extraer_numero(m2_tot_match.group(1))

    # Fallback: "XX m²" genérico si no encontramos específicos
    if 'm2_tot' not in data and 'm2_cub' not in data:
        m2_generico = re.search(r'(\d+)\s*m[²2]', texto_lower)
        if m2_generico:
            data['m2_tot'] = float(m2_generico.group(1))

    return data


def _extraer_expensas_pdf(texto_lower):
    """Extrae valor de expensas del texto."""
    # Expensas: $ 107.000 / Expensas $107000
    exp_match = re.search(
        r'expensas[:\s]*\$?\s*([\d.,]+)',
        texto_lower
    )
    if exp_match:
        exp_val = extraer_numero(exp_match.group(1))
        if exp_val:
            # Normalizar a pesos completos
            if exp_val < 1000:
                exp_val = exp_val * 1000
            return {'expensas': int(exp_val)}
    return {}


def _extraer_ambientes_pdf(texto_lower):
    """Extrae cantidad de ambientes y dormitorios del texto."""
    data = {}
    # Priorizar dato estructurado de MercadoLibre: línea con "Ambientes" y número
    amb_match = re.search(r'(?:^|\n)\s*ambientes\s+(\d{1,2})(?:\s|$)', texto_lower, re.MULTILINE)
    if amb_match:
        data['amb'] = int(amb_match.group(1))
    else:
        # Fallback: "3 ambientes" o "3 amb" en descripción
        amb_match = re.search(r'(\d{1,2})\s*amb(?:ientes)?(?:\s|\.|\,|$)', texto_lower)
        if amb_match:
            data['amb'] = int(amb_match.group(1))

    # Dormitorios / Habitaciones
    dorm_match = re.search(
        r'(?:dormitorios?|habitaciones?)[:\s]*(\d+)',
        texto_lower
    )
    if dorm_match:
        data['dormitorios'] = int(dorm_match.group(1))

    return data


def _extraer_banos_pdf(texto_lower):
    """Extrae cantidad de baños del texto."""
    # Patrón más específico: "baños: 2" o "2 baños"
    banos_match = re.search(r'baños?\s*[:\s]\s*(\d+)', texto_lower)
    if not banos_match:
        banos_match = re.search(r'(\d+)\s*baños?', texto_lower)
    if banos_match:
        num_banos = int(banos_match.group(1))
        # Sanity check: máximo 10 baños (evita capturar m²)
        if num_banos <= 10:
            return {'banos': num_banos}
    return {}


def _extraer_cochera_pdf(texto_lower):
    """Extrae información de cochera del texto."""
    data = {}
    if re.search(r'cochera|garage|estacionamiento', texto_lower):
        # Primero buscar cantidad: "cocheras: 0" = no tiene
        coch_num = re.search(r'cocheras?[:\s]*(\d+)', texto_lower)
        if coch_num:
            data['cocheras'] = int(coch_num.group(1))
        # Verificar negaciones explícitas
        elif re.search(r'sin\s+cochera|no\s+(?:tiene\s+)?cochera|cochera[:\s]*no', texto_lower):
            data['cocheras'] = 0
        # Si menciona cochera sin número ni negación, asumir que tiene 1
        elif re.search(r'con\s+cochera|c/cochera|tiene\s+cochera', texto_lower):
            data['cocheras'] = 1
    return data


def _extraer_terraza_balcon_patio_pdf(texto_lower, texto_original):
    """Extrae información de terraza, balcón y patio del texto."""
    from .helpers import detectar_atributo

    data = {}
    # Tipo de balcón: Terraza → es balcón, no terraza
    if re.search(r'tipo\s+de\s+balc[oó]n[:\s]*terraza', texto_lower):
        data['balcon'] = 'si'
    else:
        # Terraza real
        result = detectar_atributo(texto_original, 'terraza')
        if result:
            data['terraza'] = result

        # Balcón
        result = detectar_atributo(texto_original, 'balcon')
        if result:
            data['balcon'] = result

    # Patio
    result = detectar_atributo(texto_original, 'patio')
    if result:
        data['patio'] = result

    return data


def _extraer_antiguedad_pdf(texto_lower):
    """Extrae antigüedad del inmueble del texto."""
    antig_match = re.search(r'antig[üu]edad[:\s]*(\d+)', texto_lower)
    if antig_match:
        return {'antiguedad': int(antig_match.group(1))}
    # Solo si dice explícitamente "a estrenar" como atributo
    if re.search(r'(?:^|\n)\s*a\s+estrenar\s*(?:\n|$)|antig[üu]edad[:\s]*(?:a\s+estrenar|0)', texto_lower):
        return {'antiguedad': 0}
    return {}


def _extraer_disposicion_pdf(texto_lower):
    """Extrae disposición (frente/contrafrente) del texto."""
    if re.search(r'disposici[oó]n[:\s]*frente|orientaci[oó]n[:\s]*frente', texto_lower):
        return {'disposicion': 'frente'}
    if re.search(r'disposici[oó]n[:\s]*contrafrente', texto_lower):
        return {'disposicion': 'contrafrente'}
    return {}


def _extraer_estado_pdf(texto_lower):
    """Extrae estado del inmueble del texto."""
    estado_match = re.search(
        r'(?:estado(?:\s+del\s+inmueble)?|condici[oó]n)[:\s]*(a\s+estrenar|usado|buen(?:\s+estado)?|muy\s+buen(?:\s+estado)?|excelente|a\s+reciclar|a\s+refaccionar|reciclado|en\s+construcci[oó]n)',
        texto_lower
    )
    if estado_match:
        val = estado_match.group(1).strip().title()
        # Normalizar valores comunes
        if val.lower() == 'buen':
            val = 'Buen Estado'
        elif val.lower() == 'muy buen':
            val = 'Muy Buen Estado'
        return {'estado': val}
    return {}


def _extraer_atributos_si_no_pdf(texto_lower, texto_original):
    """Extrae atributos booleanos: luminosidad, apto crédito, ascensor."""
    from .helpers import detectar_atributo

    data = {}

    # LUMINOSIDAD
    result = detectar_atributo(texto_original, 'luminosidad')
    if result:
        data['luminosidad'] = result

    # APTO CRÉDITO - Buscar primero patrón estructurado
    apto_match = re.search(r'apto\s+cr[eé]dito\s+([sn][ioí])', texto_lower)
    if apto_match:
        val = apto_match.group(1).lower()
        data['apto_credito'] = 'si' if val.startswith('s') else 'no'
    else:
        result = detectar_atributo(texto_original, 'apto_credito')
        if result:
            data['apto_credito'] = result

    # ASCENSOR - Buscar primero patrón estructurado
    asc_match = re.search(r'ascensor\s+([sn][ioí])', texto_lower)
    if asc_match:
        val = asc_match.group(1).lower()
        data['ascensor'] = 'si' if val.startswith('s') else 'no'
    else:
        result = detectar_atributo(texto_original, 'ascensor')
        if result:
            data['ascensor'] = result

    return data


def _extraer_id_propiedad_pdf(texto_original):
    """Extrae ID de propiedad para verificación."""
    # MercadoLibre: MLA-123456789
    meli_match = re.search(r'MLA-?(\d{8,12})', texto_original, re.IGNORECASE)
    if meli_match:
        return {'_prop_id': f"MLA{meli_match.group(1)}"}

    # MercadoLibre alternativo: "Publicación #2539332096"
    pub_match = re.search(r'[Pp]ublicaci[oó]n\s*#\s*(\d{8,12})', texto_original)
    if pub_match:
        return {'_prop_id': f"MLA{pub_match.group(1)}"}

    # Argenprop
    argenprop_match = re.search(r'argenprop\.com[^\s]*--(\d+)', texto_original)
    if argenprop_match:
        return {'_prop_id': f"AP{argenprop_match.group(1)}"}

    return {}


def extraer_datos_pdf(filepath):
    """
    Extrae datos de propiedad de un PDF de aviso inmobiliario.

    Busca patrones comunes de MercadoLibre, Argenprop y Zonaprop.

    Args:
        filepath: Path al archivo PDF

    Returns:
        dict: Datos extraídos {precio, moneda, m2_tot, m2_cub, m2_desc,
              expensas, ambientes, banos, terraza, balcon, patio, cochera, ...}
    """
    texto_completo = extraer_texto_pdf(filepath)
    if not texto_completo:
        return {}

    # Filtrar texto: solo usar contenido ANTES del sidebar de propiedades sugeridas
    cortes = [
        'estas propiedades también podrían interesarte',
        'propiedades similares',
        'te puede interesar',
    ]
    texto = texto_completo
    texto_check = texto_completo.lower()
    for corte in cortes:
        idx = texto_check.find(corte)
        if idx > PDF_MIN_CONTENT_LENGTH:
            texto = texto_completo[:idx]
            break

    texto_lower = texto.lower()

    # Extraer datos usando funciones auxiliares
    data = {}
    data.update(_extraer_precio_pdf(texto_lower, texto))
    data.update(_extraer_m2_pdf(texto_lower))
    data.update(_extraer_expensas_pdf(texto_lower))
    data.update(_extraer_ambientes_pdf(texto_lower))
    data.update(_extraer_banos_pdf(texto_lower))
    data.update(_extraer_cochera_pdf(texto_lower))
    data.update(_extraer_terraza_balcon_patio_pdf(texto_lower, texto))
    data.update(_extraer_antiguedad_pdf(texto_lower))
    data.update(_extraer_disposicion_pdf(texto_lower))
    data.update(_extraer_estado_pdf(texto_lower))
    data.update(_extraer_atributos_si_no_pdf(texto_lower, texto))
    data.update(_extraer_id_propiedad_pdf(texto))

    return data


def validar_datos_pdf_vs_sheet(datos_pdf, datos_sheet):
    """
    Compara datos extraídos del PDF con datos del sheet.

    Args:
        datos_pdf: Dict con datos extraídos del PDF
        datos_sheet: Dict con datos de la fila del sheet

    Returns:
        dict: {coincidencias: [], discrepancias: [], faltantes_pdf: [], faltantes_sheet: []}
    """
    resultado = {
        'coincidencias': [],
        'discrepancias': [],
        'faltantes_pdf': [],
        'faltantes_sheet': [],
    }

    # Campos a comparar y tolerancias
    campos_numericos = {
        'precio': 0.01,      # 1% tolerancia
        'm2_tot': 2,         # 2 m² tolerancia
        'm2_cub': 2,
        'm2_desc': 2,
        'expensas': 5000,    # $5000 tolerancia
        'amb': 0,
        'banos': 0,
        'antiguedad': 1,     # 1 año tolerancia
        'cocheras': 0,
    }

    campos_texto = ['terraza', 'balcon', 'patio', 'luminosidad', 'disposicion']

    # Comparar campos numéricos
    for campo, tolerancia in campos_numericos.items():
        pdf_val = datos_pdf.get(campo)
        sheet_val = datos_sheet.get(campo)

        # Convertir sheet_val a número si es string
        if isinstance(sheet_val, str):
            sheet_val = extraer_numero(sheet_val)

        if pdf_val is None and sheet_val is None:
            continue
        elif pdf_val is None:
            resultado['faltantes_pdf'].append(campo)
        elif sheet_val is None:
            resultado['faltantes_sheet'].append(campo)
        else:
            # Comparar con tolerancia
            if tolerancia > 0 and tolerancia < 1:
                # Tolerancia porcentual
                diff = abs(pdf_val - sheet_val) / max(pdf_val, sheet_val, 1)
                if diff <= tolerancia:
                    resultado['coincidencias'].append(campo)
                else:
                    resultado['discrepancias'].append({
                        'campo': campo,
                        'pdf': pdf_val,
                        'sheet': sheet_val,
                        'diff': f"{diff*100:.1f}%"
                    })
            else:
                # Tolerancia absoluta
                if abs(pdf_val - sheet_val) <= tolerancia:
                    resultado['coincidencias'].append(campo)
                else:
                    resultado['discrepancias'].append({
                        'campo': campo,
                        'pdf': pdf_val,
                        'sheet': sheet_val,
                        'diff': abs(pdf_val - sheet_val)
                    })

    # Comparar campos de texto
    for campo in campos_texto:
        pdf_val = (datos_pdf.get(campo) or '').lower()
        sheet_val = (datos_sheet.get(campo) or '').lower()

        if not pdf_val and not sheet_val:
            continue
        elif not pdf_val:
            resultado['faltantes_pdf'].append(campo)
        elif not sheet_val:
            resultado['faltantes_sheet'].append(campo)
        elif pdf_val == sheet_val:
            resultado['coincidencias'].append(campo)
        else:
            resultado['discrepancias'].append({
                'campo': campo,
                'pdf': pdf_val,
                'sheet': sheet_val
            })

    return resultado


def comparar_tres_fuentes(campo, val_sheet, val_web, val_pdf):
    """
    Compara un campo entre las 3 fuentes y determina la acción recomendada.

    Args:
        campo: Nombre del campo
        val_sheet: Valor en el sheet (string o None)
        val_web: Valor del web cache (string o None)
        val_pdf: Valor del PDF (string o None)

    Returns:
        dict con:
            - sheet: valor en sheet
            - web: valor en web cache
            - pdf: valor en PDF
            - accion: 'ok', 'importar', 'solo_pdf', 'solo_web', 'revisar', 'desactualizado'
            - confianza: 'alta', 'media', 'baja'
            - valor_sugerido: valor a importar (si aplica)
    """
    # Función para normalizar valores booleanos/numéricos
    def normalizar(val, campo):
        if not val:
            return ''
        v = str(val).strip().lower()

        # Normalizar cocheras: 0="no", 1+="si"
        if campo == 'cocheras':
            if v in ('0', 'no', 'sin'):
                return 'no'
            elif v in ('si', 'sí') or (v.isdigit() and int(v) > 0):
                return 'si'

        # Normalizar expensas: tratar 128 como 128000 (miles)
        if campo == 'expensas':
            try:
                num = float(v.replace('.', '').replace(',', '.'))
                # Si es < 1000, probablemente está en miles
                if num < 1000:
                    num = num * 1000
                return str(int(num))
            except ValueError:
                pass

        return v

    # Función para comparar valores con tolerancia numérica
    def valores_iguales(v1, v2, campo):
        if v1 == v2:
            return True
        # Tolerancia numérica para expensas (2%)
        if campo == 'expensas':
            try:
                n1, n2 = float(v1), float(v2)
                if max(n1, n2) > 0:
                    diff_pct = abs(n1 - n2) / max(n1, n2)
                    return diff_pct < 0.02  # 2% tolerancia
            except (ValueError, TypeError):
                pass
        return False

    # Normalizar valores
    s = normalizar(val_sheet, campo)
    w = normalizar(val_web, campo)
    p = normalizar(val_pdf, campo)

    result = {
        'sheet': val_sheet or '',
        'web': val_web or '',
        'pdf': val_pdf or '',
        'accion': 'ok',
        'confianza': 'alta',
        'valor_sugerido': None,
    }

    # Caso 1: Sheet vacío
    if not s:
        if w and p and valores_iguales(w, p, campo):
            # Web y PDF coinciden → alta confianza
            result['accion'] = 'importar'
            result['confianza'] = 'alta'
            result['valor_sugerido'] = val_web or val_pdf
        elif p and not w:
            # Solo PDF tiene dato
            result['accion'] = 'solo_pdf'
            result['confianza'] = 'media'
            result['valor_sugerido'] = val_pdf
        elif w and not p:
            # Solo Web tiene dato
            result['accion'] = 'solo_web'
            result['confianza'] = 'media'
            result['valor_sugerido'] = val_web
        elif w and p and not valores_iguales(w, p, campo):
            # Web y PDF difieren → revisar
            result['accion'] = 'revisar'
            result['confianza'] = 'baja'
        # else: ambos vacíos, no hacer nada

    # Caso 2: Sheet tiene valor
    else:
        if w and p:
            if valores_iguales(s, w, campo) and valores_iguales(w, p, campo):
                # Todos coinciden → OK
                result['accion'] = 'ok'
            elif valores_iguales(w, p, campo) and not valores_iguales(s, w, campo):
                # Web y PDF coinciden pero sheet difiere → desactualizado
                result['accion'] = 'desactualizado'
                result['confianza'] = 'alta'
                result['valor_sugerido'] = val_web or val_pdf
            else:
                # Los 3 difieren → revisar
                result['accion'] = 'revisar'
                result['confianza'] = 'baja'
        elif w and not valores_iguales(s, w, campo):
            result['accion'] = 'revisar'
            result['confianza'] = 'media'
        elif p and not valores_iguales(s, p, campo):
            result['accion'] = 'revisar'
            result['confianza'] = 'media'
        # else: sheet coincide con lo que hay

    return result


def analizar_tres_fuentes(rows, prints_dir=None, cache=None):
    """
    Analiza todas las propiedades comparando Sheet vs Web Cache vs PDF.

    Args:
        rows: Lista de filas del sheet
        prints_dir: Directorio de prints (opcional)
        cache: Cache del web scraper (opcional, se carga si no se pasa)

    Returns:
        list: Lista de resultados por propiedad
    """
    from .storage import get_cache_for_url, load_cache

    if prints_dir is None:
        prints_dir = PRINTS_DIR

    if cache is None:
        cache = load_cache()

    prints_index = get_prints_index(rows, prints_dir)
    resultados = []

    # Campos a comparar (nombres del sheet)
    campos = ['terraza', 'balcon', 'patio', 'cocheras', 'luminosidad', 'amb',
              'banos', 'antiguedad', 'expensas', 'disposicion', 'ascensor', 'apto_credito']

    # Mapeo de nombres: todos los scrapers ahora usan los mismos nombres que el sheet
    pdf_field_map = {}

    for row in rows:
        fila = int(row.get('_row') or 0)
        if fila < 2:
            continue

        link = row.get('link', '')
        if not link.startswith('http'):
            continue

        # Obtener datos del cache
        cache_info = get_cache_for_url(link, cache)
        datos_web = cache_info['data'] or {}
        web_age = cache_info['age_days']
        web_stale = cache_info['is_stale']

        # Obtener datos del PDF
        print_info = prints_index.get(fila)
        datos_pdf = {}
        if print_info:
            archivo = prints_dir / print_info['archivo']
            if archivo.exists() and archivo.suffix.lower() == '.pdf':
                datos_pdf = extraer_datos_pdf(archivo)

        # Comparar cada campo
        comparaciones = []
        hay_diferencias = False

        for campo in campos:
            val_sheet = row.get(campo)
            val_web = datos_web.get(campo)
            # Para PDF, usar el nombre mapeado si existe
            pdf_campo = pdf_field_map.get(campo, campo)
            val_pdf = datos_pdf.get(pdf_campo)

            comp = comparar_tres_fuentes(campo, val_sheet, val_web, val_pdf)
            comp['campo'] = campo

            if comp['accion'] != 'ok':
                hay_diferencias = True

            # Solo incluir si hay algo que mostrar
            if val_sheet or val_web or val_pdf:
                comparaciones.append(comp)

        if hay_diferencias or comparaciones:
            resultados.append({
                'fila': fila,
                'direccion': row.get('direccion', ''),
                'link': link,
                'web_age': web_age,
                'web_stale': web_stale,
                'tiene_pdf': bool(print_info),
                'comparaciones': comparaciones,
            })

    return resultados


def analizar_prints_vs_sheet(rows, prints_dir=None):
    """
    Analiza todos los prints disponibles y compara con datos del sheet.

    Args:
        rows: Lista de filas del sheet
        prints_dir: Directorio de prints (opcional)

    Returns:
        list: Lista de resultados por propiedad con discrepancias
    """
    if prints_dir is None:
        prints_dir = PRINTS_DIR

    prints_index = get_prints_index(rows, prints_dir)
    resultados = []

    for row in rows:
        fila = int(row.get('_row') or 0)
        if fila < 2:
            continue

        print_info = prints_index.get(fila)
        if not print_info:
            continue

        archivo = prints_dir / print_info['archivo']
        if not archivo.exists() or archivo.suffix.lower() != '.pdf':
            continue

        # Extraer datos del PDF
        datos_pdf = extraer_datos_pdf(archivo)
        if not datos_pdf:
            continue

        # Comparar con sheet
        validacion = validar_datos_pdf_vs_sheet(datos_pdf, row)

        # Solo reportar si hay discrepancias o faltantes
        if validacion['discrepancias'] or validacion['faltantes_sheet']:
            resultados.append({
                'fila': fila,
                'direccion': row.get('direccion', ''),
                'archivo': print_info['archivo'],
                'validacion': validacion,
                'datos_pdf': datos_pdf,
            })

    return resultados
