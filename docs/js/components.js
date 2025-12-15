// ============================================
// COMPONENTES DE HEADER
// ============================================

function renderStatusBar(stats) {
  return `
    <div class="bg-slate-800 text-white">
      <div class="max-w-7xl mx-auto px-4 py-1 flex items-center justify-between text-xs">
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-1.5">
            ${state.loading
              ? '<span class="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></span><span class="text-yellow-300">Cargando...</span>'
              : state.error
                ? '<span class="w-2 h-2 bg-red-400 rounded-full"></span><span class="text-red-300">Error</span>'
                : '<span class="w-2 h-2 bg-green-400 rounded-full"></span><span class="text-green-300">OK</span>'
            }
          </div>
          ${state.lastUpdate ? `<span class="text-slate-400">· ${state.lastUpdate.toLocaleTimeString()}</span>` : ''}
          <span class="text-slate-500">${state.autoRefreshEnabled ? '· Auto ●' : ''}</span>
        </div>
        <div class="text-slate-400">
          ${stats.total} props · ${stats.activos} activas · ${stats.entran} entran · <span class="text-slate-600">v6-modular</span>
        </div>
      </div>
    </div>
  `;
}

function renderDolarBar() {
  const formatVariacion = (v) => (parseFloat(v) > 0 ? '+' : '') + (v || '0') + '%';

  return `
    <div class="bg-slate-700 text-white">
      <div class="max-w-7xl mx-auto px-4 py-1 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="text-slate-400 text-xs">💵 Dólar BNA</span>
          ${state.dolarBNA ? `
            <span class="font-bold text-emerald-400">$${state.dolarBNA.venta}</span>
            <span class="text-slate-500">|</span>
            ${state.dolarBNA.variaciones ? `
              <span class="text-xs ${variacionColor(state.dolarBNA.variaciones.dia)}">1d: ${formatVariacion(state.dolarBNA.variaciones.dia)}</span>
              <span class="text-slate-600">|</span>
              <span class="text-xs ${variacionColor(state.dolarBNA.variaciones.semana)}">7d: ${formatVariacion(state.dolarBNA.variaciones.semana)}</span>
              <span class="text-slate-600">|</span>
              <span class="text-xs ${variacionColor(state.dolarBNA.variaciones.mes)}">30d: ${formatVariacion(state.dolarBNA.variaciones.mes)}</span>
            ` : ''}
          ` : `
            <span class="text-slate-500 text-xs">Cargando...</span>
          `}
        </div>
        <button onclick="cargarDolarHoy()" class="text-xs text-slate-400 hover:text-white transition-colors" ${state.loadingDolar ? 'disabled' : ''}>
          ${state.loadingDolar ? '...' : '↻'}
        </button>
      </div>
    </div>
  `;
}

function renderMainHeader(activePage = 'buscador') {
  const isBuscador = activePage === 'buscador';
  const isStats = activePage === 'stats';

  return `
    <div class="max-w-7xl mx-auto px-4 py-3">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-4">
          <h1 class="text-xl font-bold text-slate-800">🏠 Casita Chiquis ${isBuscador ? '<span class="emoji-float text-sm">👩❤️🧔‍♂️🐱🐈</span>' : ''}</h1>
          <nav class="flex bg-slate-100 rounded-lg p-1">
            ${isBuscador
              ? '<span class="px-3 py-1.5 text-sm rounded-md bg-white shadow-sm text-slate-700 font-medium">Buscador</span>'
              : '<a href="index.html" class="px-3 py-1.5 text-sm rounded-md text-slate-600 hover:bg-white/50">Buscador</a>'
            }
            ${isStats
              ? '<span class="px-3 py-1.5 text-sm rounded-md bg-white shadow-sm text-slate-700 font-medium">📊 Stats</span>'
              : '<a href="stats.html" class="px-3 py-1.5 text-sm rounded-md text-slate-600 hover:bg-white/50">📊 Stats</a>'
            }
          </nav>
        </div>
        <div class="flex items-center gap-2">
          <a href="https://docs.google.com/spreadsheets/d/${SHEET_ID}" target="_blank" class="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700" title="Abrir Google Sheet">📝 Sheet</a>
          <button onclick="fetchData()" class="px-3 py-1.5 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 disabled:opacity-50" ${state.loading ? 'disabled' : ''} title="Actualizar datos">${state.loading ? '...' : '↻'}</button>
          <button onclick="toggleAutoRefresh()" class="px-3 py-1.5 ${state.autoRefreshEnabled ? 'bg-green-500 text-white' : 'bg-slate-200 text-slate-700'} text-sm rounded-lg hover:opacity-80" title="Auto-refresh">${state.autoRefreshEnabled ? '⏸' : '▶'}</button>
          <span class="w-px h-6 bg-slate-200"></span>
          <button onclick="state.showHelp=!state.showHelp;render()" class="px-3 py-1.5 ${state.showHelp ? 'bg-purple-500 text-white' : 'bg-slate-200 text-slate-700'} text-sm rounded-lg hover:opacity-80" title="Ayuda">?</button>
          <button onclick="state.showConfig=!state.showConfig;render()" class="px-3 py-1.5 ${state.showConfig ? 'bg-blue-500 text-white' : 'bg-slate-200 text-slate-700'} text-sm rounded-lg hover:opacity-80" title="Config">⚙️</button>
        </div>
      </div>
      <p class="text-xs text-slate-500 mt-1">Crédito $${getCreditoUSD().toLocaleString()} USD · Tengo $${CONFIG.PRESUPUESTO.toLocaleString()} · Busco $${getPrecioRange().min.toLocaleString()} - $${getPrecioRange().max.toLocaleString()}</p>
    </div>
  `;
}

function renderHeader(stats, activePage = 'buscador') {
  return `
    <header class="fixed top-0 left-0 right-0 bg-white shadow-md z-40">
      ${renderStatusBar(stats)}
      ${renderDolarBar()}
      ${renderMainHeader(activePage)}
      ${state.showConfig ? `<div class="border-t border-slate-200 bg-slate-50"><div class="max-w-7xl mx-auto px-4 py-3">${renderConfigPanel()}</div></div>` : ''}
      ${state.showHelp ? `<div class="border-t border-slate-200 bg-purple-50 max-h-[60vh] overflow-y-auto"><div class="max-w-7xl mx-auto px-4 py-3">${renderHelpPanel()}</div></div>` : ''}
    </header>
  `;
}

