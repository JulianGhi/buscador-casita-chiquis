// ============================================
// UTILIDADES
// ============================================

// Score de atributos: penaliza datos faltantes, premia datos verificados
// "si" → +bonus, "no" → 0 (neutro, verificado), missing/"?"/"" → -penalidad
function scoreAtributo(valor, peso, bonusSi = 10, penaltyMissing = 5) {
  if (peso <= 0) return { score: 0, status: 'disabled' };
  const v = (valor || '').toLowerCase().trim();
  if (v === 'si' || v === 'sí') return { score: bonusSi * peso, status: 'si' };
  if (v === 'no') return { score: 0, status: 'no' }; // Verificado que no tiene
  return { score: -penaltyMissing * peso, status: 'missing' }; // Desconocido
}

// Score de atributo numérico (cocheras)
function scoreNumerico(valor, peso, bonusPositivo = 10, penaltyMissing = 5) {
  if (peso <= 0) return { score: 0, status: 'disabled' };
  const num = parseInt(valor);
  if (!isNaN(num)) {
    if (num > 0) return { score: bonusPositivo * peso, status: 'si' };
    return { score: 0, status: 'no' }; // cocheras=0 es verificado
  }
  return { score: -penaltyMissing * peso, status: 'missing' };
}

// Score de disposición (frente/contrafrente/interno)
function scoreDisposicion(valor, peso, bonusFront = 10, penaltyMissing = 5) {
  if (peso <= 0) return { score: 0, status: 'disabled' };
  const v = (valor || '').toLowerCase().trim();
  if (v === 'frente') return { score: bonusFront * peso, status: 'si' };
  if (v === 'contrafrente' || v === 'interno' || v === 'lateral') return { score: 0, status: 'no' };
  return { score: -penaltyMissing * peso, status: 'missing' };
}

// Score de ambientes: 4+ = muy bien, 3 = bien, <3 = neutro
function scoreAmbientes(valor, peso, penaltyMissing = 3) {
  if (peso <= 0) return { score: 0, status: 'disabled' };
  const num = parseInt(valor);
  if (!isNaN(num) && num > 0) {
    if (num >= 4) return { score: 8 * peso, status: 'si' };
    if (num >= 3) return { score: 4 * peso, status: 'ok' };
    return { score: 0, status: 'no' }; // 2 o menos
  }
  return { score: -penaltyMissing * peso, status: 'missing' };
}

// Score de baños: 2+ = bonus, 1 = neutro
function scoreBanos(valor, peso, penaltyMissing = 3) {
  if (peso <= 0) return { score: 0, status: 'disabled' };
  const num = parseInt(valor);
  if (!isNaN(num) && num > 0) {
    if (num >= 2) return { score: 6 * peso, status: 'si' };
    return { score: 0, status: 'no' }; // 1 baño
  }
  return { score: -penaltyMissing * peso, status: 'missing' };
}

// Score de antigüedad: nuevo = mejor, viejo = peor
function scoreAntiguedad(valor, peso, penaltyMissing = 3) {
  if (peso <= 0) return { score: 0, status: 'disabled' };
  const num = parseInt(valor);
  if (!isNaN(num)) {
    if (num === 0) return { score: 10 * peso, status: 'si' }; // A estrenar
    if (num <= 15) return { score: 6 * peso, status: 'si' };
    if (num <= 30) return { score: 3 * peso, status: 'ok' };
    if (num <= 50) return { score: 0, status: 'no' };
    return { score: -3 * peso, status: 'no' }; // >50 años
  }
  return { score: -penaltyMissing * peso, status: 'missing' };
}

