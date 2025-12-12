// ============================================
// API CALLS
// ============================================

async function fetchDolarBNA() {
  try {
    const response = await fetch('https://api.bluelytics.com.ar/v2/evolution.json');
    if (!response.ok) throw new Error('API error');
    const allData = await response.json();

    const oficial = allData.filter(d => d.source === 'Oficial');
    if (oficial.length === 0) throw new Error('No data');

    const hoy = oficial[0];
    const hace1Dia = oficial.find((d, i) => i > 0 && d.date !== hoy.date);
    const hace7Dias = oficial.slice(0, 14).find(d => {
      const diff = (new Date(hoy.date) - new Date(d.date)) / (1000 * 60 * 60 * 24);
      return diff >= 6 && diff <= 8;
    });
    const hace30Dias = oficial.find(d => {
      const diff = (new Date(hoy.date) - new Date(d.date)) / (1000 * 60 * 60 * 24);
      return diff >= 28 && diff <= 32;
    });

    const variaciones = {
      dia: hace1Dia ? ((hoy.value_sell - hace1Dia.value_sell) / hace1Dia.value_sell * 100).toFixed(2) : null,
      semana: hace7Dias ? ((hoy.value_sell - hace7Dias.value_sell) / hace7Dias.value_sell * 100).toFixed(2) : null,
      mes: hace30Dias ? ((hoy.value_sell - hace30Dias.value_sell) / hace30Dias.value_sell * 100).toFixed(2) : null
    };

    return {
      venta: hoy.value_sell,
      compra: hoy.value_buy,
      fecha: hoy.date,
      variaciones
    };
  } catch (err) {
    console.error('Error fetching dolar:', err);
    return null;
  }
}

async function fetchData() {
  console.group('🔄 fetchData()');
  console.log('Timestamp:', new Date().toISOString());

  state.loading = true;
  state.error = null;
  render();

  const API_URL = `https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/A:AH?key=${API_KEY}`;
  console.log('Using Sheets API');

  try {
    console.log('Fetching...');
    const response = await fetch(API_URL);

    console.log('Response status:', response.status);

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error?.message || `HTTP ${response.status}`);
    }

    const data = await response.json();
    console.log('Rows received:', data.values?.length || 0);

    if (!data.values || data.values.length < 2) {
      throw new Error('No hay datos');
    }

    const csvLines = data.values.map(row =>
      row.map(cell => {
        const val = (cell || '').toString();
        if (val.includes(',') || val.includes('"')) {
          return '"' + val.replace(/"/g, '""') + '"';
        }
        return val;
      }).join(',')
    );
    const csvText = csvLines.join('\n');

    const headers = data.values[0];
    const validRows = data.values.slice(1).filter(row => row[0] || row[1] || row[2]);

    console.log('Valid rows:', validRows.length);
    const direcciones = validRows.map(row => row[0] || '(vacío)');
    console.log('Direcciones:', direcciones.join(' | '));

    state.rawData = csvText;
    state.lastUpdate = new Date();
    state.error = null;

    console.log('✅ Data loaded successfully via API');

  } catch (err) {
    console.error('❌ Error:', err.message);
    state.error = 'Error: ' + err.message;
    if (!state.rawData) state.rawData = SAMPLE_CSV;
  }

  state.loading = false;
  console.groupEnd();
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
