// ============================================
// EVENT HANDLERS
// ============================================
// Nota: updateContentPadding() está en utils.js (compartido)

function showDetail(idx) {
  state.selectedProperty = idx;
  state.negotiationPct = CONFIG.NEGOCIACION || 0;
  state.dolarEstimado = null;
  render();
}

function closeDetail() {
  state.selectedProperty = null;
  state.negotiationPct = 0;
  state.dolarEstimado = null;
  render();
}

// Actualiza solo los cálculos del modal (sin recrear sliders)
function updateSimulation() {
  const calcs = document.getElementById('simulation-calcs');
  if (!calcs) return;

  const properties = getProperties();
  const selectedProp = state.selectedProperty !== null
    ? properties.find(p => p._idx === state.selectedProperty)
    : null;

  if (selectedProp) {
    calcs.innerHTML = renderSimulationCalcs(selectedProp);
  }
}

function updateNegotiation(pct) {
  state.negotiationPct = parseFloat(pct);

  // Actualizar display del slider
  const display = document.getElementById('neg-display');
  if (display) {
    const val = parseFloat(pct);
    display.textContent = val > 0 ? '-' + (val % 1 === 0 ? val : val.toFixed(1)) + '%' : '0%';
    display.className = val > 0 ? 'text-lg font-bold text-orange-600' : 'text-lg font-bold text-slate-400';
  }

  updateSimulation();
}

function updateDolarEstimado(valor) {
  state.dolarEstimado = valor ? parseInt(valor) : null;

  // Actualizar display del slider
  const display = document.getElementById('dolar-display');
  if (display) {
    display.textContent = '$' + valor;
    display.className = valor != CONFIG.DOLAR_BASE ? 'text-lg font-bold text-green-600' : 'text-lg font-bold text-slate-400';
  }

  // Actualizar info del crédito
  const creditoInfo = document.getElementById('dolar-credito-info');
  if (creditoInfo) {
    const dolar = parseInt(valor);
    const creditoBase = getCreditoUSD();
    const creditoEstimado = getCreditoUSD(dolar);
    const diferencia = creditoBase - creditoEstimado;
    const hayAjuste = dolar !== CONFIG.DOLAR_BASE;

    if (hayAjuste) {
      creditoInfo.classList.remove('hidden');
      creditoInfo.className = `text-xs text-center mt-2 ${diferencia > 0 ? 'text-red-600' : 'text-green-600'}`;
      creditoInfo.textContent = `Crédito: $${creditoEstimado.toLocaleString()} (${diferencia > 0 ? '-' : '+'}$${Math.abs(diferencia).toLocaleString()})`;
    } else {
      creditoInfo.classList.add('hidden');
    }
  }

  updateSimulation();
}

function updateConfig(key, value) {
  CONFIG[key] = value;
  saveConfig(CONFIG);
  render();
}

function updateRefM2(barrio, value) {
  if (value === '' || value === null) {
    delete REF_M2[barrio];
  } else {
    REF_M2[barrio] = parseInt(value) || 0;
  }
  saveRefM2(REF_M2);
  render();
}

function updateWeight(key, value) {
  WEIGHTS[key].weight = parseInt(value);
  saveWeights(WEIGHTS);
  render();
}

// Actualiza solo el display durante el arrastre (sin re-render para mobile)
function updateWeightDisplay(key, value) {
  WEIGHTS[key].weight = parseInt(value);
  const display = document.getElementById('weight-display-' + key);
  if (display) {
    display.textContent = value;
  }
}

function toggleWeightEnabled(key, enabled) {
  WEIGHTS[key].enabled = enabled;
  saveWeights(WEIGHTS);
  render();
}

function updateCondition(key, enabled) {
  CONDITIONS[key].enabled = enabled;
  saveConditions(CONDITIONS);
  render();
}

function resetConditions() {
  if (!confirm('¿Resetear condiciones a valores por defecto?')) return;
  CONDITIONS = cloneDefault(DEFAULT_CONDITIONS);
  saveConditions(CONDITIONS);
  render();
}

