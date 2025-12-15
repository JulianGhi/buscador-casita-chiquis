// ============================================
// STATS - LÓGICA ESPECÍFICA
// ============================================
// Nota: updateContentPadding() está en utils.js (compartido)

let chart = null;
let scoreChart = null;
let allProperties = [];
let statsFilters = {
  activo: 'todos',       // 'todos', 'activos', 'inactivos'
  showNoAptoCredito: true,
  tipo: 'todos',
  barrios: new Set()     // empty = all
};

// ============================================
// FILTROS
// ============================================

function setActivoFilter(filter) {
  statsFilters.activo = filter;
  ['btnTodos', 'btnActivos', 'btnInactivos'].forEach(id => {
    const btn = document.getElementById(id);
    if (!btn) return;
    const isActive = (id === 'btnTodos' && filter === 'todos') ||
                    (id === 'btnActivos' && filter === 'activos') ||
                    (id === 'btnInactivos' && filter === 'inactivos');
    btn.className = isActive
      ? 'px-3 py-1 text-sm rounded-md bg-white shadow-sm text-slate-700'
      : 'px-3 py-1 text-sm rounded-md text-slate-600 hover:bg-white/50';
  });
  renderStatsPage();
}

function toggleAptoCredito(checked) {
  statsFilters.showNoAptoCredito = checked;
  renderStatsPage();
}

function setTipoFilter(tipo) {
  statsFilters.tipo = tipo;
  renderStatsPage();
}

function toggleBarrioDropdown() {
  document.getElementById('barrioDropdown').classList.toggle('hidden');
}

function toggleAllBarrios(checked) {
  const checkboxes = document.querySelectorAll('#barrioCheckboxes input[type="checkbox"]');
  checkboxes.forEach(cb => cb.checked = checked);
  statsFilters.barrios = checked ? new Set() : new Set(['__none__']);
  updateBarrioLabel();
  renderStatsPage();
}

function toggleBarrio(barrio, checked) {
  if (statsFilters.barrios.size === 0) {
    const allBarrios = [...new Set(allProperties.map(p => p.barrio).filter(Boolean))];
    statsFilters.barrios = new Set(allBarrios);
  }
  if (checked) {
    statsFilters.barrios.add(barrio);
  } else {
    statsFilters.barrios.delete(barrio);
  }
  const allBarrios = [...new Set(allProperties.map(p => p.barrio).filter(Boolean))];
  if (statsFilters.barrios.size === allBarrios.length) {
    statsFilters.barrios = new Set();
  }
  updateBarrioLabel();
  renderStatsPage();
}

function updateBarrioLabel() {
  const label = document.getElementById('barrioFilterLabel');
  if (!label) return;
  if (statsFilters.barrios.size === 0) {
    label.textContent = 'Todos los barrios';
  } else if (statsFilters.barrios.size === 1) {
    label.textContent = [...statsFilters.barrios][0];
  } else {
    label.textContent = `${statsFilters.barrios.size} barrios`;
  }
}

function getStatsFiltered() {
  return allProperties.filter(p => {
    const activo = (p.activo || '').toLowerCase();
    if (statsFilters.activo === 'activos' && activo !== 'si') return false;
    if (statsFilters.activo === 'inactivos' && activo !== 'no') return false;

    if (!statsFilters.showNoAptoCredito) {
      const aptoCredito = (p.apto_credito || '').toLowerCase();
      if (aptoCredito !== 'si') return false;
    }

    if (statsFilters.tipo !== 'todos') {
      const tipo = (p.tipo || '').toLowerCase();
      if (tipo !== statsFilters.tipo) return false;
    }

    if (statsFilters.barrios.size > 0 && !statsFilters.barrios.has(p.barrio)) return false;

    return true;
  });
}

// ============================================
// RENDER STATS PAGE
// ============================================

function renderStatsPage() {
  const filtered = getStatsFiltered();
  const stats = getStats(allProperties);

  // Render header
  document.getElementById('headerContainer').innerHTML = renderHeader(stats, 'stats');

  // Update filter count
  const filterCount = document.getElementById('filterCount');
  if (filterCount) {
    filterCount.textContent = filtered.length === allProperties.length
      ? ''
      : `${filtered.length} de ${allProperties.length} propiedades`;
  }

  // Render charts and stats
  renderChart(filtered);
  renderScoreChart(filtered);
  renderStatsGrid(filtered);

  updateContentPadding();
}