// ============================================
// COMPONENTES DE CONTENIDO
// ============================================

function renderStatsCards(stats) {
  return `
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 md:gap-3 mb-4">
      <div class="bg-white rounded-xl p-3 shadow-sm"><div class="text-xl md:text-2xl font-bold text-blue-600">${stats.total}</div><div class="text-xs text-slate-500">Total</div></div>
      <div class="bg-white rounded-xl p-3 shadow-sm"><div class="text-xl md:text-2xl font-bold text-green-600">${stats.entran}</div><div class="text-xs text-slate-500">Entran</div></div>
      <div class="bg-white rounded-xl p-3 shadow-sm"><div class="text-xl md:text-2xl font-bold text-red-600">${stats.total - stats.entran}</div><div class="text-xs text-slate-500">No entran</div></div>
      <div class="bg-white rounded-xl p-3 shadow-sm"><div class="text-xl md:text-2xl font-bold text-teal-600">${stats.activos}</div><div class="text-xs text-slate-500">Activos</div></div>
      <div class="bg-white rounded-xl p-3 shadow-sm"><div class="text-xl md:text-2xl font-bold text-purple-600">$${stats.minPrecio > 0 ? (stats.minPrecio/1000).toFixed(0) + 'k' : '-'}</div><div class="text-xs text-slate-500">Min</div></div>
      <div class="bg-white rounded-xl p-3 shadow-sm"><div class="text-xl md:text-2xl font-bold text-purple-600">$${stats.maxPrecio > 0 ? (stats.maxPrecio/1000).toFixed(0) + 'k' : '-'}</div><div class="text-xs text-slate-500">Max</div></div>
    </div>
  `;
}

function renderFilters(barrios, filtered, properties) {
  return `
    <div class="bg-white rounded-xl p-3 shadow-sm mb-4">
      <div class="flex flex-wrap gap-2 md:gap-3 items-center text-sm">
        <select onchange="state.filterStatus=this.value;render()" class="border border-slate-200 rounded-lg px-2 py-1.5 text-sm bg-white">
          <option value="todos" ${state.filterStatus === 'todos' ? 'selected' : ''}>Status: Todos</option>
          <option value="por ver" ${state.filterStatus === 'por ver' ? 'selected' : ''}>Por ver</option>
          <option value="visitado" ${state.filterStatus === 'visitado' ? 'selected' : ''}>Visitado</option>
          <option value="interesado" ${state.filterStatus === 'interesado' ? 'selected' : ''}>Interesado</option>
          <option value="descartado" ${state.filterStatus === 'descartado' ? 'selected' : ''}>Descartado</option>
        </select>
        <select onchange="state.filterOk=this.value;render()" class="border border-slate-200 rounded-lg px-2 py-1.5 text-sm bg-white">
          <option value="todos" ${state.filterOk === 'todos' ? 'selected' : ''}>A juntar: Todos</option>
          <option value="ok" ${state.filterOk === 'ok' ? 'selected' : ''}>✓ Me alcanza</option>
          <option value="no" ${state.filterOk === 'no' ? 'selected' : ''}>✗ No me alcanza</option>
        </select>
        <select onchange="state.filterBarrio=this.value;render()" class="border border-slate-200 rounded-lg px-2 py-1.5 text-sm bg-white">
          <option value="todos" ${state.filterBarrio === 'todos' ? 'selected' : ''}>Barrio: Todos</option>
          ${barrios.map(b => `<option value="${escapeHtml(b)}" ${state.filterBarrio === b ? 'selected' : ''}>${escapeHtml(b)}</option>`).join('')}
        </select>
        <select onchange="state.filterActivo=this.value;render()" class="border border-slate-200 rounded-lg px-2 py-1.5 text-sm bg-white">
          <option value="todos" ${state.filterActivo === 'todos' ? 'selected' : ''}>Aviso: Todos</option>
          <option value="si" ${state.filterActivo === 'si' ? 'selected' : ''}>✓ Activo</option>
          <option value="no" ${state.filterActivo === 'no' ? 'selected' : ''}>✗ Baja</option>
        </select>
        <div class="flex items-center gap-1 ml-auto">
          <select onchange="state.sortBy=this.value;render()" class="border border-slate-200 rounded-lg px-2 py-1.5 text-sm bg-white">
            <option value="score" ${state.sortBy === 'score' ? 'selected' : ''}>⭐ Mejor candidato</option>
            <option value="completeness" ${state.sortBy === 'completeness' ? 'selected' : ''}>Completitud</option>
            <option value="precio" ${state.sortBy === 'precio' ? 'selected' : ''}>Precio</option>
            <option value="total" ${state.sortBy === 'total' ? 'selected' : ''}>A juntar</option>
            <option value="dif" ${state.sortBy === 'dif' ? 'selected' : ''}>Diferencia</option>
            <option value="preciom2" ${state.sortBy === 'preciom2' ? 'selected' : ''}>$/m²</option>
          </select>
          <button onclick="state.sortDir=state.sortDir==='asc'?'desc':'asc';render()" class="px-2 py-1.5 border border-slate-200 rounded-lg bg-white hover:bg-slate-50">${state.sortDir === 'asc' ? '↑' : '↓'}</button>
        </div>
        <div class="flex items-center border border-slate-200 rounded-lg overflow-hidden">
          <button onclick="state.viewMode='cards';render()" class="px-2 py-1.5 text-sm ${state.viewMode === 'cards' ? 'bg-blue-500 text-white' : 'bg-white hover:bg-slate-50'}" title="Vista cards">📱</button>
          <button onclick="state.viewMode='auto';render()" class="px-2 py-1.5 text-sm ${state.viewMode === 'auto' ? 'bg-blue-500 text-white' : 'bg-white hover:bg-slate-50'}" title="Auto (cards en móvil, tabla en desktop)">Auto</button>
          <button onclick="state.viewMode='table';render()" class="px-2 py-1.5 text-sm ${state.viewMode === 'table' ? 'bg-blue-500 text-white' : 'bg-white hover:bg-slate-50'}" title="Vista tabla">📊</button>
        </div>
        <span class="text-slate-400 text-xs">${filtered.length}/${properties.length}</span>
      </div>
    </div>
  `;
}

