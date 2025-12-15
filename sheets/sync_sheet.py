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
import re
import subprocess
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

import gspread
import httpx

# =============================================================================
# IMPORTS DE CORE - Módulos refactorizados
# =============================================================================
from core import (
    # Constantes
    BARRIOS_CABA,
    ATTR_PATTERNS,
    SCOPES,
    SHEET_ID,
    WORKSHEET_NAME,
    LOCAL_FILE,
    CACHE_FILE,
    PRINTS_DIR,
    PRINTS_INDEX,
    # Helpers
    quitar_tildes,
    extraer_numero,
    extraer_m2,
    detectar_barrio,
    extraer_id_propiedad,
    get_active_rows,
    calcular_m2_faltantes,
    detectar_atributo,
    # Sheets API
    get_client,
    get_worksheet,
    get_cells_to_update,
    build_sheet_data,
    format_header_row,
    # Storage
    load_local_data,
    save_local_data,
    require_local_data,
    load_cache,
    save_cache,
    # Scrapers
    scrape_argenprop,
    scrape_mercadolibre,
    scrape_link,
    get_rows_to_scrape,
    apply_scraped_data,
    is_offline_error,
    # Validation
    add_warning,
    clear_warnings,
    get_warnings,
    print_warnings_summary,
    validar_propiedad,
    # Prints
    PRINT_DIAS_VENCIMIENTO,
    PRINT_PATTERN_ID,
    PRINT_PATTERN_FILA,
    generar_nombre_print,
    get_prints_index,
    sync_print_dates,
    build_property_index,
    extract_id_from_pdf,
    get_pending_print_files,
    process_print_file,
    # Templates
    PREVIEW_SHOW_COLS,
    PREVIEW_DIFF_COLS,
    generate_preview_html,
    build_preview_data,
)

# =============================================================================
# CONSTANTES ESPECÍFICAS DEL CLI (no están en core/)
# =============================================================================

# Verificar que SHEET_ID existe (viene de core/ que lee de env)
if not SHEET_ID:
    raise ValueError("GOOGLE_SHEET_ID environment variable is required. Set it in .env or export it.")

# Constantes específicas de este CLI (no están en core/)
PENDIENTES_FILE = Path('data/prints/pendientes.json')

CAMPOS_IMPORTANTES = ['terraza', 'balcon', 'cocheras', 'luminosidad', 'disposicion',
                      'ascensor', 'antiguedad', 'expensas', 'banos', 'apto_credito']

SCRAPEABLE_COLS = ['precio', 'm2_cub', 'm2_tot', 'm2_desc', 'm2_terr', 'amb', 'barrio', 'direccion',
                   'expensas', 'terraza', 'antiguedad', 'apto_credito', 'tipo', 'activo',
                   'cocheras', 'disposicion', 'piso', 'ascensor', 'balcon', 'luminosidad',
                   'fecha_publicado', 'banos', 'inmobiliaria', 'dormitorios', 'fecha_print']


# =============================================================================
# COMANDOS CLI
# =============================================================================

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