function renderBarrioCheckboxes() {
  const barrios = [...new Set(allProperties.map(p => p.barrio).filter(Boolean))].sort();
  const container = document.getElementById('barrioCheckboxes');
  if (!container) return;
  container.innerHTML = barrios.map(barrio => `
    <label class="flex items-center gap-2 px-2 py-1 hover:bg-slate-50 rounded cursor-pointer">
      <input type="checkbox" checked onchange="toggleBarrio('${escapeHtml(barrio)}', this.checked)" class="rounded text-blue-500">
      <span class="text-sm">${escapeHtml(barrio)}</span>
    </label>
  `).join('');
}

// ============================================
// HELPERS DE CHART (usa TIER_CONFIG y CHART_CONFIG de config.js)
// ============================================

// Extrae datos de propiedades para scatter plots
function toChartData(properties) {
  return properties
    .filter(p => p._precio > 0 && p._m2 > 0)
    .map(p => ({
      x: p._m2,
      y: p._precio,
      label: p.direccion || 'Sin dirección',
      barrio: p.barrio || 'Sin barrio',
      preciom2: p._preciom2,
      vsRef: p._vsRef,
      tier: p._tier || 5,
      score: p._score || 0,
      link: p.link || null
    }));
}

// Regresión lineal simple
function linearRegression(data, xKey = 'x') {
  const n = data.length;
  if (n < 2) return [];

  const sum = (arr, fn) => arr.reduce((a, b) => a + fn(b), 0);
  const sumX = sum(data, d => d[xKey]);
  const sumY = sum(data, d => d.y);
  const sumXY = sum(data, d => d[xKey] * d.y);
  const sumX2 = sum(data, d => d[xKey] ** 2);

  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX ** 2);
  const intercept = (sumY - slope * sumX) / n;

  const xs = data.map(d => d[xKey]);
  return [
    { x: Math.min(...xs), y: slope * Math.min(...xs) + intercept },
    { x: Math.max(...xs), y: slope * Math.max(...xs) + intercept }
  ];
}

// Genera tooltip con info de propiedad
function chartTooltip(d, showM2 = true) {
  const tierCfg = TIER_CONFIG[d.tier];
  const vsRefStr = d.vsRef != null ? ` (${formatPctSign(Math.round(d.vsRef * 100))} vs barrio)` : '';

  const lines = [d.label, d.barrio];
  lines.push(showM2 ? `${fmt(d.y)} · ${d.x}m²` : fmt(d.y));
  if (showM2) lines.push(`${fmt(d.preciom2)}/m²${vsRefStr}`);
  lines.push(`${tierCfg.label} ${tierCfg.name} · Score: ${d.score}`);
  if (d.link) lines.push(`${ICONS.external} Click para ver aviso`);
  return lines;
}

// Abre link al hacer click en punto
function onPointClick(event, elements, chart) {
  if (!elements.length || elements[0].datasetIndex !== 0) return;
  const point = chart.data.datasets[0].data[elements[0].index];
  if (point.link) window.open(point.link, '_blank');
}

// Crea dataset de propiedades con estilos por tier
function createPropertiesDataset(data) {
  return {
    label: 'Propiedades',
    data: data,
    backgroundColor: data.map(d => TIER_CONFIG[d.tier].chart.bg),
    borderColor: data.map(d => TIER_CONFIG[d.tier].chart.border),
    borderWidth: data.map(d => TIER_CONFIG[d.tier].borderWidth),
    pointRadius: data.map(d => TIER_CONFIG[d.tier].pointRadius),
    pointHoverRadius: 12,
    pointStyle: data.map(d => TIER_CONFIG[d.tier].pointStyle)
  };
}

// Crea dataset de línea de tendencia
function createTrendDataset(trendData) {
  return {
    label: 'Tendencia',
    data: trendData,
    type: 'line',
    ...CHART_CONFIG.trend,
    pointRadius: 0,
    fill: false,
    datalabels: { display: false }
  };
}

// Opciones base para scatter charts
function scatterOptions(xLabel, onClick, showLabels = false) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    onClick: onClick,
    plugins: {
      legend: { display: false },
      datalabels: showLabels ? {
        display: ctx => ctx.datasetIndex === 0,
        formatter: v => v.score,
        anchor: 'center',
        align: 'center',
        ...CHART_CONFIG.datalabels
      } : { display: false }
    },
    scales: {
      x: {
        title: { display: true, text: xLabel, font: { weight: 'bold' } },
        grid: CHART_CONFIG.grid
      },
      y: {
        title: { display: true, text: 'Precio (USD)', font: { weight: 'bold' } },
        grid: CHART_CONFIG.grid,
        ticks: { callback: v => '$' + (v / 1000) + 'k' }
      }
    }
  };
}

