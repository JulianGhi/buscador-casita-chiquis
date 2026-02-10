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
    // DolarAPI para valor actual (más actualizado durante el día)
    // Bluelytics para históricos (tiene serie temporal)
    const [dolarActual, historicos] = await Promise.all([
      fetchJSON('https://dolarapi.com/v1/dolares/oficial'),
      fetchJSON('https://api.bluelytics.com.ar/v2/evolution.json')
    ]);

    const valorHoy = dolarActual.venta;
    const fecha = dolarActual.fechaActualizacion?.split('T')[0] || new Date().toISOString().split('T')[0];

    // Calcular variaciones con históricos de Bluelytics (Oficial)
    const oficial = historicos.filter(d => d.source === 'Oficial');
    let variaciones = { dia: null, semana: null, mes: null };

    if (oficial.length > 0) {
      const buscarValor = (diasAtras) => {
        const fechaHoy = new Date();
        const fechaObjetivo = new Date(fechaHoy);
        fechaObjetivo.setDate(fechaObjetivo.getDate() - diasAtras);

        // Buscar fecha exacta o más cercana (hasta 3 días tolerancia por fines de semana)
        for (let i = 0; i <= 3; i++) {
          const fechaBuscar = new Date(fechaObjetivo);
          fechaBuscar.setDate(fechaBuscar.getDate() - i);
          const fechaStr = fechaBuscar.toISOString().split('T')[0];
          const registro = oficial.find(d => d.date === fechaStr);
          if (registro) return registro.value_sell;
        }
        return null;
      };

      variaciones = {
        dia: calcVariacion(valorHoy, buscarValor(1)),
        semana: calcVariacion(valorHoy, buscarValor(7)),
        mes: calcVariacion(valorHoy, buscarValor(30))
      };
    }

    return {
      venta: valorHoy,
      compra: dolarActual.compra,
      fecha,
      variaciones
    };
  } catch (err) {
    console.error('Error fetching dolar:', err);
    // Fallback: intentar solo DolarAPI sin históricos
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

// Hash simple para detectar cambios en datos
function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}

// fetchData con soporte para background refresh silencioso
async function fetchData(options = {}) {
  const { silent = false } = options;

  // Solo mostrar loading en refresh manual
  if (!silent) {
    state.loading = true;
    state.error = null;
    render();
  }

  const API_URL = `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/A:AH?key=${API_KEY}`;

  try {
    const data = await fetchJSON(API_URL, { errorMessage: 'Sheets API' });

    if (!data.values || data.values.length < 2) {
      throw new Error('No hay datos');
    }

    const newData = arrayToCSV(data.values);
    const newHash = simpleHash(newData);

    // Solo re-render si los datos cambiaron
    if (newHash !== state.dataHash) {
      state.rawData = newData;
      state.dataHash = newHash;
      state.lastUpdate = new Date();
      state.error = null;

      if (!silent) {
        state.loading = false;
      }
      render();
    } else if (!silent) {
      // Refresh manual sin cambios: quitar loading
      state.loading = false;
      render();
    }
    // Si es silent y no hay cambios: no hacer nada

  } catch (err) {
    console.error('fetchData error:', err.message);
    state.error = 'Error: ' + err.message;
    if (!state.rawData) state.rawData = SAMPLE_CSV;
    if (!silent) {
      state.loading = false;
      render();
    }
  }
}

// ============================================
// AUTO REFRESH (con Visibility API)
// ============================================

function startAutoRefresh() {
  stopAutoRefresh();
  if (CONFIG.AUTO_REFRESH > 0 && !document.hidden) {
    state.autoRefreshEnabled = true;
    autoRefreshInterval = setInterval(() => {
      // Background refresh silencioso
      fetchData({ silent: true });
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

// Visibility API: pausar cuando tab está oculta
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    if (state.autoRefreshEnabled) {
      state._wasAutoRefreshing = true;
      stopAutoRefresh();
    }
  } else {
    if (state._wasAutoRefreshing) {
      state._wasAutoRefreshing = false;
      startAutoRefresh();
    }
  }
});

async function fetchUVA() {
  try {
    const hoy = new Date();
    const hace7 = new Date(hoy);
    hace7.setDate(hace7.getDate() - 7);
    const fmtDate = (d) => d.toISOString().split('T')[0];
    const url = `https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/31?desde=${fmtDate(hace7)}&hasta=${fmtDate(hoy)}`;
    const response = await fetch(url, { headers: { 'Accept': 'application/json' } });
    if (!response.ok) throw new Error(`BCRA API: HTTP ${response.status}`);
    const data = await response.json();
    const detalle = data.results?.[0]?.detalle;
    if (!detalle || detalle.length === 0) throw new Error('Sin datos UVA');
    // v4 devuelve ordenado desc por fecha, el primero es el más reciente
    const ultimo = detalle[0];
    return {
      valor: ultimo.valor,
      fecha: ultimo.fecha
    };
  } catch (err) {
    console.error('Error fetching UVA:', err);
    return null;
  }
}

async function cargarUVAHoy() {
  state.loadingUVA = true;
  render();
  const data = await fetchUVA();
  state.loadingUVA = false;
  if (data) {
    state.uvaData = data;
  }
  render();
}

// ============================================
// COMPRA - CLOUD PERSISTENCE
// ============================================

async function fetchCompraData() {
  try {
    const url = `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/Compra!A:B?key=${API_KEY}`;
    const data = await fetchJSON(url, { errorMessage: 'Compra tab' });
    if (!data.values || data.values.length < 2) return null;
    // Row 1 = headers, Row 2 = data
    const row = data.values[1];
    return {
      propertyKey: row[0] || null,
      senaUSD: parseInt(row[1]) || 0,
    };
  } catch (err) {
    console.warn('fetchCompraData:', err.message);
    return null;
  }
}

async function saveCompraData(compra) {
  if (!CONFIG.APPS_SCRIPT_URL) return;
  try {
    await fetch(CONFIG.APPS_SCRIPT_URL, {
      method: 'POST',
      body: JSON.stringify({
        propertyKey: compra.propertyKey || '',
        senaUSD: compra.senaUSD || 0,
      }),
    });
  } catch (err) {
    console.warn('saveCompraData:', err.message);
  }
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
