// ============================================
// UTILIDADES
// ============================================

function getCreditoUSD(dolar = null) {
  const tc = dolar || CONFIG.DOLAR_BASE;
  return Math.round(CONFIG.CREDITO_ARS / tc);
}

function getPrecioRange(dolar = null) {
  const credito = getCreditoUSD(dolar);
  const precioMin = Math.round(credito / 0.9);
  const gastosRate = CONFIG.ESCRIBANO + CONFIG.SELLOS + CONFIG.REGISTRALES + CONFIG.INMOB + CONFIG.HIPOTECA;
  const precioMax = Math.round((CONFIG.PRESUPUESTO + credito) / (1 + gastosRate));
  return { min: precioMin, max: precioMax };
}

function parseCSV(text) {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/\s+/g, '_'));
  return lines.slice(1).map((line, idx) => {
    const values = [];
    let current = '';
    let inQuotes = false;
    for (const char of line) {
      if (char === '"') inQuotes = !inQuotes;
      else if (char === ',' && !inQuotes) { values.push(current.trim()); current = ''; }
      else current += char;
    }
    values.push(current.trim());
    const obj = { _idx: idx };
    headers.forEach((h, i) => { obj[h] = values[i] || ''; });
    return obj;
  }).filter(row => {
    return row.direccion || row.barrio || row.link;
  });
}

function calculateProperty(p) {
  const precio = parseFloat(p.precio) || 0;
  const m2 = parseFloat(p.m2_cub) || 0;
  const barrio = p.barrio;
  const tieneInmob = p.inmobiliaria && p.inmobiliaria.trim() !== '';
  const creditoUSD = getCreditoUSD();
  const calc = { ...p, _precio: precio, _m2: m2, _preciom2: m2 > 0 ? Math.round(precio / m2) : 0, _ref: REF_M2[barrio] || 0 };
  calc._vsRef = (calc._preciom2 > 0 && calc._ref > 0) ? (calc._preciom2 - calc._ref) / calc._ref : null;
  calc._tu10 = Math.max(precio - creditoUSD, precio * 0.1);
  calc._escr = Math.round(precio * CONFIG.ESCRIBANO);
  calc._sell = precio <= CONFIG.SELLOS_EXENTO ? 0 : Math.round(precio * CONFIG.SELLOS);
  calc._reg = Math.round(precio * CONFIG.REGISTRALES);
  calc._inmob = tieneInmob ? Math.round(precio * CONFIG.INMOB) : 0;
  calc._hip = Math.round(precio * CONFIG.HIPOTECA);
  calc._cert = CONFIG.CERTIFICADOS;
  calc._total = calc._tu10 + calc._escr + calc._sell + calc._reg + calc._inmob + calc._hip + calc._cert;
  calc._ok = calc._total <= CONFIG.PRESUPUESTO;
  calc._dif = CONFIG.PRESUPUESTO - calc._total;
  calc._completeness = [p.direccion, p.barrio, precio > 0, m2 > 0].filter(Boolean).length;

  // Score de candidato
  let score = 0;
  const activo = (p.activo || '').toLowerCase();
  const aptoCredito = (p.apto_credito || '').toLowerCase();
  const W = WEIGHTS;

  // Filtros básicos: si no pasa, score = 0
  const pasaFiltros = p.link && activo !== 'no' && aptoCredito !== 'no' && (calc._ok || precio === 0);

  if (!pasaFiltros) {
    score = 0;
  } else {
    score = 10; // Base para los que pasan filtros
  }

  if (calc._vsRef !== null && W.bajo_mercado.weight > 0) {
    if (calc._vsRef < -0.15) score += 15 * W.bajo_mercado.weight;
    else if (calc._vsRef < -0.05) score += 8 * W.bajo_mercado.weight;
    else if (calc._vsRef < 0) score += 3 * W.bajo_mercado.weight;
    else if (calc._vsRef > 0.15) score -= 5 * W.bajo_mercado.weight;
  }

  if (W.m2.weight > 0) {
    if (m2 >= 70) score += 4 * W.m2.weight;
    else if (m2 >= 50) score += 2 * W.m2.weight;
    else if (m2 >= 40) score += 1 * W.m2.weight;
  }

  if (p.terraza?.toLowerCase() === 'si') score += 10 * W.terraza.weight;
  if (p.balcon?.toLowerCase() === 'si') score += 10 * W.balcon.weight;
  if (parseInt(p.cocheras) > 0) score += 10 * W.cochera.weight;
  if (p.luminosidad?.toLowerCase() === 'si') score += 10 * W.luminosidad.weight;
  if (p.disposicion?.toLowerCase() === 'frente') score += 10 * W.frente.weight;

  score += calc._completeness * 3;
  calc._score = score;
  return calc;
}

