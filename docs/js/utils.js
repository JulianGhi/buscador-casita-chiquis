// ============================================
// UTILIDADES
// ============================================

// Ajusta el padding del contenido para compensar el header fijo
function updateContentPadding() {
  requestAnimationFrame(() => {
    const header = document.querySelector('header');
    const content = document.querySelector('.main-content');
    if (header && content) {
      content.style.paddingTop = (header.offsetHeight + 16) + 'px';
    }
  });
}

// ============================================
// SISTEMA DE SCORING UNIFICADO
// Usa SCORING_RULES de config.js
// ============================================

function scoreAttribute(key, valor, peso) {
  if (peso <= 0) return { score: 0, status: 'disabled' };
  const rule = SCORING_RULES[key];
  if (!rule) return { score: 0, status: 'unknown' };

  const v = (valor || '').toLowerCase().trim();
  const num = parseInt(valor);
  const hasNum = !isNaN(num);

  switch (rule.type) {
    case 'boolean':
      if (v === 'si' || v === 'sí') return { score: rule.bonus * peso, status: 'si' };
      if (v === 'no') return { score: 0, status: 'no' };
      return { score: -rule.penaltyMissing * peso, status: 'missing' };

    case 'numeric':
      if (hasNum) {
        if (num > 0) return { score: rule.bonus * peso, status: 'si' };
        return { score: 0, status: 'no' };
      }
      return { score: -rule.penaltyMissing * peso, status: 'missing' };

    case 'disposicion':
      if (v === 'frente') return { score: rule.bonus * peso, status: 'si' };
      if (v === 'contrafrente' || v === 'interno' || v === 'lateral') return { score: 0, status: 'no' };
      return { score: -rule.penaltyMissing * peso, status: 'missing' };

    case 'threshold':
      if (hasNum && num > 0) {
        for (const t of rule.thresholds) {
          if (num >= t.min) return { score: t.score * peso, status: t.score > 3 ? 'si' : 'ok' };
        }
        return { score: 0, status: 'no' };
      }
      return { score: -rule.penaltyMissing * peso, status: 'missing' };

    case 'range':
      if (hasNum) {
        for (const r of rule.ranges) {
          if (r.max !== undefined && num <= r.max) return { score: r.score * peso, status: r.score > 0 ? 'si' : 'no' };
          if (r.min !== undefined && num >= r.min) return { score: r.score * peso, status: 'no' };
        }
        return { score: 0, status: 'ok' };
      }
      return { score: -rule.penaltyMissing * peso, status: 'missing' };

    case 'vsRef':
      // Handled separately in calculateProperty
      return { score: 0, status: 'special' };

    default:
      return { score: 0, status: 'unknown' };
  }
}

// Calcula score de precio vs referencia del barrio
function scoreVsRef(vsRef, peso) {
  if (peso <= 0 || vsRef === null) return 0;
  const rule = SCORING_RULES.bajo_mercado;
  for (const r of rule.ranges) {
    if (r.max !== undefined && vsRef <= r.max) return r.score * peso;
    if (r.min !== undefined && vsRef >= r.min) return r.score * peso;
  }
  return 0;
}

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

// ============================================
// CÁLCULO DE COSTOS (reutilizable)
// ============================================
function calculateCosts(precio, options = {}) {
  const {
    tieneInmob = false,
    dolar = null,
    negociacionPct = 0
  } = options;

  const creditoUSD = getCreditoUSD(dolar);
  const precioFinal = Math.round(precio * (1 - negociacionPct / 100));

  const tu10 = Math.max(precioFinal - creditoUSD, precioFinal * 0.1);
  const escr = Math.round(precioFinal * CONFIG.ESCRIBANO);
  const sell = precioFinal <= CONFIG.SELLOS_EXENTO ? 0 : Math.round(precioFinal * CONFIG.SELLOS);
  const reg = Math.round(precioFinal * CONFIG.REGISTRALES);
  const inmob = tieneInmob ? Math.round(precioFinal * CONFIG.INMOB) : 0;
  const hip = Math.round(precioFinal * CONFIG.HIPOTECA);
  const cert = CONFIG.CERTIFICADOS;
  const total = tu10 + escr + sell + reg + inmob + hip + cert;

  return {
    precio: precioFinal,
    creditoUSD,
    tu10, escr, sell, reg, inmob, hip, cert, total,
    ok: total <= CONFIG.PRESUPUESTO,
    dif: CONFIG.PRESUPUESTO - total
  };
}

