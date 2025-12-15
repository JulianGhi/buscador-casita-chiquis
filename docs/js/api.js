// ============================================
// API CALLS
// ============================================

// Helper genérico para fetch JSON con manejo de errores
async function fetchJSON(url, options = {}) {
  const { errorMessage = 'API error' } = options;
  const response = await fetch(url);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `${errorMessage}: HTTP ${response.status}`);
  }
  return response.json();
}

// Calcula variación porcentual
function calcVariacion(actual, anterior) {
  if (!anterior) return null;
  return ((actual - anterior) / anterior * 100).toFixed(2);
}

async function fetchDolarBNA() {
  try {
    const allData = await fetchJSON('https://api.bluelytics.com.ar/v2/evolution.json');
    const oficial = allData.filter(d => d.source === 'Oficial');
    if (oficial.length === 0) throw new Error('No data');

    const hoy = oficial[0];

    // Buscar valores históricos para variaciones
    const findByDaysAgo = (minDays, maxDays) => oficial.find(d => {
      const diff = (new Date(hoy.date) - new Date(d.date)) / (1000 * 60 * 60 * 24);
      return diff >= minDays && diff <= maxDays;
    });

    const hace1Dia = oficial.find((d, i) => i > 0 && d.date !== hoy.date);
    const hace7Dias = findByDaysAgo(6, 8);
    const hace30Dias = findByDaysAgo(28, 32);

    return {
      venta: hoy.value_sell,
      compra: hoy.value_buy,
      fecha: hoy.date,
      variaciones: {
        dia: calcVariacion(hoy.value_sell, hace1Dia?.value_sell),
        semana: calcVariacion(hoy.value_sell, hace7Dias?.value_sell),
        mes: calcVariacion(hoy.value_sell, hace30Dias?.value_sell)
      }
    };
  } catch (err) {
    console.error('Error fetching dolar:', err);
    return null;
  }
}

// Convierte array de arrays a CSV
function arrayToCSV(rows) {
  return rows.map(row =>
    row.map(cell => {
      const val = (cell || '').toString();
      return (val.includes(',') || val.includes('"'))
        ? '"' + val.replace(/"/g, '""') + '"'
        : val;
    }).join(',')
  ).join('\n');
}

async function fetchData() {
  state.loading = true;
  state.error = null;
  render();

  const API_URL = `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/A:AH?key=${API_KEY}`;

  try {
    const data = await fetchJSON(API_URL, { errorMessage: 'Sheets API' });

    if (!data.values || data.values.length < 2) {
      throw new Error('No hay datos');
    }

    state.rawData = arrayToCSV(data.values);
    state.lastUpdate = new Date();
    state.error = null;

  } catch (err) {
    console.error('fetchData error:', err.message);
    state.error = 'Error: ' + err.message;
    if (!state.rawData) state.rawData = SAMPLE_CSV;
  }

  state.loading = false;
  render();
}

// ============================================
// AUTO REFRESH
// ============================================

function startAutoRefresh() {
  stopAutoRefresh();
  if (CONFIG.AUTO_REFRESH > 0) {
    state.autoRefreshEnabled = true;
    console.log(`⏱️ Auto-refresh cada ${CONFIG.AUTO_REFRESH}s`);
    autoRefreshInterval = setInterval(() => {
      fetchData();
    }, CONFIG.AUTO_REFRESH * 1000);
  }
}

function stopAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
  }
  state.autoRefreshEnabled = false;
}

function toggleAutoRefresh() {
  if (state.autoRefreshEnabled) {
    stopAutoRefresh();
  } else {
    startAutoRefresh();
  }
  render();
}

async function cargarDolarHoy() {
  state.loadingDolar = true;
  render();
  const data = await fetchDolarBNA();
  state.loadingDolar = false;
  if (data) {
    state.dolarBNA = data;
    state.dolarEstimado = Math.round(data.venta);
  }
  render();
}
