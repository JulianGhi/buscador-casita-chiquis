"""
Sistema de validaciones y warnings.

Incluye:
- Acumulación de warnings durante scraping
- Validación de propiedades
- Impresión de resumen
"""

from .helpers import extraer_m2

# =============================================================================
# CONSTANTES DE VALIDACIÓN
# =============================================================================

# Umbrales de precio (USD) para detectar precios sospechosos
PRECIO_MINIMO_RAZONABLE = 30000   # < este valor = muy bajo para CABA
PRECIO_MAXIMO_RAZONABLE = 500000  # > este valor = muy alto para depto

# =============================================================================
# SISTEMA DE WARNINGS
# =============================================================================

# Lista global de warnings (se limpia con clear_warnings)
_warnings = []


def add_warning(tipo, mensaje, propiedad=None):
    """Agrega un warning a la lista para revisión."""
    _warnings.append({
        'tipo': tipo,
        'mensaje': mensaje,
        'propiedad': propiedad,
    })


def clear_warnings():
    """Limpia la lista de warnings."""
    global _warnings
    _warnings = []


def get_warnings():
    """Retorna la lista de warnings (para tests)."""
    return _warnings


def print_warnings_summary():
    """Imprime resumen de warnings al final del scrape."""
    if not _warnings:
        print("\n✅ Sin warnings - todos los datos pasaron validación")
        return

    print(f"\n{'='*60}")
    print(f"⚠️  RESUMEN DE WARNINGS ({len(_warnings)} items)")
    print(f"{'='*60}")

    # Agrupar por tipo
    by_type = {}
    for w in _warnings:
        tipo = w['tipo']
        if tipo not in by_type:
            by_type[tipo] = []
        by_type[tipo].append(w)

    for tipo, warnings in by_type.items():
        print(f"\n📋 {tipo.upper()} ({len(warnings)}):")
        for w in warnings[:10]:  # Mostrar max 10 por tipo
            prop = w['propiedad'] or ''
            print(f"   • {w['mensaje']} {prop}")
        if len(warnings) > 10:
            print(f"   ... y {len(warnings) - 10} más")

    print(f"\n{'='*60}")


# =============================================================================
# VALIDACIÓN DE PROPIEDADES
# =============================================================================

def validar_propiedad(data, contexto=None):
    """
    Valida los datos de una propiedad y agrega warnings si hay problemas.

    Args:
        data: dict con los datos scrapeados
        contexto: string para identificar la propiedad (dirección o link)
    """
    ctx = contexto or data.get('direccion', data.get('link', '?'))[:50]

    # Validar m² (cub + desc = tot)
    m2_cub, m2_tot, m2_desc = extraer_m2(data)

    if m2_cub > 0 and m2_tot > 0:
        if m2_cub > m2_tot:
            add_warning('m2_inconsistente', f"m² cub ({m2_cub}) > m² tot ({m2_tot})", ctx)
        elif m2_desc > 0:
            esperado = m2_cub + m2_desc
            if esperado != m2_tot and abs(esperado - m2_tot) > 2:  # tolerancia de 2m²
                add_warning('m2_no_cierra', f"cub({m2_cub}) + desc({m2_desc}) = {esperado} ≠ tot({m2_tot})", ctx)

    # Validar precio sospechoso
    precio = int(data.get('precio') or 0)
    if precio > 0:
        if precio < PRECIO_MINIMO_RAZONABLE:
            add_warning('precio_bajo', f"Precio muy bajo: ${precio:,}", ctx)
        elif precio > PRECIO_MAXIMO_RAZONABLE:
            add_warning('precio_alto', f"Precio muy alto: ${precio:,}", ctx)

    # Validar atributos inciertos
    for attr in ['terraza', 'balcon', 'apto_credito', 'ascensor']:
        if data.get(attr) == '?':
            add_warning('atributo_incierto', f"{attr}=? (revisar manualmente)", ctx)

    # Validar campos importantes faltantes
    if not data.get('barrio'):
        add_warning('dato_faltante', "Sin barrio", ctx)
    if not data.get('m2_cub') and not data.get('m2_tot'):
        add_warning('dato_faltante', "Sin m²", ctx)

    # Validar balcón/terraza vs m2_desc
    balcon = (data.get('balcon') or '').lower()
    terraza = (data.get('terraza') or '').lower()
    tiene_exterior = balcon == 'si' or terraza == 'si'
    if tiene_exterior and m2_desc <= 0:
        exterior = []
        if balcon == 'si':
            exterior.append('balcón')
        if terraza == 'si':
            exterior.append('terraza')
        add_warning('m2_desc_inconsistente', f"Tiene {'+'.join(exterior)} pero m²_desc={m2_desc}", ctx)


# =============================================================================
# DETECCION DE DATOS FALTANTES
# =============================================================================

def get_missing_fields(row, campos_importantes):
    """
    Detecta campos importantes faltantes en una fila.

    Args:
        row: Dict con datos de la fila
        campos_importantes: Lista de campos a verificar

    Returns:
        list: Lista de nombres de campos faltantes
    """
    missing = []
    for campo in campos_importantes:
        valor = (row.get(campo) or '').strip().lower()
        if not valor or valor == '?':
            missing.append(campo)
    return missing


def get_properties_with_missing_data(rows, campos_importantes, prints_index=None, solo_sin_print=False):
    """
    Filtra propiedades activas con datos faltantes.

    Args:
        rows: Lista de filas del sheet
        campos_importantes: Lista de campos importantes a verificar
        prints_index: Indice de prints (opcional)
        solo_sin_print: Si True, solo incluye propiedades sin print

    Returns:
        list: Lista de dicts con info de propiedades pendientes, ordenada por cantidad de faltantes
    """
    if prints_index is None:
        prints_index = {}

    pendientes = []
    for row in rows:
        fila = row.get('_row', 0)
        if fila < 2:
            continue

        # Solo activas
        activo = (row.get('activo') or '').lower()
        if activo == 'no':
            continue

        # Solo con link
        link = row.get('link', '')
        if not link.startswith('http'):
            continue

        # Detectar campos faltantes
        missing = get_missing_fields(row, campos_importantes)
        if not missing:
            continue

        print_info = prints_index.get(fila)
        tiene_print = print_info is not None

        # Filtrar por print si se pidio
        if solo_sin_print and tiene_print:
            continue

        pendientes.append({
            'fila': fila,
            'direccion': row.get('direccion', ''),
            'barrio': row.get('barrio', ''),
            'link': link,
            'missing': missing,
            'tiene_print': tiene_print,
            'print_info': print_info
        })

    # Ordenar por cantidad de datos faltantes (mas incompletos primero)
    pendientes.sort(key=lambda x: -len(x['missing']))
    return pendientes
