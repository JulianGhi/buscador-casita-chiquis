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
    // Fetch datos históricos de Bluelytics para calcular variaciones
    const historicos = await fetchJSON('https://api.bluelytics.com.ar/v2/evolution.json');
    const oficial = historicos.filter(d => d.source === 'Oficial');

    if (oficial.length === 0) throw new Error('No hay datos históricos');

    const hoy = oficial[0];
    const valorHoy = hoy.value_sell;

    // Buscar valores históricos por fecha
    const fechaHoy = new Date(hoy.date);

    // Helper para buscar valor en fecha específica (o la más cercana anterior)
    const buscarValor = (diasAtras) => {
      const fechaObjetivo = new Date(fechaHoy);
      fechaObjetivo.setDate(fechaObjetivo.getDate() - diasAtras);

      // Buscar la fecha exacta o la más cercana (hasta 3 días de tolerancia)
      for (let i = 0; i <= 3; i++) {
        const fechaBuscar = new Date(fechaObjetivo);
        fechaBuscar.setDate(fechaBuscar.getDate() - i);
        const fechaStr = fechaBuscar.toISOString().split('T')[0];
        const registro = oficial.find(d => d.date === fechaStr);
        if (registro) return registro.value_sell;
      }
      return null;
    };

    const valorAyer = buscarValor(1);
    const valorSemana = buscarValor(7);
    const valorMes = buscarValor(30);

    return {
      venta: valorHoy,
      compra: hoy.value_buy,
      fecha: hoy.date,
      variaciones: {
        dia: calcVariacion(valorHoy, valorAyer),
        semana: calcVariacion(valorHoy, valorSemana),
        mes: calcVariacion(valorHoy, valorMes)
      }
    };
  } catch (err) {
    console.error('Error fetching dolar históricos:', err);
    // Fallback a DolarAPI (sin históricos)
    try {
      const data = await fetchJSON('https://dolarapi.com/v1/dolares/oficial');
      return {
        venta: data.venta,
        compra: data.compra,
        fecha: data.fechaActualizacion?.split('T')[0] || new Date().toISOString().split('T')[0],
        variaciones: { dia: null, semana: null, mes: null }
      };
    } catch (fallbackErr) {
      console.error('Fallback también falló:', fallbackErr);
      return null;
    }
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
    CONFIG.DOLAR_BASE = Math.round(data.venta);  // Actualizar base
  }
  render();
}
