"""
Templates HTML para generacion de previews y reportes.

Separa la logica de presentacion del codigo de negocio.
"""

# =============================================================================
# CSS COMPARTIDO
# =============================================================================

PREVIEW_CSS = """
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
""".strip()


# =============================================================================
# COLUMNAS DEFAULT PARA PREVIEW
# =============================================================================

# Columnas a mostrar en el preview
PREVIEW_SHOW_COLS = ['direccion', 'barrio', 'precio', 'm2_cub', 'm2_tot', 'amb',
                     'expensas', 'terraza', 'apto_credito', 'status', 'activo', 'notas']

# Columnas que se comparan para detectar cambios
PREVIEW_DIFF_COLS = ['precio', 'm2_cub', 'm2_tot', 'amb']


# =============================================================================
# FUNCIONES DE GENERACION HTML
# =============================================================================

def format_column_label(col):
    """Formatea nombre de columna para mostrar en header."""
    return col.replace('_', ' ').replace('m2', 'm²').title()


def format_cell_value(value, col, is_empty=False):
    """
    Formatea valor de celda segun el tipo de columna.

    Args:
        value: Valor a formatear
        col: Nombre de la columna
        is_empty: Si el valor esta vacio

    Returns:
        tuple: (valor_formateado, css_class_adicional)
    """
    if is_empty or not value:
        return '-', 'empty-cell'

    value = str(value).strip()

    # Columnas booleanas
    if col in ['terraza', 'apto_credito', 'activo', 'balcon', 'cocheras']:
        if value.lower() == 'si':
            return '<span class="badge badge-yes">Si</span>', ''
        elif value.lower() == 'no':
            return '<span class="badge badge-no">No</span>', ''

    # Notas (truncar)
    if col == 'notas':
        if len(value) > 100:
            return value[:100] + '...', 'notes'
        return value, 'notes'

    return value, ''


def generate_link_cell(link_url, status=None):
    """
    Genera HTML para celda de link con estado.

    Args:
        link_url: URL del link
        status: Codigo de estado HTTP (None si no se verifico)

    Returns:
        str: HTML de la celda
    """
    if not link_url:
        return '<td class="empty-cell">-</td>'

    link_icon = ''
    if status is not None:
        if status == 200:
            link_icon = '<span class="online">OK</span>'
        elif status in [404, 410]:
            link_icon = f'<span class="offline">X {status}</span>'
        else:
            link_icon = f'<span class="unknown">? {status}</span>'

    return f'<td><a href="{link_url}" target="_blank">link</a> {link_icon}</td>'


def generate_preview_html(rows_data, stats, columns=None):
    """
    Genera HTML completo del preview.

    Args:
        rows_data: Lista de dicts con datos de cada fila:
            - fila: numero de fila
            - link: URL del aviso
            - link_status: codigo HTTP (opcional)
            - is_offline: bool
            - cells: lista de dicts {value, css_class}
        stats: Dict con estadisticas:
            - added_cells: celdas nuevas
            - modified_cells: celdas modificadas
            - offline_count: links offline
        columns: Lista de nombres de columnas (default: PREVIEW_SHOW_COLS)

    Returns:
        str: HTML completo
    """
    if columns is None:
        columns = PREVIEW_SHOW_COLS

    # Header
    header_cols = ''.join(f'<th>{format_column_label(c)}</th>\n' for c in columns)

    # Rows
    rows_html = []
    for row in rows_data:
        row_class = 'offline-row' if row.get('is_offline') else ''
        link_cell = generate_link_cell(row.get('link'), row.get('link_status'))

        cells_html = []
        for cell in row.get('cells', []):
            css = cell.get('css_class', '')
            val = cell.get('value', '-')
            cells_html.append(f'<td class="{css}">{val}</td>')

        rows_html.append(f'''
            <tr class="{row_class}">
                <td>{row.get('fila', '')}</td>
                {link_cell}
                {''.join(cells_html)}
            </tr>''')

    # Summary
    offline_html = ''
    if stats.get('offline_count', 0) > 0:
        offline_html = f'<span class="offline">! {stats["offline_count"]} links offline</span>'

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Preview - Sync Sheet</title>
    <style>{PREVIEW_CSS}</style>
</head>
<body>
    <h1>Preview: Local vs Google Sheets</h1>
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
                {header_cols}
            </tr>
        </thead>
        <tbody>
            {''.join(rows_html)}
        </tbody>
    </table>
    <div class="summary">
        <strong>Resumen:</strong>
        <span class="new">+{stats.get('added_cells', 0)} celdas nuevas</span>
        <span class="modified">~{stats.get('modified_cells', 0)} celdas modificadas</span>
        {offline_html}
    </div>
</body>
</html>'''


def build_preview_data(local_rows, cloud_rows, link_status=None, columns=None, diff_cols=None):
    """
    Construye datos para el preview comparando local vs cloud.

    Args:
        local_rows: Lista de filas locales (dicts)
        cloud_rows: Dict {fila: row_dict} de datos en la nube
        link_status: Dict {fila: http_status} (opcional)
        columns: Columnas a mostrar
        diff_cols: Columnas a comparar para detectar cambios

    Returns:
        tuple: (rows_data, stats)
    """
    if columns is None:
        columns = PREVIEW_SHOW_COLS
    if diff_cols is None:
        diff_cols = PREVIEW_DIFF_COLS
    if link_status is None:
        link_status = {}

    rows_data = []
    stats = {'added_cells': 0, 'modified_cells': 0, 'offline_count': 0}

    for row in local_rows:
        fila = row.get('_row', 0)
        if fila < 2:
            continue

        cloud = cloud_rows.get(fila, {})

        # Solo mostrar filas con algun dato
        has_data = any(row.get(c) for c in columns if c not in ['notas'])
        if not has_data:
            continue

        # Estado del link
        status = link_status.get(fila)
        is_offline = status in [404, 410, 0] if status is not None else False
        if is_offline:
            stats['offline_count'] += 1

        # Construir celdas
        cells = []
        for col in columns:
            local_val = str(row.get(col, '') or '').strip()
            cloud_val = str(cloud.get(col, '') or '').strip()

            css_class = ''
            if col in diff_cols:
                if local_val and not cloud_val:
                    css_class = 'new-cell'
                    stats['added_cells'] += 1
                elif local_val and cloud_val and local_val != cloud_val:
                    css_class = 'modified-cell'
                    stats['modified_cells'] += 1

            # Formatear valor
            formatted_val, extra_css = format_cell_value(local_val, col, not local_val)
            if extra_css:
                css_class = f'{css_class} {extra_css}'.strip()

            cells.append({'value': formatted_val, 'css_class': css_class})

        rows_data.append({
            'fila': fila,
            'link': row.get('link', ''),
            'link_status': status,
            'is_offline': is_offline,
            'cells': cells
        })

    return rows_data, stats