function renderTable(filtered) {
  return `
    <div class="bg-white rounded-xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600" title="Tier + Score">⭐</th>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600">Activo</th>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600" title="Apto Crédito">Apto</th>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600">Status</th>
              <th class="px-3 py-2.5 text-left font-medium text-slate-600">Dirección</th>
              <th class="px-3 py-2.5 text-left font-medium text-slate-600">Barrio</th>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600">Tipo</th>
              <th class="px-3 py-2.5 text-right font-medium text-slate-600">Precio</th>
              <th class="px-2 py-2.5 text-right font-medium text-slate-600">m²</th>
              <th class="px-2 py-2.5 text-right font-medium text-slate-600" title="m² descubiertos">desc</th>
              <th class="px-3 py-2.5 text-right font-medium text-slate-600">$/m²</th>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600" title="Diferencia vs precio promedio del barrio">vs Ref</th>
              <th class="px-3 py-2.5 text-right font-medium text-slate-600">A juntar</th>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600">OK</th>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600" title="Cocheras">🚗</th>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600" title="Terraza">🌿</th>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600" title="Balcón">🪴</th>
              <th class="px-2 py-2.5 text-center font-medium text-slate-600" title="Baños">🚿</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            ${filtered.map((p, i) => {
              const rowBg = getRowBgColor(p);
              return `
              <tr class="hover:bg-slate-100 transition-colors cursor-pointer ${rowBg}" onclick="showDetail(${p._idx})">
                <td class="px-2 py-2.5 text-center"><span class="inline-flex items-center gap-1">${tierBadge(p._tier)}<span class="text-xs font-mono ${p._score > 50 ? 'text-green-600 font-bold' : p._score > 0 ? 'text-green-500' : 'text-slate-400'}">${p._score}</span></span></td>
                <td class="px-2 py-2.5 text-center">${activoBadge(p.activo)}</td>
                <td class="px-2 py-2.5 text-center">${aptoCreditoBadge(p.apto_credito)}</td>
                <td class="px-2 py-2.5 text-center">${statusBadge(p.status)}</td>
                <td class="px-3 py-2.5"><span class="font-medium text-slate-800">${p.direccion ? escapeHtml(p.direccion) : '<span class="text-slate-300 text-xs italic">sin dir</span>'}</span>${fechaIndicators(p)}</td>
                <td class="px-3 py-2.5 text-slate-600">${p.barrio ? escapeHtml(p.barrio) : '<span class="text-slate-300 text-xs italic">-</span>'}</td>
                <td class="px-2 py-2.5 text-center text-xs text-slate-600">${p.tipo ? escapeHtml(p.tipo.toUpperCase()) : '<span class="text-slate-300">-</span>'}</td>
                <td class="px-3 py-2.5 text-right font-mono text-slate-800">${p._precio > 0 ? '$' + p._precio.toLocaleString() : '<span class="text-slate-300">-</span>'}</td>
                <td class="px-2 py-2.5 text-right text-slate-600">${p._m2 ? p._m2 : '<span class="text-slate-300">-</span>'}</td>
                <td class="px-2 py-2.5 text-right text-slate-500 text-xs">${p.m2_terr && p.m2_terr !== '0' ? p.m2_terr : '<span class="text-slate-300">-</span>'}</td>
                <td class="px-3 py-2.5 text-right font-mono text-slate-600">${p._preciom2 > 0 ? '$' + p._preciom2.toLocaleString() : '<span class="text-slate-300">-</span>'}</td>
                <td class="px-2 py-2.5 text-center">${evalIcon(p._vsRef)}</td>
                <td class="px-3 py-2.5 text-right font-mono text-slate-800">${p._precio > 0 ? '$' + p._total.toLocaleString() : '<span class="text-slate-300">-</span>'}</td>
                <td class="px-2 py-2.5 text-center">${p._precio > 0 ? okPill(p._ok) : '<span class="text-slate-300">-</span>'}</td>
                <td class="px-2 py-2.5 text-center">${p.cocheras ? (p.cocheras !== '0' ? '<span class="text-green-600">✓</span>' : '<span class="text-slate-300">-</span>') : '<span class="text-slate-300">-</span>'}</td>
                <td class="px-2 py-2.5 text-center">${p.terraza?.toLowerCase() === 'si' ? '<span class="text-green-600">✓</span>' : '<span class="text-slate-300">-</span>'}</td>
                <td class="px-2 py-2.5 text-center">${p.balcon?.toLowerCase() === 'si' ? '<span class="text-green-600">✓</span>' : '<span class="text-slate-300">-</span>'}</td>
                <td class="px-2 py-2.5 text-center text-xs">${p.banos && p.banos !== '0' ? p.banos : '<span class="text-slate-300">-</span>'}</td>
              </tr>
            `;}).join('')}
          </tbody>
        </table>
      </div>
      ${filtered.length === 0 ? '<div class="text-center py-8 text-slate-400">No hay propiedades que coincidan</div>' : ''}
    </div>
  `;
}