def cmd_scrape(check_all=False, no_cache=False, force_update=False):
    """Scrapea links del archivo local y actualiza los datos

    Args:
        check_all: Scrapear todos los links (no solo los que faltan datos)
        no_cache: Ignorar cache y re-scrapear
        force_update: Sobrescribir valores existentes (no solo llenar vacíos)
    """
    if not LOCAL_FILE.exists():
        print(f"❌ No existe {LOCAL_FILE}")
        print("   Ejecutá primero: python sync_sheet.py pull")
        return

    with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    headers = data['headers']
    rows = data['rows']

    # Cargar cache y encontrar filas a scrapear
    cache = load_cache() if not no_cache else {}
    to_scrape = get_rows_to_scrape(rows, check_all)

    if not to_scrape:
        print("✅ No hay filas que necesiten scraping")
        return

    print(f"🔍 Scrapeando {len(to_scrape)} links...")
    if not no_cache:
        print(f"   (usando cache de {len(cache)} links)")
    if force_update:
        print(f"   ⚠️  Modo --update: sobrescribiendo valores existentes")

    # Contadores
    updated, offline, cache_hits = 0, 0, 0
    clear_warnings()

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

        # Manejar errores
        if '_error' in scraped:
            print(f"      ❌ {scraped['_error']}")
            if is_offline_error(scraped) and 'activo' in headers:
                rows[idx]['activo'] = 'no'
                offline += 1
                print(f"      📴 Marcado como NO activo")
            continue

        # Link activo - marcar y aplicar datos
        if 'activo' in headers:
            rows[idx]['activo'] = 'si'

        result = apply_scraped_data(rows[idx], scraped, SCRAPEABLE_COLS, headers, force_update)

        if result['changes']:
            print(f"      ✅ Nuevo: {', '.join(result['changes'])}")
            updated += 1
        if result['updates']:
            print(f"      🔄 Actualizado: {', '.join(result['updates'])}")
            updated += 1
        if not result['changes'] and not result['updates']:
            print(f"      ⚪ Sin cambios")

        validar_propiedad(rows[idx], contexto=direccion)
        time.sleep(0.5)

    # Guardar cambios
    data['rows'] = rows
    data['scraped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(LOCAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if not no_cache:
        save_cache(cache)

    # Resumen
    print(f"\n✅ {updated} filas actualizadas en {LOCAL_FILE}")
    if cache_hits:
        print(f"📦 {cache_hits} desde cache, {len(to_scrape) - cache_hits} scrapeados")
    if offline:
        print(f"📴 {offline} links marcados como NO activos")
    print_warnings_summary()
    print(f"\n   Revisá con: python sync_sheet.py view")
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

    # Sincronizar fechas de prints antes de push
    prints_updated = sync_print_dates(rows)

    mode = "FORCE (sobrescribe todo)" if force else "MERGE (solo celdas vacías)"
    print(f"📤 {'[DRY RUN] ' if dry_run else ''}Push en modo {mode}...")
    print(f"   {len(rows)} filas a procesar")
    if prints_updated:
        print(f"   📸 {prints_updated} fechas de print sincronizadas")

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
        all_data = build_sheet_data(headers, rows)
        worksheet.clear()
        worksheet.update(values=all_data, range_name='A1')
        format_header_row(worksheet)
        print(f"✅ Sheet sobrescrito con {len(rows)} filas")
    else:
        # Merge: solo actualizar celdas que cambiaron
        current_values = worksheet.get_all_values()
        cells = get_cells_to_update(rows, current_values, headers, SCRAPEABLE_COLS)

        if cells:
            worksheet.update_cells(cells)
            print(f"✅ {len(cells)} celdas actualizadas")
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

    # Generar datos y HTML usando templates
    rows_data, stats = build_preview_data(
        local_rows, cloud_rows, link_status,
        columns=PREVIEW_SHOW_COLS, diff_cols=PREVIEW_DIFF_COLS
    )
    html = generate_preview_html(rows_data, stats, columns=PREVIEW_SHOW_COLS)

    # Guardar HTML
    html_path = LOCAL_FILE.parent / 'preview.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Preview generado: {html_path}")

    # Abrir en browser
    subprocess.run(['xdg-open', str(html_path)])


# =============================================================================
# SISTEMA DE PRINTS - Comandos CLI
# =============================================================================

def cmd_prints_open(limit=None):
    """Abre en el browser todas las propiedades sin print."""
    import webbrowser

    data = load_local_data()
    if not data:
        print("❌ Primero ejecutá: python sync_sheet.py pull")
        return

    rows = data['rows']
    prints_index = get_prints_index(rows)

    # Encontrar propiedades activas sin print
    sin_print = []
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
        if fila in prints_index:
            continue  # Ya tiene print

        sin_print.append({
            'fila': fila,
            'link': link,
            'direccion': row.get('direccion', ''),
            'barrio': row.get('barrio', ''),
        })

    if not sin_print:
        print("✅ Todas las propiedades activas tienen print!")
        return

    # Limitar cantidad si se especifica
    to_open = sin_print[:limit] if limit else sin_print

    print(f"\n🌐 Abriendo {len(to_open)} pestañas...")
    print(f"   (Guardá cada PDF con Ctrl+P, el nombre que quieras)")
    print(f"   (Después ejecutá: python sync_sheet.py prints scan)\n")

    for p in to_open:
        print(f"   → {p['direccion'][:40]} ({p['barrio']})")
        webbrowser.open(p['link'])
        time.sleep(0.3)  # Pequeña pausa entre tabs

    print(f"\n📁 Guardá los PDFs en: {(PRINTS_DIR / 'nuevos').absolute()}")


def cmd_prints_scan():
    """Analiza PDFs nuevos en la carpeta 'nuevos/', extrae IDs y los mueve a prints/."""
    data = load_local_data()
    if not data:
        print("❌ Primero ejecutá: python sync_sheet.py pull")
        return

    # Construir índices y listar archivos
    id_to_fila, fila_to_info = build_property_index(data['rows'])

    NUEVOS_DIR = PRINTS_DIR / 'nuevos'
    NUEVOS_DIR.mkdir(parents=True, exist_ok=True)
    PRINTS_DIR.mkdir(parents=True, exist_ok=True)

    archivos = get_pending_print_files(NUEVOS_DIR)
    if not archivos:
        print("✅ No hay archivos nuevos para procesar")
        print(f"   (Guardá los PDFs en: {NUEVOS_DIR.absolute()})")
        return

    print(f"\n🔍 Analizando {len(archivos)} archivos...")

    procesados = []
    sin_match = []

    for archivo in archivos:
        print(f"\n   📄 {archivo.name[:50]}...")

        result = process_print_file(archivo, id_to_fila, fila_to_info)
        if result:
            print(f"      ✅ Match: Fila {result['fila']} - {result['direccion'][:30]}")
            print(f"      → Renombrado a: {result['archivo_nuevo']}")
            procesados.append(result)
        else:
            print(f"      ❌ No se encontró match")
            # Intentar mostrar ID detectado
            if archivo.suffix.lower() == '.pdf':
                prop_id = extract_id_from_pdf(archivo)
                if prop_id:
                    print(f"         ID detectado: {prop_id} (no está en el sheet)")
            sin_match.append(archivo.name)

    # Resumen
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN")
    print(f"{'='*60}")
    print(f"   Procesados: {len(procesados)} ✅")
    print(f"   Sin match: {len(sin_match)} ❌")

    if procesados:
        print(f"\n✅ RENOMBRADOS:")
        for p in procesados:
            print(f"   Fila {p['fila']:2d}: {p['direccion'][:35]} → {p['archivo_nuevo']}")

    if sin_match:
        print(f"\n❌ SIN MATCH (revisar manualmente):")
        for s in sin_match:
            print(f"   {s}")
        print(f"\n   Tip: Verificá que las propiedades estén en el sheet")
        print(f"        o renombrá manualmente con formato: MLA123456_2025-12-15.pdf")


def cmd_prints():
    """Muestra estado de prints: cuáles existen, cuáles faltan, cuáles están vencidos."""
    data = load_local_data()
    if not data:
        print("❌ Primero ejecutá: python sync_sheet.py pull")
        return

    rows = data['rows']
    prints_index = get_prints_index(rows)

    # Clasificar propiedades activas
    activas = []
    for row in get_active_rows(rows):
        fila = row.get('_row', 0)
        link = row.get('link', '')
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

    # Estadísticas
    con_print = [p for p in activas if p['print']]
    sin_print = [p for p in activas if not p['print']]
    vencidos = [p for p in con_print if p['print']['vencido']]
    actualizados = [p for p in con_print if not p['print']['vencido']]

    print(f"\n📸 ESTADO DE PRINTS")
    print(f"{'='*70}")
    print(f"   Propiedades activas: {len(activas)}")
    print(f"   Con print actualizado: {len(actualizados)} ✅")
    print(f"   Con print vencido (>{PRINT_DIAS_VENCIMIENTO}d): {len(vencidos)} ⚠️")
    print(f"   Sin print: {len(sin_print)} ❌")
    print(f"{'='*70}")

    if vencidos:
        print(f"\n⚠️  PRINTS VENCIDOS (actualizar):")
        for p in vencidos:
            print(f"   Fila {p['fila']:2d}: {p['direccion'][:35]:<35} | {p['print']['archivo'][:30]} ({p['print']['dias']}d)")

    if sin_print:
        print(f"\n❌ SIN PRINT (crear):")
        for p in sin_print[:15]:
            id_str = p['prop_id'] or 'SIN_ID'
            print(f"   {id_str:<15} {p['direccion'][:30]:<30} → {p['nombre_sugerido'] or 'N/A'}")
        if len(sin_print) > 15:
            print(f"   ... y {len(sin_print) - 15} más")

    if actualizados:
        print(f"\n✅ PRINTS ACTUALIZADOS:")
        for p in actualizados[:10]:
            print(f"   Fila {p['fila']:2d}: {p['direccion'][:35]:<35} | {p['print']['archivo'][:30]} ({p['print']['dias']}d)")
        if len(actualizados) > 10:
            print(f"   ... y {len(actualizados) - 10} más")

    # Detectar prints huérfanos (de propiedades inactivas o sin asociar)
    filas_activas = {p['fila'] for p in activas}
    huerfanos = []
    for f in PRINTS_DIR.iterdir():
        if not f.is_file() or f.suffix.lower() not in ['.png', '.pdf', '.jpg', '.jpeg']:
            continue
        if f.name.startswith('.') or f.name in ['index.json', 'pendientes.json']:
            continue
        # Ver si está asociado a alguna fila activa
        asociado = False
        for fila, info in prints_index.items():
            if info.get('archivo') == f.name and fila in filas_activas:
                asociado = True
                break
        if not asociado:
            huerfanos.append(f.name)

    if huerfanos:
        print(f"\n📦 PRINTS DE PROPIEDADES INACTIVAS ({len(huerfanos)}):")
        for h in huerfanos[:8]:
            print(f"   {h}")
        if len(huerfanos) > 8:
            print(f"   ... y {len(huerfanos) - 8} más")
        print(f"   (pueden moverse a sin_asociar/ si ya no sirven)")

    # Guardar índice
    PRINTS_DIR.mkdir(parents=True, exist_ok=True)
    index_output = {
        'generado': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total_activas': len(activas),
        'con_print': len(con_print),
        'sin_print': len(sin_print),
        'vencidos': len(vencidos),
        'huerfanos': len(huerfanos),
        'dias_vencimiento': PRINT_DIAS_VENCIMIENTO,
        'prints': {str(k): v for k, v in prints_index.items()}
    }
    with open(PRINTS_INDEX, 'w', encoding='utf-8') as f:
        json.dump(index_output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Índice guardado en: {PRINTS_INDEX}")

    # Sugerencias
    if sin_print or vencidos:
        print(f"\n💡 SUGERENCIAS:")
        if sin_print:
            print(f"   → Crear prints para {len(sin_print)} propiedades sin respaldo")
        if vencidos:
            print(f"   → Actualizar {len(vencidos)} prints vencidos (pueden haber cambiado)")
        print(f"   → Nomenclatura: {{ID}}_{{FECHA}}.pdf (ej: MLA123456_2025-12-15.pdf)")


def cmd_pendientes(solo_sin_print=False):
    """Genera lista de propiedades con datos faltantes."""
    if not LOCAL_FILE.exists():
        print("❌ Primero ejecutá: python sync_sheet.py pull")
        return

    with open(LOCAL_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rows = data['rows']
    prints_index = get_prints_index(rows)

    # Filtrar propiedades activas con link
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
        missing = []
        for campo in CAMPOS_IMPORTANTES:
            valor = (row.get(campo) or '').strip().lower()
            if not valor or valor == '?':
                missing.append(campo)

        # Si tiene todos los datos, skip
        if not missing:
            continue

        print_info = prints_index.get(fila)
        tiene_print = print_info is not None

        # Si solo queremos los que no tienen print
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

    # Ordenar por cantidad de datos faltantes (más incompletos primero)
    pendientes.sort(key=lambda x: -len(x['missing']))

    # Guardar JSON
    PRINTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        'total': len(pendientes),
        'con_print': sum(1 for p in pendientes if p['tiene_print']),
        'sin_print': sum(1 for p in pendientes if not p['tiene_print']),
        'instrucciones': 'Guardá los screenshots en data/prints/ con el nombre: fila_XX.pdf o el título del aviso',
        'propiedades': pendientes
    }

    with open(PENDIENTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Mostrar resumen
    print(f"\n📋 PROPIEDADES CON DATOS FALTANTES")
    print(f"{'='*60}")
    print(f"   Total: {len(pendientes)}")
    print(f"   Con print: {output['con_print']} ✅")
    print(f"   Sin print: {output['sin_print']} ⚠️")
    print(f"{'='*60}\n")

    for p in pendientes:
        print_icon = '✅' if p['tiene_print'] else '⚠️'
        missing_str = ', '.join(p['missing'][:5])
        if len(p['missing']) > 5:
            missing_str += f' +{len(p["missing"])-5}'
        print(f"   {print_icon} Fila {p['fila']:2d}: {p['direccion'][:30]:<30} | Faltan: {missing_str}")

    print(f"\n💾 Guardado en: {PENDIENTES_FILE}")
    print(f"📸 Tip: Guardá PDFs con Ctrl+P → 'Guardar como PDF'")


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
    python sync_sheet.py prints        # 5. Ver estado de prints/backups
    python sync_sheet.py pendientes    # 6. Ver props con datos faltantes
        """
    )

    parser.add_argument('command', choices=['pull', 'scrape', 'view', 'diff', 'push', 'prints', 'pendientes'],
                       help='Comando a ejecutar')
    parser.add_argument('subcommand', nargs='?', default=None,
                       help='[prints] Subcomando: open, scan')
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
    parser.add_argument('--update', action='store_true',
                       help='[scrape] Sobrescribe valores existentes (no solo llena vacíos)')
    parser.add_argument('--sin-print', action='store_true',
                       help='[pendientes] Solo muestra los que no tienen screenshot')
    parser.add_argument('--limit', type=int, default=None,
                       help='[prints open] Limita cantidad de tabs a abrir')

    args = parser.parse_args()

    if args.command == 'pull':
        cmd_pull()
    elif args.command == 'scrape':
        cmd_scrape(check_all=args.all, no_cache=args.no_cache, force_update=args.update)
    elif args.command == 'view':
        cmd_view(check_links=args.check_links)
    elif args.command == 'diff':
        cmd_diff()
    elif args.command == 'push':
        cmd_push(force=args.force, dry_run=args.dry_run)
    elif args.command == 'prints':
        if args.subcommand == 'open':
            cmd_prints_open(limit=args.limit)
        elif args.subcommand == 'scan':
            cmd_prints_scan()
        else:
            cmd_prints()
    elif args.command == 'pendientes':
        cmd_pendientes(solo_sin_print=args.sin_print)


if __name__ == '__main__':
    main()
