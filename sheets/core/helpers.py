"""
Funciones helper puras para sync_sheet.

Incluye:
- Extracción de datos (números, m², barrios, IDs)
- Detección de atributos booleanos
- Normalización de texto
"""

import re
import unicodedata


# =============================================================================
# CONSTANTES
# =============================================================================

# Barrios conocidos de CABA
BARRIOS_CABA = [
    # Zona Oeste (principal área de búsqueda)
    'Floresta', 'Flores', 'Caballito', 'Parque Chacabuco', 'Parque Avellaneda',
    'Villa Luro', 'Liniers', 'Mataderos', 'Villa Real', 'Versalles',
    'Vélez Sársfield', 'Velez Sarsfield',  # con y sin tilde
    'Monte Castro', 'Villa del Parque', 'Villa Devoto', 'Villa Santa Rita',
    'Paternal', 'Villa General Mitre', 'Agronomía',
    # Zona Norte
    'Villa Crespo', 'Almagro', 'Villa Ortúzar', 'Chacarita', 'Colegiales',
    'Belgrano', 'Núñez', 'Saavedra', 'Villa Urquiza', 'Villa Pueyrredón', 'Coghlan',
    'Palermo', 'Recoleta',
    # Zona Centro/Sur
    'Retiro', 'San Nicolás', 'Monserrat', 'San Telmo', 'Constitución',
    'Barracas', 'La Boca', 'Boedo', 'San Cristóbal', 'Balvanera',
    'Once', 'Abasto',
]

# Patrones de detección para atributos booleanos
# - 'si': patrones que indican presencia
# - 'no': patrones que indican ausencia (se evalúan PRIMERO)
# - 'solo_label': si True, el label solo cuenta como 'si'
ATTR_PATTERNS = {
    'terraza': {
        'si': ['terraza: si', 'terraza: sí', 'terraza:si', 'terraza:sí', 'con terraza'],
        'no': ['terraza: no', 'terraza:no', 'sin terraza', 'no tiene terraza'],
        'solo_label': True,
    },
    'balcon': {
        'si': ['balcon: si', 'balcón: si', 'balcon: sí', 'balcón: sí', 'con balcon', 'con balcón'],
        'no': ['balcon: no', 'balcón: no', 'sin balcon', 'sin balcón', 'no tiene balcon', 'no tiene balcón'],
        'solo_label': True,
    },
    'cochera': {
        'si': ['cochera: si', 'cochera: sí', 'con cochera', 'tiene cochera'],
        'no': ['cochera: no', 'sin cochera', 'no tiene cochera', 'cocheras: 0', 'cochera: 0'],
        'solo_label': True,
    },
    'luminosidad': {
        'si': ['luminoso', 'muy luminoso', 'luz natural', 'buena luz', 'excelente luz'],
        'no': ['poco luminoso', 'no luminoso', 'no es luminoso', 'sin luz', 'oscuro', 'poca luz'],
        'solo_label': False,
    },
    'ascensor': {
        'si': ['ascensor: si', 'ascensor: sí', 'con ascensor', 'tiene ascensor'],
        'no': ['ascensor: no', 'sin ascensor', 'no tiene ascensor'],
        'solo_label': False,
    },
    'apto_credito': {
        'si': ['apto credito: si', 'apto crédito: si', 'apto credito: sí', 'apto crédito: sí',
               'apto banco', 'acepta credito', 'acepta crédito',
               'es apto credito', 'es apto crédito', 'apto credito', 'apto crédito'],
        'no': ['apto credito: no', 'apto crédito: no', 'no apto credito', 'no apto crédito',
               'no acepta credito', 'no acepta crédito', 'no es apto credito', 'no es apto crédito'],
        'solo_label': False,
    },
}


# =============================================================================
# FUNCIONES DE EXTRACCIÓN
# =============================================================================

def quitar_tildes(texto):
    """Quita tildes/acentos de un texto pero mantiene espacios y puntuación."""
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')


def extraer_numero(texto, quitar_miles=False):
    """Extrae el primer número de un texto, o None si no hay.

    Args:
        texto: Texto del que extraer el número
        quitar_miles: Si True, quita puntos de miles (ej: "150.000" → "150000")

    Returns:
        String con el número encontrado, o None si no hay
    """
    if not texto:
        return None
    texto = str(texto)
    if quitar_miles:
        texto = texto.replace('.', '')
    match = re.search(r'(\d+)', texto)
    return match.group(1) if match else None


def extraer_m2(data):
    """Extrae m2_cub, m2_tot, m2_desc de un dict como ints."""
    return (
        int(data.get('m2_cub') or 0),
        int(data.get('m2_tot') or 0),
        int(data.get('m2_desc') or 0),
    )


def detectar_barrio(texto):
    """Detecta barrio de CABA en un texto. Retorna el nombre o None."""
    if not texto:
        return None
    texto_lower = texto.lower()
    for barrio in BARRIOS_CABA:
        if barrio.lower() in texto_lower:
            return barrio
    return None


