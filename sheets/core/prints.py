"""
Sistema de prints - Backup de publicaciones en PDF/PNG.

Funciones para gestionar screenshots/PDFs de avisos inmobiliarios.
"""

import re
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
        fila = row.get('_row', 0)
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

    # Agregar historial al indice
    for fila, info in prints_index.items():
        historial = prints_historial.get(fila, [])
        if len(historial) > 1:
            info['historial'] = sorted(historial, key=lambda x: x['fecha'], reverse=True)
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
        fila = row.get('_row', 0)
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
        fila = row.get('_row', 0)
        if fila in prints_index:
            fecha_print = prints_index[fila].get('fecha', '')
            if fecha_print and row.get('fecha_print', '') != fecha_print:
                row['fecha_print'] = fecha_print
                updated += 1

    return updated