function renderCards(filtered) {
  return `
    <div class="space-y-3">
      ${filtered.map(p => {
        const completePct = p._completeness * 25;
        const barColor = p._completeness >= 3 ? 'bg-green-500' : p._completeness >= 2 ? 'bg-yellow-500' : 'bg-red-400';
        const isInactivo = (p.activo || '').toLowerCase() === 'no';
        const noAptoCredito = (p.apto_credito || '').toLowerCase() !== 'si';
        const cardStyle = isInactivo
          ? 'bg-red-50 border-2 border-red-200 opacity-70'
          : noAptoCredito
            ? 'bg-yellow-100 border-2 border-yellow-300'
            : 'bg-white';
        const warnings = [];
        if (isInactivo) warnings.push('<span class="text-red-600">INACTIVO</span>');
        if (noAptoCredito) warnings.push('<span class="text-amber-600">NO APTO CRÉDITO</span>');
        if (p._missingCount > 0) warnings.push(`<span class="text-orange-500">${p._missingCount} DATO${p._missingCount > 1 ? 'S' : ''} FALTANTE${p._missingCount > 1 ? 'S' : ''}</span>`);
        return `
          <div class="${cardStyle} rounded-xl p-4 shadow-sm cursor-pointer hover:shadow-md transition-shadow" onclick="showDetail(${p._idx})">
            ${warnings.length ? '<div class="text-xs font-medium mb-1">' + warnings.join(' · ') + '</div>' : ''}
            <div class="flex items-center gap-2 mb-2">
              <div class="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                <div class="h-full ${barColor} rounded-full transition-all" style="width: ${completePct}%"></div>
              </div>
              <span class="text-xs text-slate-400">${p._completeness}/4</span>
            </div>
            <div class="flex items-start justify-between gap-2 mb-1">
              <span class="font-medium text-slate-800">${p.direccion ? escapeHtml(p.direccion) : '<span class="text-slate-300 italic">sin dirección</span>'}</span>
              ${p._precio > 0 ? okPill(p._ok) : ''}
            </div>
            <div class="text-sm text-slate-500 mb-2">${p.barrio ? escapeHtml(p.barrio) : '<span class="text-slate-300 italic">sin barrio</span>'}</div>
            <div class="flex items-center gap-2 text-sm mb-2">
              <span class="font-mono font-medium">${p._precio > 0 ? '$' + p._precio.toLocaleString() : '<span class="text-slate-300">$?</span>'}</span>
              <span class="text-slate-300">·</span>
              <span>${p._m2 ? p._m2 + 'm²' : '<span class="text-slate-300">m²?</span>'}</span>
              ${p._preciom2 > 0 ? `<span class="text-slate-300">·</span><span class="text-slate-500">$${p._preciom2.toLocaleString()}/m²</span>` : ''}
            </div>
            <div class="flex flex-wrap items-center gap-2">
              ${statusBadge(p.status)}
              ${activoBadge(p.activo)}
              ${evalIcon(p._vsRef)}
              ${tierBadge(p._tier)}
              <span class="text-xs font-mono px-1.5 py-0.5 rounded ${p._score > 50 ? 'bg-green-100 text-green-700 font-bold' : p._score > 0 ? 'bg-green-50 text-green-600' : 'bg-slate-100 text-slate-400'}">⭐${p._score}</span>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

// ============================================
// PANELES DE CONFIGURACIÓN Y AYUDA
// ============================================

function renderHelpPanel() {
  const sheetUrl = 'https://docs.google.com/spreadsheets/d/16n92ghEe8Vr1tiLdqbccF3i97kiwhHin9OPWY-O50L4';
  return `
    <div>
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-medium text-purple-700">❓ Cómo usar</h3>
        <button onclick="state.showHelp=false;render()" class="text-slate-400 hover:text-slate-600 text-xl">&times;</button>
      </div>
      <div class="space-y-4 text-sm text-slate-600">
        <div class="bg-purple-50 rounded-lg p-3">
          <p class="font-medium text-purple-800 mb-2">Agregar propiedades</p>
          <a href="${sheetUrl}" target="_blank" class="inline-flex items-center gap-2 px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
            Abrir Google Sheet <span>↗</span>
          </a>
        </div>
        <div>
          <p class="font-medium text-slate-700 mb-2">Campos con desplegable:</p>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            <div><span class="font-mono bg-slate-100 px-1 rounded">barrio</span> - seleccionar de lista</div>
            <div><span class="font-mono bg-slate-100 px-1 rounded">amb</span> - 1 a 5</div>
            <div><span class="font-mono bg-slate-100 px-1 rounded">apto_credito</span> - si/no</div>
            <div><span class="font-mono bg-slate-100 px-1 rounded">terraza</span> - si/no</div>
            <div><span class="font-mono bg-slate-100 px-1 rounded">status</span> - Por ver, Visitado, etc.</div>
            <div><span class="font-mono bg-slate-100 px-1 rounded">activo</span> - si/no (aviso online)</div>
          </div>
        </div>
        <div class="bg-blue-50 rounded-lg p-3">
          <p class="font-medium text-blue-800 mb-1">Indicadores de precio:</p>
          <div class="flex gap-4 text-xs">
            <span>🟢 Bajo mercado (&lt;-12%)</span>
            <span>🟡 En mercado</span>
            <span>🔴 Sobre mercado (&gt;+12%)</span>
          </div>
        </div>
        <div class="bg-slate-50 rounded-lg p-3">
          <p class="font-medium text-slate-800 mb-2">Colores de fila:</p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            <div class="flex items-center gap-2"><span class="w-4 h-4 rounded bg-green-100 border border-green-300"></span> Entra en presupuesto</div>
            <div class="flex items-center gap-2"><span class="w-4 h-4 rounded bg-yellow-200 border-l-4 border-yellow-500"></span> Verificar si es apto crédito</div>
            <div class="flex items-center gap-2"><span class="w-4 h-4 rounded bg-yellow-100 border border-yellow-300"></span> NO apto crédito (confirmado)</div>
            <div class="flex items-center gap-2"><span class="w-4 h-4 rounded bg-red-100 border border-red-300 opacity-60"></span> Link dado de baja</div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ============================================
// CONFIG PANEL - SUB-COMPONENTES
// ============================================

// Helper para campos de input
function configInput(label, value, onChange, options = {}) {
  const { type = 'number', step, className = '' } = options;
  const stepAttr = step ? `step="${step}"` : '';
  return `
    <div class="${className}">
      <label class="block text-xs text-slate-500 mb-1">${label}</label>
      <input type="${type}" ${stepAttr} value="${value}" onchange="${onChange}" class="w-full px-3 py-2 border rounded-lg text-sm" />
    </div>
  `;
}

// Helper para campos de solo lectura
function configDisplay(label, value, colorClass = 'text-slate-700') {
  return `
    <div>
      <label class="block text-xs text-slate-500 mb-1">${label}</label>
      <div class="px-3 py-2 ${THEME.neutral.bg} rounded-lg text-sm font-mono ${colorClass}">${value}</div>
    </div>
  `;
}

function renderConfigTab_General() {
  return `
    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      ${configInput('Crédito hipotecario (ARS)', CONFIG.CREDITO_ARS, "updateConfig('CREDITO_ARS', parseInt(this.value))")}
      ${configInput('Dólar base (ARS/USD)', CONFIG.DOLAR_BASE, "updateConfig('DOLAR_BASE', parseInt(this.value))")}
      ${configDisplay('= Crédito en USD', '$' + getCreditoUSD().toLocaleString(), 'font-bold ' + THEME.success.text)}
      ${configInput('Tengo para poner (USD)', CONFIG.PRESUPUESTO, "updateConfig('PRESUPUESTO', parseInt(this.value))")}
      ${configDisplay('= Rango de precios', '$' + getPrecioRange().min.toLocaleString() + ' - $' + getPrecioRange().max.toLocaleString())}
      ${configInput('Auto-refresh (seg, 0=off)', CONFIG.AUTO_REFRESH, "updateConfig('AUTO_REFRESH', parseInt(this.value)); startAutoRefresh();")}
    </div>
  `;
}

function renderConfigTab_Gastos() {
  return `
    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      ${configInput('Escribano (%)', toPct(CONFIG.ESCRIBANO), "updateConfig('ESCRIBANO', fromPct(this.value))", { step: '0.01' })}
      ${configInput('Sellos (%)', toPct(CONFIG.SELLOS), "updateConfig('SELLOS', fromPct(this.value))", { step: '0.01' })}
      ${configInput('Exento sellos hasta (USD)', CONFIG.SELLOS_EXENTO, "updateConfig('SELLOS_EXENTO', parseInt(this.value))")}
      ${configInput('Registrales (%)', toPct(CONFIG.REGISTRALES), "updateConfig('REGISTRALES', fromPct(this.value))", { step: '0.01' })}
      ${configInput('Inmobiliaria (%)', toPct(CONFIG.INMOB), "updateConfig('INMOB', fromPct(this.value))", { step: '0.01' })}
      ${configInput('Hipoteca (%)', toPct(CONFIG.HIPOTECA), "updateConfig('HIPOTECA', fromPct(this.value))", { step: '0.01' })}
      ${configInput('Certificados (USD fijo)', CONFIG.CERTIFICADOS, "updateConfig('CERTIFICADOS', parseInt(this.value))")}
      ${configInput('Margen referencia (%)', toPct(CONFIG.MARGEN_REF, 0), "updateConfig('MARGEN_REF', fromPct(this.value))", { step: '1' })}
    </div>
  `;
}

function renderConfigTab_Barrios() {
  const barrioItems = Object.entries(REF_M2).sort((a, b) => a[0].localeCompare(b[0])).map(([barrio, valor]) => `
    <div class="flex items-center gap-2 ${THEME.neutral.bg} rounded-lg p-2">
      <input type="number" value="${valor}" onchange="updateRefM2('${escapeHtml(barrio)}', this.value)" class="w-20 px-2 py-1 border rounded text-sm" />
      <span class="text-sm text-slate-600 flex-1 truncate" title="${escapeHtml(barrio)}">${escapeHtml(barrio)}</span>
      <button onclick="deleteBarrio('${escapeHtml(barrio)}')" class="${THEME.error.textLight} hover:${THEME.error.text} text-sm">${ICONS.cross}</button>
    </div>
  `).join('');

  return `
    <div class="mb-3">
      <button onclick="addBarrio()" class="px-3 py-1.5 ${THEME.info.bgSolid} text-white text-sm rounded-lg hover:bg-blue-600">+ Agregar barrio</button>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
      ${barrioItems}
    </div>
  `;
}

function renderConfigTab_Pesos() {
  // Tier badges
  const tierBadges = Object.entries(TIER_CONFIG).map(([tier, cfg]) =>
    `<span class="${cfg.css} px-1.5 py-0.5 rounded">${cfg.label}: ${cfg.name}</span>`
  ).join('');

  // Condiciones
  const condicionItems = Object.entries(CONDITIONS).map(([key, config]) => `
    <label class="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" ${config.enabled ? 'checked' : ''}
        onchange="updateCondition('${key}', this.checked)"
        class="w-4 h-4 accent-blue-500 rounded" />
      <span class="text-sm ${config.enabled ? THEME.neutral.text : 'text-slate-400'}">${config.label}</span>
      <span class="text-xs text-slate-400" title="${config.desc}">${ICONS.info}</span>
    </label>
  `).join('');

  // Pesos
  const pesoItems = Object.entries(WEIGHTS).map(([key, config]) => `
    <div class="flex flex-col p-2 rounded-lg ${config.enabled ? 'bg-blue-50/50' : THEME.neutral.bg + ' opacity-50'}" title="${config.desc}">
      <div class="flex items-center gap-1.5 text-xs mb-1">
        <input type="checkbox" ${config.enabled ? 'checked' : ''}
          onchange="toggleWeightEnabled('${key}', this.checked)"
          class="w-3.5 h-3.5 accent-blue-500 rounded" />
        <span class="${config.enabled ? THEME.neutral.text + ' font-medium' : 'text-slate-400'}">${config.label}</span>
        <span class="font-bold ${config.enabled ? THEME.info.text : 'text-slate-400'} ml-auto text-sm">${config.weight}</span>
      </div>
      <input type="range" min="0" max="10" value="${config.weight}"
        onchange="updateWeight('${key}', this.value)"
        oninput="updateWeight('${key}', this.value)"
        ${config.enabled ? '' : 'disabled'}
        class="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer ${config.enabled ? 'accent-blue-500' : 'accent-slate-300'}" />
    </div>
  `).join('');

  return `
    <div class="mb-4">
      <div class="flex flex-wrap items-center gap-2 text-xs mb-3">
        <span class="font-medium text-slate-600">Sistema de Tiers:</span>
        ${tierBadges}
      </div>
      <div class="${THEME.neutral.bg} rounded-lg p-3 mb-4">
        <div class="text-xs font-medium text-slate-600 mb-2">Condiciones habilitadas:</div>
        <div class="flex flex-wrap gap-3">${condicionItems}</div>
      </div>
    </div>
    <div class="text-xs text-slate-500 mb-2">Ponderación (${ICONS.arrowUp} peso = más importante, hover para ver qué prioriza):</div>
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">${pesoItems}</div>
    <div class="mt-2 text-right">
      <button onclick="resetWeights()" class="text-xs text-slate-400 hover:${THEME.error.textLight}">Reset pesos</button>
      <button onclick="resetConditions()" class="text-xs text-slate-400 hover:${THEME.error.textLight} ml-3">Reset condiciones</button>
    </div>
  `;
}

// ============================================
// CONFIG PANEL - PRINCIPAL
// ============================================

function renderConfigPanel() {
  const tabClass = (tab) => state.configTab === tab
    ? 'px-3 py-1.5 text-sm font-medium text-blue-600 border-b-2 border-blue-600'
    : 'px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 cursor-pointer';

  const tabs = [
    { id: 'general', label: 'General' },
    { id: 'gastos', label: 'Costos' },
    { id: 'barrios', label: 'Barrios $/m²' },
    { id: 'pesos', label: `${ICONS.config} Ponderación` }
  ];

  const tabButtons = tabs.map(t =>
    `<button onclick="state.configTab='${t.id}';render()" class="${tabClass(t.id)}">${t.label}</button>`
  ).join('');

  const tabContent = {
    general: renderConfigTab_General,
    gastos: renderConfigTab_Gastos,
    barrios: renderConfigTab_Barrios,
    pesos: renderConfigTab_Pesos
  };

  return `
    <div>
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-4">
          <h3 class="font-medium ${THEME.neutral.text}">${ICONS.config} Configuración</h3>
          <div class="flex border-b ${THEME.neutral.border}">${tabButtons}</div>
        </div>
        <div class="flex items-center gap-3">
          <button onclick="resetConfig()" class="text-xs text-slate-400 hover:${THEME.error.textLight}">Reset todo</button>
          <button onclick="state.showConfig=false;render()" class="p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded" title="Cerrar">${ICONS.cross}</button>
        </div>
      </div>
      ${tabContent[state.configTab]()}
    </div>
  `;
}

// ============================================
// MODAL DE DETALLE - COMPONENTES
// ============================================

// Lista de atributos que pueden faltar (para datos faltantes)
const MISSING_ATTRS = [
  { key: 'm2', label: 'm²' },
  { key: 'ambientes', label: 'Ambientes' },
  { key: 'banos', label: 'Baños' },
  { key: 'antiguedad', label: 'Antigüedad' },
  { key: 'expensas', label: 'Expensas' },
  { key: 'terraza', label: 'Terraza' },
  { key: 'balcon', label: 'Balcón' },
  { key: 'cochera', label: 'Cochera' },
  { key: 'luminosidad', label: 'Luminosidad' },
  { key: 'frente', label: 'Disposición' }
];

// Renderiza badges de la propiedad
function renderModalBadges(p) {
  const aptoBadge = p.apto_credito?.toLowerCase() === 'si'
    ? `<span class="text-xs ${THEME.purple.bg} ${THEME.purple.text} px-1.5 py-0.5 rounded">${ICONS.check} Apto crédito</span>`
    : p.apto_credito?.toLowerCase() === 'no'
      ? `<span class="text-xs ${THEME.error.bg} ${THEME.error.text} px-1.5 py-0.5 rounded">${ICONS.cross} No apto</span>`
      : '';

  const linkBadge = p.link
    ? `<a href="${escapeHtml(p.link)}" target="_blank" class="text-xs ${THEME.info.bg} ${THEME.info.text} px-2 py-0.5 rounded hover:bg-blue-200">Ver aviso ${ICONS.external}</a>`
    : '';

  return `
    <div class="flex flex-wrap gap-2 items-center">
      ${statusBadge(p.status)}
      ${activoBadge(p.activo)}
      ${aptoBadge}
      ${evalIcon(p._vsRef)}
      ${linkBadge}
    </div>
  `;
}

// Renderiza alerta de datos faltantes
function renderMissingData(p) {
  if (p._missingCount <= 0) return '';

  const missingBadges = MISSING_ATTRS
    .filter(attr => p._attrScores?.[attr.key] === 'missing')
    .map(attr => `<span class="text-xs ${THEME.negociar.bg} ${THEME.negociar.text} px-2 py-0.5 rounded">${attr.label}</span>`)
    .join('');

  return `
    <div class="${THEME.negociar.bg.replace('100', '50')} border ${THEME.negociar.border} rounded-lg p-3">
      <div class="text-xs font-medium ${THEME.negociar.text} mb-2">${ICONS.warning} Datos faltantes (penalizan score):</div>
      <div class="flex flex-wrap gap-2">${missingBadges}</div>
    </div>
  `;
}

// Renderiza características y amenities
function renderCaracteristicas(p) {
  const caracteristicas = [
    p.tipo ? { label: 'Tipo', value: p.tipo.toUpperCase() } : null,
    p.amb ? { label: 'Ambientes', value: p.amb } : null,
    p.m2_tot && p.m2_tot !== '0' ? { label: 'm² totales', value: p.m2_tot } : null,
    p.m2_terr && p.m2_terr !== '0' ? { label: 'm² desc.', value: p.m2_terr } : null,
    p.banos && p.banos !== '0' ? { label: 'Baños', value: p.banos } : null,
    p.antiguedad ? { label: 'Antigüedad', value: p.antiguedad + ' años' } : null,
    p.estado ? { label: 'Estado', value: p.estado } : null,
    p.expensas && p.expensas !== '0' ? { label: 'Expensas', value: '$' + parseInt(p.expensas).toLocaleString() } : null,
    p.disposicion ? { label: 'Disposición', value: p.disposicion } : null,
    p.piso ? { label: 'Piso', value: p.piso } : null,
  ].filter(Boolean);

  const amenities = [
    p.terraza?.toLowerCase() === 'si' ? `${ICONS.terraza} Terraza` : null,
    p.balcon?.toLowerCase() === 'si' ? `${ICONS.house} Balcón` : null,
    p.cocheras && p.cocheras !== '0' ? `${ICONS.cochera} Cochera` : null,
    p.ascensor?.toLowerCase() === 'si' ? '🛗 Ascensor' : null,
    p.luminosidad?.toLowerCase() === 'si' || p.luminosidad?.toLowerCase() === 'buena' ? `${ICONS.luminosidad} Luminoso` : null,
  ].filter(Boolean);

  if (caracteristicas.length === 0 && amenities.length === 0) return '';

  return `
    <div class="${THEME.neutral.bg} rounded-xl p-4">
      <div class="flex flex-wrap gap-x-6 gap-y-2 text-sm">
        ${caracteristicas.map(c => `<div><span class="text-slate-500">${c.label}:</span> <span class="font-medium">${c.value}</span></div>`).join('')}
      </div>
      ${amenities.length > 0 ? `<div class="flex flex-wrap gap-2 mt-3 text-sm">${amenities.map(a => `<span class="bg-white px-2 py-1 rounded border">${a}</span>`).join('')}</div>` : ''}
    </div>
  `;
}

// Renderiza stats principales (precio, m², etc)
function renderPriceStats(p, costsNeg, hayAjuste) {
  return `
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="${THEME.neutral.bg} rounded-xl p-3 text-center">
        ${state.negotiationPct > 0 && p._precio > 0 ? `
          <div class="text-xs line-through text-slate-400">$${p._precio.toLocaleString()}</div>
          <div class="text-xl font-bold ${THEME.negociar.textLight}">$${costsNeg.precio.toLocaleString()}</div>
        ` : `<div class="text-xl font-bold ${THEME.neutral.textDark}">$${p._precio > 0 ? p._precio.toLocaleString() : '-'}</div>`}
        <div class="text-xs text-slate-500">Precio</div>
      </div>
      <div class="${THEME.neutral.bg} rounded-xl p-3 text-center">
        <div class="text-xl font-bold ${THEME.neutral.textDark}">${p._m2 || '-'}</div>
        <div class="text-xs text-slate-500">m² cub</div>
      </div>
      <div class="${THEME.neutral.bg} rounded-xl p-3 text-center">
        <div class="text-xl font-bold ${THEME.neutral.textDark}">${p._preciom2 > 0 ? '$' + p._preciom2.toLocaleString() : '-'}</div>
        <div class="text-xs text-slate-500">$/m² ${p._ref ? `<span class="text-slate-400">(ref: $${p._ref.toLocaleString()})</span>` : ''}</div>
      </div>
      <div class="${THEME.neutral.bg} rounded-xl p-3 text-center">
        ${hayAjuste && p._precio > 0 ? `
          <div class="text-xs line-through text-slate-400">$${p._total.toLocaleString()}</div>
          <div class="text-xl font-bold ${costsNeg.ok ? THEME.success.textLight : THEME.error.textLight}">$${costsNeg.total.toLocaleString()}</div>
        ` : `<div class="text-xl font-bold ${p._ok ? THEME.success.textLight : THEME.error.textLight}">$${p._precio > 0 ? p._total.toLocaleString() : '-'}</div>`}
        <div class="text-xs text-slate-500">A juntar</div>
      </div>
    </div>
  `;
}

// Renderiza sliders de negociación y dólar
function renderSimulationSliders(dolarActual, hayAjusteDolar, diferenciaCredito, creditoEstimado) {
  const negPct = state.negotiationPct;
  const negDisplay = negPct > 0 ? '-' + (negPct % 1 === 0 ? negPct : negPct.toFixed(1)) + '%' : '0%';

  return `
    <div class="grid md:grid-cols-2 gap-4">
      <div class="bg-gradient-to-r from-orange-50 to-amber-50 rounded-xl p-4 border ${THEME.negociar.border}">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium text-orange-800">${ICONS.handshake} Negociar</span>
          <span class="text-lg font-bold ${negPct > 0 ? THEME.negociar.textLight : 'text-slate-400'}">${negDisplay}</span>
        </div>
        <input type="range" min="0" max="15" step="0.5" value="${negPct}"
          onchange="updateNegotiation(this.value)" oninput="updateNegotiation(this.value)"
          class="w-full h-2 bg-orange-200 rounded-lg appearance-none cursor-pointer accent-orange-500" />
        <div class="flex justify-between text-xs ${THEME.negociar.textLight} mt-1"><span>Publicado</span><span>-15%</span></div>
      </div>

      <div class="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-4 border ${THEME.success.border}">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium text-green-800">${ICONS.dolar} Dólar estimado</span>
          <span class="text-lg font-bold ${hayAjusteDolar ? THEME.success.textLight : 'text-slate-400'}">$${dolarActual}</span>
        </div>
        <input type="range" min="900" max="2000" step="10" value="${dolarActual}"
          onchange="updateDolarEstimado(this.value)" oninput="updateDolarEstimado(this.value)"
          class="w-full h-2 bg-green-200 rounded-lg appearance-none cursor-pointer accent-green-500" />
        <div class="flex justify-between text-xs ${THEME.success.textLight} mt-1">
          <span>$900</span>
          <span>Base: $${CONFIG.DOLAR_BASE}</span>
          <span>$2000</span>
        </div>
        ${hayAjusteDolar ? `<div class="text-xs text-center mt-2 ${diferenciaCredito > 0 ? THEME.error.textLight : THEME.success.textLight}">Crédito: $${creditoEstimado.toLocaleString()} (${diferenciaCredito > 0 ? '-' : '+'}$${Math.abs(diferenciaCredito).toLocaleString()})</div>` : ''}
      </div>
    </div>
  `;
}

// Renderiza sugerencia de quita necesaria
function renderQuitaSugerencia(quita, dolarActual, creditoEstimado) {
  if (quita.quitaPct <= 0) return '';

  const isRealista = quita.esRealista;
  const gradientClass = isRealista ? 'from-purple-50 to-pink-50' : 'from-red-50 to-orange-50';
  const borderClass = isRealista ? THEME.purple.border : THEME.error.border;
  const textClass = isRealista ? 'text-purple-800' : 'text-red-800';
  const textClass2 = isRealista ? 'text-purple-700' : 'text-red-700';

  return `
    <div class="bg-gradient-to-r ${gradientClass} rounded-xl p-4 border ${borderClass}">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-lg">${isRealista ? ICONS.lightbulb : ICONS.warning}</span>
        <span class="font-medium ${textClass}">
          ${isRealista ? 'Para que entre en presupuesto:' : 'Muy cara para tu presupuesto'}
        </span>
      </div>
      <div class="text-sm ${textClass2}">
        ${isRealista
          ? `Necesitás negociar <span class="font-bold">-${quita.quitaPct.toFixed(1)}%</span> (<span class="font-mono">-$${quita.quitaUSD.toLocaleString()}</span>) → precio objetivo: <span class="font-mono font-bold">$${quita.precioTarget.toLocaleString()}</span>`
          : `Necesitarías <span class="font-bold">-${quita.quitaPct.toFixed(1)}%</span> (<span class="font-mono">-$${quita.quitaUSD.toLocaleString()}</span>), poco realista`
        }
      </div>
      ${isRealista ? `<div class="text-xs text-purple-500 mt-1">Con dólar a $${dolarActual} y crédito de $${creditoEstimado.toLocaleString()}</div>` : ''}
    </div>
  `;
}

// Renderiza desglose de costos
function renderCostsBreakdown(p, costsNeg, hayAjuste, ahorro) {
  const costItems = [
    { label: 'Tu 10% (o precio - crédito)', value: hayAjuste ? costsNeg.tu10 : p._tu10, highlight: hayAjuste },
    { label: `Escribano (${(CONFIG.ESCRIBANO * 100).toFixed(1)}%)`, value: hayAjuste ? costsNeg.escr : p._escr },
    {
      label: `Sellos ${(hayAjuste ? costsNeg.precio : p._precio) <= CONFIG.SELLOS_EXENTO
        ? `<span class="${THEME.success.textLight} text-xs">(exento)</span>`
        : `(${(CONFIG.SELLOS * 100).toFixed(2)}%)`}`,
      value: hayAjuste ? costsNeg.sell : p._sell
    },
    { label: `Registrales (${(CONFIG.REGISTRALES * 100).toFixed(1)}%)`, value: hayAjuste ? costsNeg.reg : p._reg },
  ];

  if (p.inmobiliaria) {
    costItems.push({ label: `Inmobiliaria (${(CONFIG.INMOB * 100).toFixed(2)}%)`, value: hayAjuste ? costsNeg.inmob : p._inmob });
  }

  costItems.push(
    { label: `Hipoteca (${(CONFIG.HIPOTECA * 100).toFixed(1)}%)`, value: hayAjuste ? costsNeg.hip : p._hip },
    { label: 'Certificados', value: costsNeg.cert }
  );

  const totalOk = hayAjuste ? costsNeg.ok : p._ok;
  const totalVal = hayAjuste ? costsNeg.total : p._total;
  const difVal = hayAjuste ? costsNeg.dif : p._dif;

  return `
    <div class="${THEME.neutral.bg} rounded-xl p-4">
      <h3 class="text-sm font-medium ${THEME.neutral.text} mb-3">${ICONS.precio} Desglose de costos</h3>
      <div class="space-y-2 text-sm">
        ${costItems.map(item => `
          <div class="flex justify-between">
            <span class="text-slate-600">${item.label}</span>
            <span class="font-mono ${item.highlight ? THEME.negociar.textLight : ''} ${item.highlight ? 'font-medium' : ''}">$${item.value.toLocaleString()}</span>
          </div>
        `).join('')}
        <div class="border-t pt-2 mt-2 flex justify-between font-medium">
          <span>TOTAL A JUNTAR</span>
          <span class="font-mono ${totalOk ? THEME.success.textLight : THEME.error.textLight}">$${totalVal.toLocaleString()}</span>
        </div>
        <div class="flex justify-between text-xs">
          <span class="text-slate-500">Tengo: $${CONFIG.PRESUPUESTO.toLocaleString()}</span>
          <span class="${difVal >= 0 ? THEME.success.textLight : THEME.error.textLight}">${difVal >= 0 ? 'Sobran' : 'Faltan'} $${Math.abs(difVal).toLocaleString()}</span>
        </div>
        ${hayAjuste && ahorro > 0 ? `<div class="text-center ${THEME.success.textLight} text-xs mt-1">${ICONS.lightbulb} Con estos ajustes ahorrás $${ahorro.toLocaleString()}</div>` : ''}
      </div>
    </div>
  `;
}

// Renderiza sección de notas, rating, fechas e inmobiliaria
function renderModalFooter(p) {
  const sections = [];

  if (p.notas) {
    sections.push(`
      <div>
        <h3 class="text-sm font-medium ${THEME.neutral.text} mb-2">${ICONS.notes} Notas</h3>
        <p class="text-sm text-slate-600 ${THEME.neutral.bg} rounded-xl p-4">${escapeHtml(p.notas)}</p>
      </div>
    `);
  }

  if (p.rating) {
    sections.push(`
      <div class="flex items-center gap-2">
        <span class="text-sm text-slate-500">Tu valoración:</span>
        <span class="text-yellow-500">${ratingStars(p.rating)}</span>
      </div>
    `);
  }

  if (p.fecha_publicado || p.fecha_contacto || p.fecha_visita) {
    const fechas = [
      p.fecha_publicado ? `<span>${ICONS.calendar} Publicado: ${p.fecha_publicado}</span>` : '',
      p.fecha_contacto ? `<span>${ICONS.phone} Contactado: ${p.fecha_contacto}</span>` : '',
      p.fecha_visita ? `<span>${ICONS.house} Visitado: ${p.fecha_visita}</span>` : ''
    ].filter(Boolean).join('');

    sections.push(`<div class="flex flex-wrap gap-4 text-xs text-slate-400">${fechas}</div>`);
  }

  if (p.inmobiliaria) {
    sections.push(`
      <div class="text-xs text-slate-400">
        ${ICONS.building} ${escapeHtml(p.inmobiliaria)} ${p.contacto ? '· ' + escapeHtml(p.contacto) : ''}
      </div>
    `);
  }

  return sections.join('');
}

// ============================================
// MODAL PRINCIPAL
// ============================================

function renderDetailModal(p) {
  if (!p) return '';

  // Calcular datos
  const dolarActual = state.dolarEstimado || CONFIG.DOLAR_BASE;
  const creditoBase = getCreditoUSD();
  const creditoEstimado = getCreditoUSD(dolarActual);
  const diferenciaCredito = creditoBase - creditoEstimado;
  const tieneInmob = !esVentaDirecta(p.inmobiliaria);

  const costsNeg = calculateCosts(p._precio, {
    tieneInmob,
    dolar: dolarActual,
    negociacionPct: state.negotiationPct
  });

  const ahorro = p._total - costsNeg.total;
  const hayAjuste = state.negotiationPct > 0 || (state.dolarEstimado && state.dolarEstimado !== CONFIG.DOLAR_BASE);
  const hayAjusteDolar = state.dolarEstimado && state.dolarEstimado !== CONFIG.DOLAR_BASE;
  const quita = calculateQuitaNecesaria(p._precio, tieneInmob, dolarActual);

  return `
    <div class="fixed inset-0 modal-backdrop z-50 flex items-center justify-center p-4" onclick="if(event.target===this)closeDetail()">
      <div class="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-start z-10">
          <div>
            <h2 class="text-xl font-bold ${THEME.neutral.textDark}">${escapeHtml(p.direccion) || '<span class="text-slate-400">Sin dirección</span>'}</h2>
            <p class="text-slate-500">${escapeHtml(p.barrio) || 'Sin barrio'} ${p.tipo ? '· ' + p.tipo.toUpperCase() : ''}</p>
          </div>
          <button onclick="closeDetail()" class="text-slate-400 hover:text-slate-600 text-2xl">${ICONS.close}</button>
        </div>

        <div class="p-6 space-y-5">
          ${renderModalBadges(p)}
          ${renderMissingData(p)}
          ${renderCaracteristicas(p)}
          ${renderPriceStats(p, costsNeg, hayAjuste)}

          ${p._precio > 0 ? `
            ${renderSimulationSliders(dolarActual, hayAjusteDolar, diferenciaCredito, creditoEstimado)}
            ${!costsNeg.ok ? renderQuitaSugerencia(quita, dolarActual, creditoEstimado) : ''}
            ${renderCostsBreakdown(p, costsNeg, hayAjuste, ahorro)}
          ` : ''}

          ${renderModalFooter(p)}
        </div>
      </div>
    </div>
  `;
}