def extraer_id_propiedad(link):
    """Extrae ID de propiedad desde URL.

    Returns:
        - MLA123456789 para MercadoLibre
        - AP12345678 para Argenprop
        - ZP12345678 para Zonaprop
        - None si no matchea
    """
    if not link:
        return None

    # MercadoLibre: MLA-123456789 o MLA123456789
    meli = re.search(r'MLA-?(\d+)', link, re.IGNORECASE)
    if meli:
        return f"MLA{meli.group(1)}"

    # Argenprop: termina en --12345678
    argenprop = re.search(r'--(\d+)$', link)
    if argenprop:
        return f"AP{argenprop.group(1)}"

    # Zonaprop: termina en -12345678.html
    zonaprop = re.search(r'-(\d{8})\.html$', link)
    if zonaprop:
        return f"ZP{zonaprop.group(1)}"

    return None


# =============================================================================
# FUNCIONES DE FILTRADO
# =============================================================================

def get_active_rows(rows):
    """Filtra filas activas con links válidos.

    Returns:
        Lista de rows que cumplen:
        - _row >= 2 (no es header)
        - activo != 'no'
        - link empieza con 'http'
    """
    return [
        row for row in rows
        if row.get('_row', 0) >= 2
        and (row.get('activo') or '').lower() != 'no'
        and row.get('link', '').startswith('http')
    ]


# =============================================================================
# FUNCIONES DE CÁLCULO
# =============================================================================

def calcular_m2_faltantes(data):
    """
    Calcula m² faltantes si tenemos 2 de los 3 valores.

    Lógica: m2_tot = m2_cub + m2_desc

    Returns:
        dict con campos calculados (vacío si no se pudo calcular nada)
    """
    calculados = {}
    m2_cub, m2_tot, m2_desc = extraer_m2(data)

    # Si tenemos tot y cub pero no desc → calcular desc
    if m2_tot > 0 and m2_cub > 0 and m2_desc == 0:
        calculado = m2_tot - m2_cub
        if calculado >= 0:
            calculados['m2_desc'] = str(calculado)

    # Si tenemos tot y desc pero no cub → calcular cub
    elif m2_tot > 0 and m2_desc > 0 and m2_cub == 0:
        calculado = m2_tot - m2_desc
        if calculado > 0:
            calculados['m2_cub'] = str(calculado)

    # Si tenemos cub y desc pero no tot → calcular tot
    elif m2_cub > 0 and m2_desc > 0 and m2_tot == 0:
        calculados['m2_tot'] = str(m2_cub + m2_desc)

    return calculados


# =============================================================================
# DETECCIÓN DE ATRIBUTOS
# =============================================================================

def detectar_atributo(texto, atributo, warning_callback=None, contexto=None):
    """
    Detecta si un atributo está presente o ausente basado en patrones.

    Args:
        texto: string a analizar
        atributo: nombre del atributo ('terraza', 'balcon', etc.)
        warning_callback: función opcional para reportar warnings
        contexto: string opcional para identificar la propiedad

    Returns:
        'si': atributo presente
        'no': atributo ausente
        '?': atributo mencionado pero valor incierto
        None: atributo no mencionado
    """
    if atributo not in ATTR_PATTERNS:
        return None

    patterns = ATTR_PATTERNS[atributo]
    # Normalizar: minúsculas y sin tildes
    texto_lower = quitar_tildes(texto.lower())

    # Primero verificar patrones de negación
    for patron in patterns['no']:
        if patron in texto_lower:
            return 'no'

    # Luego verificar patrones positivos
    for patron in patterns['si']:
        if patron in texto_lower:
            return 'si'

    # Si solo_label está activo, verificar si el label aparece solo
    if patterns.get('solo_label') and atributo in texto_lower:
        return 'si'

    # Si el atributo está mencionado pero no matcheó ningún patrón → incierto
    if atributo in texto_lower:
        msg = f"'{texto[:60]}...'"
        if warning_callback:
            warning_callback('atributo_incierto', f"{atributo}=? en: {msg}", contexto)
        return '?'

    return None


# =============================================================================
# INFERENCIA DE VALORES FALTANTES
# =============================================================================

def inferir_valores_faltantes(row):
    """
    Infiere valores faltantes basado en reglas lógicas.

    Reglas:
    - status vacío → 'Por ver' (valor por defecto)
    - m2_desc = 0 → terraza=no, balcon=no (sin espacio descubierto)
    - tipo=ph + ascensor vacío → ascensor=no (PHs no tienen ascensor)
    - tipo=ph + cochera vacía → cochera=no (PHs raramente tienen)

    Args:
        row: dict con datos de la propiedad

    Returns:
        dict: campos inferidos {campo: valor}
    """
    inferidos = {}

    # Status por defecto
    if not row.get('status'):
        inferidos['status'] = 'Por ver'

    m2_desc = int(row.get('m2_desc') or 0)
    tipo = (row.get('tipo') or '').lower()

    # Sin espacio descubierto → sin terraza/balcon
    if m2_desc == 0:
        if not row.get('terraza'):
            inferidos['terraza'] = 'no'
        if not row.get('balcon'):
            inferidos['balcon'] = 'no'

    # PH → sin ascensor (son de 1-2 pisos)
    if tipo == 'ph' and not row.get('ascensor'):
        inferidos['ascensor'] = 'no'

    # PH → sin cochera (raramente tienen)
    if tipo == 'ph' and not row.get('cochera'):
        inferidos['cochera'] = 'no'

    return inferidos