function resetWeights() {
  if (!confirm('¿Resetear pesos a valores por defecto?')) return;
  WEIGHTS = cloneDefault(DEFAULT_WEIGHTS);
  saveWeights(WEIGHTS);
  render();
}

function addBarrio() {
  const nombre = prompt('Nombre del barrio:')?.trim();
  if (!nombre) return;
  const valor = prompt('$/m² de referencia:');
  if (!valor) return;
  REF_M2[nombre] = parseInt(valor) || 0;
  saveRefM2(REF_M2);
  render();
}

function deleteBarrio(barrio) {
  if (!confirm(`¿Eliminar ${barrio}?`)) return;
  delete REF_M2[barrio];
  saveRefM2(REF_M2);
  render();
}

function resetConfig() {
  if (!confirm('¿Resetear toda la configuración a los valores por defecto?')) return;
  CONFIG = { ...DEFAULT_CONFIG };
  REF_M2 = { ...DEFAULT_REF_M2 };
  CONDITIONS = cloneDefault(DEFAULT_CONDITIONS);
  WEIGHTS = cloneDefault(DEFAULT_WEIGHTS);
  saveConfig(CONFIG);
  saveRefM2(REF_M2);
  saveConditions(CONDITIONS);
  saveWeights(WEIGHTS);
  render();
}

// ============================================
// RENDER PRINCIPAL
// ============================================

function render() {
  // Guardar estado del input de búsqueda ANTES de destruir el DOM
  const searchInput = document.getElementById('search-input');
  const searchWasFocused = document.activeElement === searchInput;
  const searchValue = searchInput?.value || '';
  const searchCursor = searchInput?.selectionStart || 0;

  const properties = getProperties();
  const filtered = getFiltered(properties);
  const stats = getStats(properties);
  const barrios = [...new Set(properties.map(p => p.barrio).filter(Boolean))].sort();
  const selectedProp = state.selectedProperty !== null ? properties.find(p => p._idx === state.selectedProperty) : null;

  const root = document.getElementById('root');
  root.innerHTML = `
    ${renderHeader(stats)}

    <!-- Main Content -->
    <div class="main-content min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-3 md:p-6">
      <div class="max-w-7xl mx-auto">
        ${state.error ? `<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm">${escapeHtml(state.error)}</div>` : ''}
        ${renderFilters(barrios, filtered, properties)}

        <!-- Cards view (mobile or forced) -->
        <div class="${state.viewMode === 'cards' ? '' : state.viewMode === 'table' ? 'hidden' : 'md:hidden'}">
          ${renderCards(filtered)}
          ${filtered.length === 0 ? '<div class="text-center py-8 text-slate-400">No hay propiedades que coincidan</div>' : ''}
        </div>

        <!-- Table view (desktop or forced) -->
        <div class="${state.viewMode === 'table' ? '' : state.viewMode === 'cards' ? 'hidden' : 'hidden md:block'}">
          ${renderTable(filtered)}
        </div>
      </div>
    </div>

    ${selectedProp ? renderDetailModal(selectedProp) : ''}
  `;

  // Restaurar estado del input de búsqueda DESPUÉS de recrear el DOM
  const newSearchInput = document.getElementById('search-input');
  if (newSearchInput) {
    newSearchInput.value = searchValue;
    if (searchWasFocused) {
      newSearchInput.focus();
      newSearchInput.setSelectionRange(searchCursor, searchCursor);
    }
  }

  updateContentPadding();
}

// ============================================
// INICIALIZACIÓN
// ============================================

function init() {
  console.log(`🏠 Casita Chiquis ${APP_VERSION} iniciando...`);

  // Cargar datos
  fetchData();

  // Iniciar auto-refresh
  startAutoRefresh();

  // Cargar dólar y UVA en paralelo
  cargarDolarHoy();
  cargarUVAHoy();
}

// Ejecutar al cargar
init();