// ============================================
// RENDER CHARTS
// ============================================

function renderChart(properties) {
  const ctx = document.getElementById('scatterChart');
  if (!ctx) return;

  Chart.register(ChartDataLabels);

  const data = toChartData(properties);
  const trend = linearRegression(data, 'x');

  if (chart) chart.destroy();
  chart = new Chart(ctx.getContext('2d'), {
    type: 'scatter',
    data: {
      datasets: [
        createPropertiesDataset(data),
        createTrendDataset(trend)
      ]
    },
    options: {
      ...scatterOptions('M² cubiertos', (e, el) => onPointClick(e, el, chart), true),
      plugins: {
        ...scatterOptions('M² cubiertos', null, true).plugins,
        tooltip: { callbacks: { label: ctx => chartTooltip(ctx.raw, true) } }
      }
    }
  });
}

function renderScoreChart(properties) {
  const ctx = document.getElementById('scoreChart');
  if (!ctx) return;

  // Reusar datos pero con X = score
  const data = toChartData(properties).map(d => ({ ...d, x: d.score }));
  const trend = linearRegression(data, 'x');

  if (scoreChart) scoreChart.destroy();
  scoreChart = new Chart(ctx.getContext('2d'), {
    type: 'scatter',
    data: {
      datasets: [
        createPropertiesDataset(data),
        createTrendDataset(trend)
      ]
    },
    options: {
      ...scatterOptions('Score', (e, el) => onPointClick(e, el, scoreChart), false),
      plugins: {
        ...scatterOptions('Score', null, false).plugins,
        tooltip: { callbacks: { label: ctx => chartTooltip(ctx.raw, false) } }
      }
    }
  });
}

function renderStatsGrid(properties) {
  const valid = properties.filter(p => p._precio > 0);
  const withM2 = valid.filter(p => p._m2 > 0);

  const statsData = {
    total: properties.length,
    entran: valid.filter(p => p._ok).length,
    avgPrecioM2: withM2.length > 0 ? Math.round(withM2.reduce((a, b) => a + b._preciom2, 0) / withM2.length) : 0,
    avgM2: withM2.length > 0 ? Math.round(withM2.reduce((a, b) => a + b._m2, 0) / withM2.length) : 0,
  };

  const grid = document.getElementById('statsGrid');
  if (!grid) return;

  grid.innerHTML = `
    <div class="bg-white rounded-xl p-4 shadow-sm">
      <div class="text-2xl font-bold text-blue-600">${statsData.total}</div>
      <div class="text-xs text-slate-500">Total propiedades</div>
    </div>
    <div class="bg-white rounded-xl p-4 shadow-sm">
      <div class="text-2xl font-bold text-green-600">${statsData.entran}</div>
      <div class="text-xs text-slate-500">Entran en presupuesto</div>
    </div>
    <div class="bg-white rounded-xl p-4 shadow-sm">
      <div class="text-2xl font-bold text-purple-600">$${statsData.avgPrecioM2.toLocaleString()}</div>
      <div class="text-xs text-slate-500">$/m² promedio</div>
    </div>
    <div class="bg-white rounded-xl p-4 shadow-sm">
      <div class="text-2xl font-bold text-slate-600">${statsData.avgM2}m²</div>
      <div class="text-xs text-slate-500">M² promedio</div>
    </div>
  `;
}

// ============================================
// INICIALIZACIÓN STATS
// ============================================

async function initStats() {
  console.log('📊 Stats v6-modular iniciando...');

  state.loading = true;
  renderStatsPage();

  // Cargar datos
  try {
    await fetchData();
    allProperties = getProperties();
    renderBarrioCheckboxes();
    renderStatsPage();
  } catch (e) {
    console.error('Error:', e);
    state.error = e.message;
  }

  state.loading = false;
  renderStatsPage();

  // Cargar dólar
  fetchDolarBNA().then(data => {
    if (data) {
      state.dolarBNA = data;
      renderStatsPage();
    }
  });

  // Auto-refresh
  startAutoRefresh();
}

// Override render for stats page
function render() {
  allProperties = getProperties();
  renderStatsPage();
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
  const dropdown = document.getElementById('barrioDropdown');
  if (!dropdown) return;
  const btn = e.target.closest('button');
  if (!dropdown.contains(e.target) && !btn?.onclick?.toString().includes('toggleBarrioDropdown')) {
    dropdown.classList.add('hidden');
  }
});

// Start
initStats();