function getProperties() {
  return parseCSV(state.rawData).map(calculateProperty);
}

function getFiltered(properties) {
  let result = [...properties];
  if (state.filterStatus !== 'todos') result = result.filter(p => p.status?.toLowerCase().includes(state.filterStatus.toLowerCase()));
  if (state.filterOk === 'ok') result = result.filter(p => p._ok);
  else if (state.filterOk === 'no') result = result.filter(p => !p._ok);
  if (state.filterBarrio !== 'todos') result = result.filter(p => p.barrio === state.filterBarrio);
  if (state.filterActivo === 'si') result = result.filter(p => p.activo?.toLowerCase() === 'si');
  else if (state.filterActivo === 'no') result = result.filter(p => p.activo?.toLowerCase() === 'no');
  result.sort((a, b) => {
    let va = a['_' + state.sortBy] ?? a[state.sortBy] ?? 0;
    let vb = b['_' + state.sortBy] ?? b[state.sortBy] ?? 0;
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    return state.sortDir === 'asc' ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
  });
  return result;
}

function getStats(properties) {
  return {
    total: properties.length,
    entran: properties.filter(p => p._ok).length,
    activos: properties.filter(p => p.activo?.toLowerCase() === 'si').length,
    porVer: properties.filter(p => p.status?.toLowerCase().includes('por ver')).length,
    minPrecio: properties.filter(p => p._precio > 0).length > 0 ? Math.min(...properties.filter(p => p._precio > 0).map(p => p._precio)) : 0,
    maxPrecio: properties.filter(p => p._precio > 0).length > 0 ? Math.max(...properties.filter(p => p._precio > 0).map(p => p._precio)) : 0,
  };
}

function escapeHtml(text) {
  if (!text) return '';
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function diasHace(fecha) {
  if (!fecha) return null;
  const hoy = new Date();
  const f = new Date(fecha);
  if (isNaN(f.getTime())) return null;
  const diff = Math.floor((hoy - f) / (1000 * 60 * 60 * 24));
  return diff;
}

// ============================================
// BADGES Y INDICADORES
// ============================================

function evalIcon(vsRef) {
  if (vsRef === null || vsRef === undefined) return '<span class="text-slate-300 text-xs italic">s/d</span>';
  const pct = Math.round(vsRef * 100);
  const sign = pct > 0 ? '+' : '';
  if (vsRef < -CONFIG.MARGEN_REF) return `<span class="text-green-600 text-xs font-medium" title="Bajo mercado">${sign}${pct}%</span>`;
  if (vsRef > CONFIG.MARGEN_REF) return `<span class="text-red-500 text-xs font-medium" title="Sobre mercado">${sign}${pct}%</span>`;
  return `<span class="text-yellow-600 text-xs" title="En mercado">${sign}${pct}%</span>`;
}

function okPill(ok) {
  return ok
    ? '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">✓</span>'
    : '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">✗</span>';
}

function activoBadge(activo) {
  if (!activo) return '<span class="text-slate-300">?</span>';
  const s = activo.toLowerCase();
  if (s === 'si') return '<span class="text-green-600 text-lg">✓</span>';
  if (s === 'no') return '<span class="text-red-600 text-lg">✗</span>';
  return `<span class="text-yellow-600">${activo}</span>`;
}

function aptoCreditoBadge(apto) {
  if (!apto) return '<span class="text-slate-300">?</span>';
  const s = apto.toLowerCase();
  if (s === 'si') return '<span class="text-green-600 text-lg">✓</span>';
  if (s === 'no') return '<span class="text-amber-600 text-lg">✗</span>';
  return `<span class="text-yellow-600">${apto}</span>`;
}

function statusBadge(status) {
  if (!status) return '<span class="text-slate-300 text-xs italic">status?</span>';
  const s = status.toLowerCase();
  if (s.includes('visitado')) return `<span class="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">${status}</span>`;
  if (s.includes('interesado')) return `<span class="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">${status}</span>`;
  if (s.includes('descartado')) return `<span class="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">${status}</span>`;
  return `<span class="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">${status}</span>`;
}

function ratingStars(rating) {
  if (!rating) return '-';
  const n = parseInt(rating) || 0;
  return '★'.repeat(n) + '☆'.repeat(5 - n);
}

function fechaIndicators(p) {
  const pubDias = diasHace(p.fecha_publicado);
  const trackDias = diasHace(p.fecha_agregado);
  let parts = [];
  if (pubDias !== null) parts.push(`📅${pubDias}d`);
  if (trackDias !== null) parts.push(`👁${trackDias}d`);
  if (parts.length === 0) return '';
  return `<div class="text-[10px] text-slate-400 mt-0.5">${parts.join(' · ')}</div>`;
}