// Score de expensas: bajas = bonus, altas = penalty
function scoreExpensas(valor, peso, penaltyMissing = 2) {
  if (peso <= 0) return { score: 0, status: 'disabled' };
  const num = parseInt(valor);
  if (!isNaN(num)) {
    if (num === 0) return { score: 8 * peso, status: 'si' }; // Sin expensas
    if (num <= 80) return { score: 5 * peso, status: 'si' };
    if (num <= 150) return { score: 2 * peso, status: 'ok' };
    if (num <= 250) return { score: 0, status: 'no' };
    return { score: -4 * peso, status: 'no' }; // >250 (muy altas)
  }
  return { score: -penaltyMissing * peso, status: 'missing' };
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

  // Score de candidato con sistema de tiers
  // Tier determina el orden principal, score es secundario dentro del tier
  let score = 0;
  let tier = 4; // Peor tier por defecto
  const activo = (p.activo || '').toLowerCase();
  const aptoCredito = (p.apto_credito || '').toLowerCase();
  const W = WEIGHTS;
  const C = CONDITIONS;

  // Evaluar condiciones
  const esActivo = activo === 'si';
  const esAptoCredito = aptoCredito === 'si';
  const noSabemosCredito = aptoCredito === '' || aptoCredito === '?';
  const noAptoCredito = aptoCredito === 'no';
  const dentroPresupuesto = calc._ok || precio === 0;
  const tieneLink = !!p.link;

  // Sistema de Tiers (orden estricto de prioridad):
  // Tier 1: activo + apto_credito=si + dentro presupuesto (los mejores)
  // Tier 2: activo + apto_credito=si + fuera presupuesto (buenos pero caros)
  // Tier 3: activo + apto_credito=? (hay que averiguar)
  // Tier 4: activo + apto_credito=no (no aceptan crédito)
  // Tier 5: no activo o sin link (descartados)

  if (!tieneLink || !esActivo) {
    tier = 5;
    score = 0;
  } else if (esAptoCredito && dentroPresupuesto) {
    tier = 1;
    score = 100; // Base alta para tier 1
  } else if (esAptoCredito && !dentroPresupuesto) {
    tier = 2;
    score = 80; // Apto pero caro
  } else if (noSabemosCredito) {
    tier = 3;
    score = 50; // Hay que averiguar
  } else if (noAptoCredito) {
    tier = 4;
    score = 25; // No apto crédito
  }

  // Si CONDITIONS.apto_credito está deshabilitado, ignorar apto_credito en tiers
  if (C.apto_credito && !C.apto_credito.enabled && tier >= 1 && tier <= 4) {
    // Reagrupar: solo importa activo + presupuesto
    if (dentroPresupuesto) {
      tier = 1;
      score = 100;
    } else {
      tier = 2;
      score = 80;
    }
  }

  // Si CONDITIONS.ok_presupuesto está deshabilitado, ignorar presupuesto en tiers
  if (C.ok_presupuesto && !C.ok_presupuesto.enabled && tier >= 1 && tier <= 4) {
    // Reagrupar: solo importa activo + apto_credito
    if (esAptoCredito) {
      tier = 1;
      score = 100;
    } else if (noSabemosCredito) {
      tier = 2;
      score = 80;
    } else {
      tier = 3;
      score = 50;
    }
  }

  // Scoring de atributos con penalización por datos faltantes
  // Guardamos detalles para debugging/transparencia
  const attrScores = {};

  // Helper: peso efectivo (0 si deshabilitado)
  const getWeight = (key) => W[key].enabled ? W[key].weight : 0;

  // Bajo mercado: solo si tenemos datos para calcular
  const wBajo = getWeight('bajo_mercado');
  if (calc._vsRef !== null && wBajo > 0) {
    if (calc._vsRef < -0.15) score += 15 * wBajo;
    else if (calc._vsRef < -0.05) score += 8 * wBajo;
    else if (calc._vsRef < 0) score += 3 * wBajo;
    else if (calc._vsRef > 0.15) score -= 5 * wBajo;
  }

  // M2: bonus por tamaño, penalidad si no sabemos
  const wM2 = getWeight('m2');
  if (wM2 > 0) {
    if (m2 >= 70) { score += 4 * wM2; attrScores.m2 = 'si'; }
    else if (m2 >= 50) { score += 2 * wM2; attrScores.m2 = 'si'; }
    else if (m2 >= 40) { score += 1 * wM2; attrScores.m2 = 'ok'; }
    else if (m2 > 0) { attrScores.m2 = 'no'; } // Verificado pero chico
    else { score -= 3 * wM2; attrScores.m2 = 'missing'; } // Sin datos
  }

  // Atributos numéricos con escalas específicas
  const ambientes = scoreAmbientes(p.amb, getWeight('ambientes'));
  score += ambientes.score; attrScores.ambientes = ambientes.status;

  const banos = scoreBanos(p.banos, getWeight('banos'));
  score += banos.score; attrScores.banos = banos.status;

  const antiguedad = scoreAntiguedad(p.antiguedad, getWeight('antiguedad'));
  score += antiguedad.score; attrScores.antiguedad = antiguedad.status;

  const expensas = scoreExpensas(p.expensas, getWeight('expensas'));
  score += expensas.score; attrScores.expensas = expensas.status;

  // Atributos booleanos: si/no/missing
  const terraza = scoreAtributo(p.terraza, getWeight('terraza'));
  score += terraza.score; attrScores.terraza = terraza.status;

  const balcon = scoreAtributo(p.balcon, getWeight('balcon'));
  score += balcon.score; attrScores.balcon = balcon.status;

  const cochera = scoreNumerico(p.cocheras, getWeight('cochera'));
  score += cochera.score; attrScores.cochera = cochera.status;

  const luminosidad = scoreAtributo(p.luminosidad, getWeight('luminosidad'));
  score += luminosidad.score; attrScores.luminosidad = luminosidad.status;

  const frente = scoreDisposicion(p.disposicion, getWeight('frente'));
  score += frente.score; attrScores.frente = frente.status;

  // Contar datos faltantes para mostrar en UI
  const missingCount = Object.values(attrScores).filter(s => s === 'missing').length;
  calc._attrScores = attrScores;
  calc._missingCount = missingCount;

  calc._score = score;
  calc._tier = tier;
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

function tierBadge(tier) {
  const colors = {
    1: 'bg-green-100 text-green-700',
    2: 'bg-blue-100 text-blue-700',
    3: 'bg-yellow-100 text-yellow-700',
    4: 'bg-orange-100 text-orange-700',
    5: 'bg-red-100 text-red-700 opacity-60'
  };
  const labels = { 1: 'T1', 2: 'T2', 3: 'T3', 4: 'T4', 5: 'T5' };
  const titles = {
    1: 'Activo + Apto crédito + OK$',
    2: 'Activo + Apto crédito + Caro',
    3: 'Activo + Crédito?',
    4: 'Activo + No apto crédito',
    5: 'Inactivo'
  };
  const color = colors[tier] || 'bg-slate-100 text-slate-500';
  return `<span class="text-[10px] ${color} px-1 py-0.5 rounded font-medium" title="${titles[tier] || ''}">${labels[tier] || '?'}</span>`;
}

function ratingStars(rating) {
  if (!rating) return '-';
  const n = parseInt(rating) || 0;
  return '★'.repeat(n) + '☆'.repeat(5 - n);
}

function fechaIndicators(p) {
  const pubDias = diasHace(p.fecha_publicado);
  if (pubDias === null) return '';
  return `<div class="text-[10px] text-slate-400 mt-0.5">📅${pubDias}d</div>`;
}
