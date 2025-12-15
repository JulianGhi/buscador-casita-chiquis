// ============================================
// STATS - LÓGICA ESPECÍFICA
// ============================================

function updateContentPadding() {
  requestAnimationFrame(() => {
    const header = document.querySelector('header');
    const content = document.querySelector('.main-content');
    if (header && content) {
      content.style.paddingTop = (header.offsetHeight + 16) + 'px';
    }
  });
}

let chart = null;
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

  // Render chart and stats
  renderChart(filtered);
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

// Colores por tier
const TIER_COLORS = {
  1: { bg: 'rgba(34, 197, 94, 0.7)', border: 'rgb(22, 163, 74)' },   // Verde - T1 Ideal
  2: { bg: 'rgba(59, 130, 246, 0.7)', border: 'rgb(37, 99, 235)' },  // Azul - T2 Negociar
  3: { bg: 'rgba(234, 179, 8, 0.7)', border: 'rgb(202, 138, 4)' },   // Amarillo - T3 Verificar
  4: { bg: 'rgba(249, 115, 22, 0.7)', border: 'rgb(234, 88, 12)' },  // Naranja - T4 No apto
  5: { bg: 'rgba(248, 113, 113, 0.4)', border: 'rgb(239, 68, 68)' }, // Rojo claro - T5 Inactivo
};

function renderChart(properties) {
  const ctx = document.getElementById('scatterChart');
  if (!ctx) return;

  const validProps = properties.filter(p => p._precio > 0 && p._m2 > 0);

  const data = validProps.map(p => {
    const tier = p._tier || 5;
    return {
      x: p._m2,
      y: p._precio,
      label: p.direccion || 'Sin dirección',
      barrio: p.barrio || 'Sin barrio',
      preciom2: p._preciom2,
      ok: p._ok,
      vsRef: p._vsRef,
      tier: tier,
      score: p._score || 0
    };
  });

  // Calculate trend line
  let trendData = [];
  const n = data.length;
  if (n > 1) {
    const sumX = data.reduce((a, b) => a + b.x, 0);
    const sumY = data.reduce((a, b) => a + b.y, 0);
    const sumXY = data.reduce((a, b) => a + b.x * b.y, 0);
    const sumX2 = data.reduce((a, b) => a + b.x * b.x, 0);

    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    const minX = Math.min(...data.map(d => d.x));
    const maxX = Math.max(...data.map(d => d.x));

    trendData = [
      { x: minX, y: slope * minX + intercept },
      { x: maxX, y: slope * maxX + intercept }
    ];
  }

  if (chart) chart.destroy();

  chart = new Chart(ctx.getContext('2d'), {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: 'Propiedades',
          data: data,
          backgroundColor: data.map(d => TIER_COLORS[d.tier].bg),
          borderColor: data.map(d => TIER_COLORS[d.tier].border),
          borderWidth: data.map(d => d.tier <= 2 ? 2 : 1),
          pointRadius: data.map(d => d.tier === 1 ? 10 : d.tier === 2 ? 8 : 6),
          pointHoverRadius: 12,
          pointStyle: data.map(d => {
            if (d.tier === 5) return 'crossRot';
            if (d.tier === 4) return 'triangle';
            if (d.tier === 3) return 'rectRot';
            return 'circle';
          }),
        },
        {
          label: 'Tendencia',
          data: trendData,
          type: 'line',
          borderColor: 'rgba(100, 116, 139, 0.5)',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              const d = context.raw;
              const vsRef = d.vsRef !== null ? ` (${d.vsRef > 0 ? '+' : ''}${Math.round(d.vsRef * 100)}% vs barrio)` : '';
              const tierNames = {1: 'Ideal', 2: 'Negociar', 3: 'Verificar', 4: 'No apto', 5: 'Inactivo'};
              return [
                d.label,
                d.barrio,
                `$${d.y.toLocaleString()} · ${d.x}m²`,
                `$${d.preciom2.toLocaleString()}/m²${vsRef}`,
                `T${d.tier} ${tierNames[d.tier]} · Score: ${d.score}`
              ];
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: 'M² cubiertos', font: { weight: 'bold' } },
          grid: { color: 'rgba(0,0,0,0.05)' }
        },
        y: {
          title: { display: true, text: 'Precio (USD)', font: { weight: 'bold' } },
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            callback: function(value) { return '$' + (value / 1000) + 'k'; }
          }
        }
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