// Calcula quita necesaria para entrar en presupuesto
function calculateQuitaNecesaria(precio, tieneInmob = false, dolar = null) {
  const creditoUSD = getCreditoUSD(dolar);
  const costosRate = CONFIG.ESCRIBANO + CONFIG.SELLOS + CONFIG.REGISTRALES +
                     (tieneInmob ? CONFIG.INMOB : 0) + CONFIG.HIPOTECA;

  const precioTarget1 = (CONFIG.PRESUPUESTO + creditoUSD - CONFIG.CERTIFICADOS) / (1 + costosRate);
  const precioTarget2 = (CONFIG.PRESUPUESTO - CONFIG.CERTIFICADOS) / (0.1 + costosRate);
  const umbral = creditoUSD / 0.9;
  const precioTarget = precioTarget1 > umbral ? precioTarget1 : precioTarget2;

  const quitaPct = precio > 0 ? Math.max(0, ((precio - precioTarget) / precio) * 100) : 0;
  const quitaUSD = Math.round(precio - precioTarget);

  return {
    precioTarget: Math.round(precioTarget),
    quitaPct,
    quitaUSD,
    esRealista: quitaPct > 0 && quitaPct <= 20
  };
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

// Detecta si es venta directa (sin comisión inmobiliaria)
function esVentaDirecta(inmobiliaria) {
  const text = (inmobiliaria || '').toLowerCase();
  return text.includes('direct') || text.includes('dueño') || text.includes('particular');
}

function calculateProperty(p) {
  const precio = parseFloat(p.precio) || 0;
  const m2 = parseFloat(p.m2_cub) || 0;
  const barrio = p.barrio;
  // Asumir siempre inmobiliaria EXCEPTO si explícitamente es venta directa
  const tieneInmob = !esVentaDirecta(p.inmobiliaria);

  // Usar calculateCosts para costos (con negociación global si está configurada)
  const costs = calculateCosts(precio, { tieneInmob, negociacionPct: CONFIG.NEGOCIACION || 0 });

  // Calcular datos básicos
  const expensas = parseFloat(p.expensas) || 0;

  const precioNeg = costs.precio;  // precio con negociación aplicada
  const antiguedad = parseFloat(p.antiguedad) || null;

  // Calcular si es nueva (agregada en últimos N días - configurable)
  const diasAgregado = diasHace(p.fecha_agregado);
  const esNueva = diasAgregado !== null && diasAgregado <= (CONFIG.DIAS_NUEVA || 7);

  // Calcular si se vendió recientemente (inactiva + fecha_inactivo en últimos N días)
  const diasInactivo = diasHace(p.fecha_inactivo);
  const vendidaReciente = (p.activo || '').toLowerCase() === 'no' && diasInactivo !== null && diasInactivo <= (CONFIG.DIAS_VENDIDA_RECIENTE || 7);

  const calc = {
    ...p,
    _precio: precio,
    _precioNeg: precioNeg,
    _hayNeg: CONFIG.NEGOCIACION > 0,
    _m2: m2,
    _expensas: expensas,
    _antiguedad: antiguedad,
    _esNueva: esNueva,
    _vendidaReciente: vendidaReciente,
    _preciom2: m2 > 0 ? Math.round(precio / m2) : 0,
    _ref: REF_M2[barrio] || 0,
    // Costos (de calculateCosts)
    _tu10: costs.tu10,
    _escr: costs.escr,
    _sell: costs.sell,
    _reg: costs.reg,
    _inmob: costs.inmob,
    _hip: costs.hip,
    _cert: costs.cert,
    _total: costs.total,
    _ok: costs.ok,
    _dif: costs.dif,
    _completeness: [p.direccion, p.barrio, precio > 0, m2 > 0].filter(Boolean).length
  };

  calc._vsRef = (calc._preciom2 > 0 && calc._ref > 0) ? (calc._preciom2 - calc._ref) / calc._ref : null;

  // === SISTEMA DE TIERS ===
  const activo = (p.activo || '').toLowerCase();
  const aptoCredito = (p.apto_credito || '').toLowerCase();
  const C = CONDITIONS;

  const esActivo = activo === 'si';
  const esAptoCredito = aptoCredito === 'si';
  const noSabemosCredito = aptoCredito === '' || aptoCredito === '?';
  const noAptoCredito = aptoCredito === 'no';
  const dentroPresupuesto = calc._ok || precio === 0;
  const tieneLink = !!p.link;

  let tier = 4;
  let score = 0;

  // Determinar tier
  if (!tieneLink || !esActivo) {
    tier = 5; score = 0;
  } else if (esAptoCredito && dentroPresupuesto) {
    tier = 1; score = 100;
  } else if (esAptoCredito && !dentroPresupuesto) {
    tier = 2; score = 80;
  } else if (noSabemosCredito) {
    tier = 3; score = 50;
  } else if (noAptoCredito) {
    tier = 4; score = 25;
  }

  // Ajustar tier si condiciones están deshabilitadas
  if (C.apto_credito && !C.apto_credito.enabled && tier >= 1 && tier <= 4) {
    tier = dentroPresupuesto ? 1 : 2;
    score = dentroPresupuesto ? 100 : 80;
  }
  if (C.ok_presupuesto && !C.ok_presupuesto.enabled && tier >= 1 && tier <= 4) {
    if (esAptoCredito) { tier = 1; score = 100; }
    else if (noSabemosCredito) { tier = 2; score = 80; }
    else { tier = 3; score = 50; }
  }

  // === SCORING DE ATRIBUTOS ===
  const getWeight = (key) => WEIGHTS[key]?.enabled ? WEIGHTS[key].weight : 0;
  const attrScores = {};

  // Bajo mercado (caso especial)
  score += scoreVsRef(calc._vsRef, getWeight('bajo_mercado'));

  // M2 (usa reglas de threshold)
  const m2Score = scoreAttribute('m2', m2 > 0 ? m2.toString() : '', getWeight('m2'));
  score += m2Score.score; attrScores.m2 = m2Score.status;

  // Mapeo de campos a reglas de scoring
  const attrMapping = {
    ambientes: p.amb,
    banos: p.banos,
    antiguedad: p.antiguedad,
    expensas: p.expensas,
    terraza: p.terraza,
    balcon: p.balcon,
    cochera: p.cocheras,
    luminosidad: p.luminosidad,
    frente: p.disposicion
  };

  for (const [key, valor] of Object.entries(attrMapping)) {
    const result = scoreAttribute(key, valor, getWeight(key));
    score += result.score;
    attrScores[key] = result.status;
  }

  calc._attrScores = attrScores;
  calc._missingCount = Object.values(attrScores).filter(s => s === 'missing').length;
  calc._score = score;
  calc._tier = tier;

  return calc;
}

function getProperties() {
  return parseCSV(state.rawData).map(calculateProperty);
}

function getFiltered(properties) {
  let result = [...properties];

  // Filtros básicos
  if (state.filterStatus !== 'todos') result = result.filter(p => p.status?.toLowerCase().includes(state.filterStatus.toLowerCase()));
  if (state.filterOk === 'ok') result = result.filter(p => p._ok);
  else if (state.filterOk === 'no') result = result.filter(p => !p._ok);
  if (state.filterBarrio !== 'todos') result = result.filter(p => p.barrio === state.filterBarrio);
  if (state.filterActivo === 'si') result = result.filter(p => p.activo?.toLowerCase() === 'si');
  else if (state.filterActivo === 'no') result = result.filter(p => p.activo?.toLowerCase() === 'no');

  // Filtro por tier
  if (state.filterTier !== 'todos') {
    const tierNum = parseInt(state.filterTier);
    result = result.filter(p => p._tier === tierNum);
  }

  // Filtro apto crédito
  if (state.filterCredito === 'si') result = result.filter(p => p.apto_credito?.toLowerCase() === 'si');
  else if (state.filterCredito === 'no') result = result.filter(p => p.apto_credito?.toLowerCase() === 'no');
  else if (state.filterCredito === '?') result = result.filter(p => !p.apto_credito || p.apto_credito === '?');

  // Filtros booleanos (atributos)
  const boolFilter = (field, stateVal) => {
    if (stateVal === 'si') return p => p[field]?.toLowerCase() === 'si';
    if (stateVal === 'no') return p => p[field]?.toLowerCase() === 'no';
    return null;
  };
  if (state.filterTerraza !== 'todos') result = result.filter(boolFilter('terraza', state.filterTerraza));
  if (state.filterBalcon !== 'todos') result = result.filter(boolFilter('balcon', state.filterBalcon));
  if (state.filterCochera !== 'todos') result = result.filter(boolFilter('cochera', state.filterCochera));
  if (state.filterLuminoso !== 'todos') result = result.filter(boolFilter('luminosidad', state.filterLuminoso));

  // Búsqueda por texto (dirección, notas, barrio)
  if (state.searchText?.trim()) {
    const q = state.searchText.toLowerCase().trim();
    result = result.filter(p =>
      p.direccion?.toLowerCase().includes(q) ||
      p.notas?.toLowerCase().includes(q) ||
      p.barrio?.toLowerCase().includes(q)
    );
  }

  result.sort((a, b) => {
    // Ordenamiento especial para 'score': primero por tier (menor = mejor), luego por score
    if (state.sortBy === 'score') {
      if (a._tier !== b._tier) {
        return state.sortDir === 'asc' ? (b._tier - a._tier) : (a._tier - b._tier);
      }
      // Dentro del mismo tier, ordenar por score
      return state.sortDir === 'asc' ? (a._score - b._score) : (b._score - a._score);
    }
    // Ordenamiento normal para otros campos
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

// Formatea días en texto amigable ("hace 2 meses", "hace 5 días")
function formatTiempoHace(dias) {
  if (dias === null || dias === undefined) return null;
  if (dias === 0) return 'hoy';
  if (dias === 1) return 'ayer';
  if (dias < 7) return `hace ${dias}d`;
  if (dias < 30) return `hace ${Math.floor(dias / 7)}sem`;
  if (dias < 365) return `hace ${Math.floor(dias / 30)}m`;
  return `hace ${Math.floor(dias / 365)}a`;
}

// Formatea una fecha como tiempo relativo
function fechaRelativa(fecha) {
  const dias = diasHace(fecha);
  return formatTiempoHace(dias);
}

// ============================================
// BADGES Y INDICADORES
// ============================================

// Determina el color de fondo de una fila de la tabla basado en su estado
function getRowBgColor(p) {
  const activo = (p.activo || '').toLowerCase();
  const apto = (p.apto_credito || '').toLowerCase();

  // Inactivo = rojo desaturado
  if (activo === 'no') return `${THEME.error.bg}/70 opacity-60`;

  // Datos por verificar (activo o apto dudoso) pero entra en presupuesto
  if ((activo === '?' || apto === '?' || !apto) && p._ok) {
    return `${THEME.warning.bg.replace('100', '200')}/70 border-l-4 border-yellow-500`;
  }

  // No apto crédito
  if (apto === 'no') return THEME.warning.bg;

  // OK presupuesto = verde suave
  if (p._ok) return `${THEME.success.bg}/30`;

  return '';
}

// Función genérica para badges de si/no/?
function booleanBadge(value, options = {}) {
  const { noColor = THEME.error.textLight, size = 'text-lg' } = options;
  if (!value) return `<span class="text-slate-300">${ICONS.question}</span>`;
  const s = value.toLowerCase();
  if (s === 'si' || s === 'sí') return `<span class="${THEME.success.textLight} ${size}">${ICONS.check}</span>`;
  if (s === 'no') return `<span class="${noColor} ${size}">${ICONS.cross}</span>`;
  return `<span class="${THEME.warning.textLight}">${value}</span>`;
}

// Función para colorear variaciones porcentuales (positivo=rojo, negativo=verde)
function variacionColor(valor) {
  const num = parseFloat(valor);
  if (isNaN(num) || num === 0) return 'text-slate-400';
  return num > 0 ? 'text-red-400' : 'text-green-400';
}

function evalIcon(vsRef) {
  if (vsRef === null || vsRef === undefined) return '<span class="text-slate-300 text-xs italic">s/d</span>';
  const pct = Math.round(vsRef * 100);
  const sign = pct > 0 ? '+' : '';
  if (vsRef < -CONFIG.MARGEN_REF) return `<span class="text-green-600 text-xs font-medium" title="Bajo mercado">${sign}${pct}%</span>`;
  if (vsRef > CONFIG.MARGEN_REF) return `<span class="text-red-500 text-xs font-medium" title="Sobre mercado">${sign}${pct}%</span>`;
  return `<span class="text-yellow-600 text-xs" title="En mercado">${sign}${pct}%</span>`;
}

function okPill(ok) {
  const t = ok ? THEME.success : THEME.error;
  const icon = ok ? ICONS.check : ICONS.cross;
  return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${t.bg} ${t.textDark}">${icon}</span>`;
}

function activoBadge(activo) {
  return booleanBadge(activo, { noColor: THEME.error.textLight });
}

function aptoCreditoBadge(apto) {
  return booleanBadge(apto, { noColor: 'text-amber-600' });
}

// Badge de status usando STATUS_CONFIG
function statusBadge(status) {
  if (!status) return '<span class="text-slate-300 text-xs italic">status?</span>';
  const s = status.toLowerCase();

  // Buscar config por coincidencia parcial
  let config = STATUS_CONFIG.default;
  for (const [key, cfg] of Object.entries(STATUS_CONFIG)) {
    if (key !== 'default' && s.includes(key)) {
      config = cfg;
      break;
    }
  }

  const theme = THEME[config.theme];
  return `<span class="text-xs ${theme.bg} ${theme.text} px-1.5 py-0.5 rounded">${status}</span>`;
}

function tierBadge(tier) {
  const cfg = TIER_CONFIG[tier] || { css: 'bg-slate-100 text-slate-500', label: '?', title: '' };
  return `<span class="text-[10px] ${cfg.css} px-1 py-0.5 rounded font-medium" title="${cfg.title}">${cfg.label}</span>`;
}

function printBadge(fechaPrint) {
  if (!fechaPrint) {
    return `<span class="text-slate-300" title="Sin backup PDF">○</span>`;
  }
  // Calcular días desde el print
  const printDate = new Date(fechaPrint);
  const today = new Date();
  const dias = Math.floor((today - printDate) / (1000 * 60 * 60 * 24));

  if (dias > 30) {
    return `<span class="text-amber-500" title="Print desactualizado (${dias}d)">📄</span>`;
  }
  return `<span class="text-green-600" title="Print OK (${fechaPrint})">📄</span>`;
}

function ratingStars(rating) {
  if (!rating) return '-';
  const n = parseInt(rating) || 0;
  return '★'.repeat(n) + '☆'.repeat(5 - n);
}

function fechaIndicators(p) {
  const badges = [];
  const items = [];

  // Badge de nueva (agregada en últimos 7 días)
  if (p._esNueva) badges.push('<span class="text-[10px] bg-green-500 text-white px-1 rounded">NUEVA</span>');

  // Badge de vendida recientemente
  if (p._vendidaReciente) badges.push('<span class="text-[10px] bg-purple-500 text-white px-1 rounded">VENDIDA</span>');

  // Publicado (cuánto tiempo lleva el aviso online)
  const pubRel = fechaRelativa(p.fecha_publicado);
  if (pubRel) items.push(`${ICONS.calendar}${pubRel}`);

  // Agregado (cuánto tiempo lo estás siguiendo)
  const agrRel = fechaRelativa(p.fecha_agregado);
  if (agrRel) items.push(`➕${agrRel}`);

  const badgeHtml = badges.length ? `<div class="flex gap-1 mt-0.5">${badges.join('')}</div>` : '';
  const itemsHtml = items.length ? `<div class="text-[10px] text-slate-400 mt-0.5">${items.join(' · ')}</div>` : '';

  return badgeHtml + itemsHtml;
}
