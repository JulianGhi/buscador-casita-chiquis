// ============================================
// MI COMPRA - TRACKER DE COMPRA STANDALONE
// ============================================

let allProperties = [];
let compraState = loadFromStorage('casita_compra') || { propertyKey: null, senaUSD: 0 };
// Migración: propertyLink viejo → propertyKey
if (compraState.propertyLink && !compraState.propertyKey) {
  compraState.propertyKey = compraState.propertyLink;
  delete compraState.propertyLink;
  saveToStorage('casita_compra', compraState);
}

// ============================================
// ESTADO Y PERSISTENCIA
// ============================================

function propertyKey(p) {
  return p.link || ((p.direccion || '') + '|' + (p.barrio || ''));
}

function saveCompraState() {
  saveToStorage('casita_compra', compraState);
  // Fire-and-forget: sync to cloud
  saveCompraData(compraState);
}

function getSelectedProperty() {
  if (!compraState.propertyKey) return null;
  return allProperties.find(p => propertyKey(p) === compraState.propertyKey) || null;
}

function selectProperty(idx) {
  const prop = allProperties.find(p => p._idx === parseInt(idx));
  if (!prop) return;
  compraState.propertyKey = propertyKey(prop);
  saveCompraState();
  renderCompraPage();
}

function clearSelection() {
  compraState.propertyKey = null;
  compraState.senaUSD = 0;
  saveCompraState();
  renderCompraPage();
}

function updateSena(value) {
  compraState.senaUSD = parseInt(value) || 0;
  saveCompraState();
  // Actualización parcial (sin recrear todo)
  updateCompraCalcs();
}

// ============================================
// CÁLCULOS
// ============================================

function calculateCompraData(property) {
  const precio = property._precio;
  const sena = compraState.senaUSD || 0;
  const creditoUSD = getCreditoUSD();
  const cuota = getCuotaInfo();
  const tieneInmob = !esVentaDirecta(property.inmobiliaria);

  const anticipo = Math.max(precio - creditoUSD, precio * 0.1);
  const faltanteCasa = Math.max(0, anticipo - sena);

  const escr = Math.round(precio * CONFIG.ESCRIBANO);
  const sell = precio <= CONFIG.SELLOS_EXENTO ? 0 : Math.round(precio * CONFIG.SELLOS);
  const reg = Math.round(precio * CONFIG.REGISTRALES);
  const inmob = tieneInmob ? Math.round(precio * CONFIG.INMOB) : 0;
  const hip = Math.round(precio * CONFIG.HIPOTECA);
  const cert = CONFIG.CERTIFICADOS;
  const gastosTotal = escr + sell + reg + inmob + hip + cert;

  const totalNecesario = anticipo + gastosTotal;
  const totalFaltante = faltanteCasa + gastosTotal;
  const progreso = totalNecesario > 0 ? Math.min(100, (sena / totalNecesario) * 100) : 0;

  return {
    precio, sena, creditoUSD, cuota,
    anticipo: Math.round(anticipo),
    faltanteCasa: Math.round(faltanteCasa),
    escr, sell, reg, inmob, hip, cert,
    tieneInmob, gastosTotal,
    totalNecesario: Math.round(totalNecesario),
    totalFaltante: Math.round(totalFaltante),
    progreso,
    ok: totalFaltante <= CONFIG.PRESUPUESTO,
    dif: CONFIG.PRESUPUESTO - totalFaltante,
  };
}

// ============================================
// ACTUALIZACIÓN PARCIAL (para input de seña)
// ============================================

function updateCompraCalcs() {
  const calcs = document.getElementById('compra-calcs');
  if (!calcs) return;
  const property = getSelectedProperty();
  if (!property) return;
  const data = calculateCompraData(property);
  calcs.innerHTML = renderCompraCalcs(data, property);
}

// ============================================
// RENDER
// ============================================

function renderCompraPage() {
  const stats = getStats(allProperties);
  document.getElementById('headerContainer').innerHTML = renderHeader(stats, 'compra');

  const container = document.getElementById('compra-content');
  const property = getSelectedProperty();

  if (!property) {
    container.innerHTML = renderPropertySelector();
  } else {
    const data = calculateCompraData(property);
    container.innerHTML = renderCompraDetail(property, data);
  }

  updateContentPadding();
}

function renderPropertySelector() {
  const activas = allProperties.filter(p => {
    const activo = (p.activo || '').toLowerCase();
    return activo === 'si' && p._precio > 0;
  });

  const options = activas
    .sort((a, b) => (a.barrio || '').localeCompare(b.barrio || '') || a._precio - b._precio)
    .map(p => {
      const dir = p.direccion || 'Sin dirección';
      const barrio = p.barrio || '?';
      const precio = fmt(p._precio);
      return `<option value="${p._idx}">${barrio} · ${dir} · ${precio}</option>`;
    }).join('');

  return `
    <div class="bg-white rounded-xl shadow-sm p-6 text-center">
      <div class="text-4xl mb-4">🔑</div>
      <h2 class="text-lg font-semibold text-slate-700 mb-2">Mi compra</h2>
      <p class="text-sm text-slate-500 mb-6">Elegí una propiedad para empezar a trackear tu compra</p>

      <select onchange="if(this.value) selectProperty(this.value)"
              class="w-full px-4 py-3 rounded-lg border border-slate-300 text-sm text-slate-700 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
        <option value="">Seleccionar propiedad...</option>
        ${options}
      </select>

      ${activas.length === 0 ? '<p class="text-xs text-slate-400 mt-4">No hay propiedades activas con precio</p>' : ''}
    </div>
  `;
}

function renderCompraDetail(property, data) {
  const dir = property.direccion || 'Sin dirección';
  const barrio = property.barrio || '';
  const creditoCubreSaldo = data.faltanteCasa <= 0;
  const uva = getValorUVA();
  const dolar = CONFIG.DOLAR_BASE;

  return `
    <!-- Propiedad seleccionada -->
    <div class="bg-white rounded-xl shadow-sm mb-4 overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3">
        <div class="min-w-0">
          <div class="font-semibold text-slate-800 truncate">${ICONS.house} ${escapeHtml(dir)}</div>
          <div class="text-sm text-slate-500">${escapeHtml(barrio)} · ${fmt(data.precio)}</div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          ${property.link ? `<a href="${escapeHtml(property.link)}" target="_blank" class="text-blue-500 hover:text-blue-700 text-sm">${ICONS.external}</a>` : ''}
          <button onclick="clearSelection()" class="text-slate-400 hover:text-red-500 text-lg" title="Desvincular">${ICONS.close}</button>
        </div>
      </div>
    </div>

    <!-- Input seña (fuera de compra-calcs para no perder foco) -->
    <div class="bg-white rounded-xl shadow-sm mb-4 p-4">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-slate-600">Seña pagada (USD)</span>
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-400">$</span>
          <input type="number" id="sena-input" value="${data.sena || ''}" placeholder="0"
                 oninput="updateSena(this.value)"
                 class="w-28 px-3 py-1.5 text-right rounded-lg border border-slate-300 text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
        </div>
      </div>
    </div>

    <!-- Cálculos (se actualizan sin destruir el input) -->
    <div id="compra-calcs">
      ${renderCompraCalcs(data, property)}
    </div>

    <!-- Cambiar propiedad -->
    <div class="mt-4 text-center">
      <button onclick="clearSelection()" class="text-sm text-slate-400 hover:text-slate-600">Cambiar propiedad</button>
    </div>
  `;
}

function renderCompraCalcs(data, property) {
  const creditoCubreSaldo = data.faltanteCasa <= 0;
  const uva = getValorUVA();
  const dolar = CONFIG.DOLAR_BASE;
  const anticipoPct = data.precio > 0 ? ((data.anticipo / data.precio) * 100).toFixed(1) : 0;

  return `
    <!-- Barra de progreso -->
    <div class="bg-white rounded-xl shadow-sm mb-4 p-4">
      <div class="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
        <div class="bg-green-500 h-3 rounded-full transition-all" style="width: ${data.progreso.toFixed(1)}%"></div>
      </div>
      <div class="flex justify-between text-xs text-slate-500 mt-1">
        <span>Seña ${fmt(data.sena)}</span>
        <span class="font-medium">${data.progreso.toFixed(0)}%</span>
        <span>Total ${fmt(data.totalNecesario)}</span>
      </div>
    </div>

    <!-- Faltante + Gastos -->
    <div class="grid grid-cols-2 gap-3 mb-4">
      <div class="bg-white rounded-xl shadow-sm p-4 border-l-4 ${creditoCubreSaldo ? 'border-green-400' : 'border-blue-400'}">
        <div class="text-xs font-medium ${creditoCubreSaldo ? 'text-green-600' : 'text-blue-600'} mb-1">Faltante casa</div>
        ${creditoCubreSaldo
          ? `<div class="text-xl font-bold text-green-600">${ICONS.check} $0</div>
             <div class="text-xs text-green-500">Crédito cubre el saldo</div>`
          : `<div class="text-xl font-bold text-blue-700">${fmt(data.faltanteCasa)}</div>
             <div class="text-xs text-blue-400">anticipo - seña</div>`
        }
      </div>
      <div class="bg-white rounded-xl shadow-sm p-4 border-l-4 border-amber-400">
        <div class="text-xs font-medium text-amber-600 mb-1">Gastos escritura</div>
        <div class="text-xl font-bold text-amber-700">${fmt(data.gastosTotal)}</div>
        <div class="text-xs text-amber-400">escr+sell+reg${data.tieneInmob ? '+inmob' : ''}</div>
      </div>
    </div>

    <!-- Crédito hipotecario -->
    <div class="bg-white rounded-xl shadow-sm mb-4 p-4">
      <div class="text-xs font-medium text-slate-500 mb-2">Crédito hipotecario</div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="text-xs text-slate-400">Capital</div>
          <div class="font-semibold text-slate-700">${fmtNum(Math.round(CONFIG.CREDITO_UVA))} UVAs</div>
          <div class="text-sm text-slate-500">= ${fmt(data.creditoUSD)}</div>
        </div>
        <div>
          <div class="text-xs text-slate-400">Cuota</div>
          <div class="font-semibold text-slate-700">${fmtNum(Math.round(data.cuota.uva))} UVAs</div>
          <div class="text-sm text-slate-500">= $${Math.round(data.cuota.ars).toLocaleString()} ARS</div>
          <div class="text-xs text-slate-400">~USD ${data.cuota.usd}</div>
        </div>
      </div>
      <div class="text-xs text-slate-400 mt-2">Dólar $${dolar} · UVA $${uva.toLocaleString('es-AR', {minimumFractionDigits: 0, maximumFractionDigits: 0})}</div>
    </div>

    <!-- Desglose de gastos -->
    <div class="bg-white rounded-xl shadow-sm mb-4 p-4">
      <div class="text-xs font-medium text-slate-500 mb-3">Desglose de gastos</div>
      <div class="space-y-2 text-sm">
        ${desgloseRow('Anticipo (' + anticipoPct + '%)', data.anticipo)}
        ${desgloseRow('Escribano (' + toPct(CONFIG.ESCRIBANO) + '%)', data.escr)}
        ${desgloseRow('Sellos (' + (data.precio <= CONFIG.SELLOS_EXENTO ? 'exento' : toPct(CONFIG.SELLOS) + '%') + ')', data.sell)}
        ${desgloseRow('Registrales (' + toPct(CONFIG.REGISTRALES, 1) + '%)', data.reg)}
        ${data.tieneInmob ? desgloseRow('Inmobiliaria (' + toPct(CONFIG.INMOB) + '%)', data.inmob) : ''}
        ${desgloseRow('Hipoteca (' + toPct(CONFIG.HIPOTECA, 0) + '%)', data.hip)}
        ${desgloseRow('Certificados', data.cert)}
        <div class="border-t border-slate-200 pt-2 flex justify-between font-semibold text-slate-800">
          <span>TOTAL A JUNTAR</span>
          <span>${fmt(data.totalFaltante)}</span>
        </div>
        <div class="flex justify-between text-xs ${data.ok ? 'text-green-600' : 'text-red-600'}">
          <span>Tengo: ${fmt(CONFIG.PRESUPUESTO)}</span>
          <span>${data.ok ? 'Sobran' : 'Faltan'} ${fmt(Math.abs(data.dif))}</span>
        </div>
      </div>
    </div>

    <!-- Total final -->
    <div class="bg-slate-800 text-white rounded-xl shadow-sm p-4 flex items-center justify-between">
      <span class="text-sm font-medium">Total faltante</span>
      <span class="text-2xl font-bold">${fmt(data.totalFaltante)}</span>
    </div>
  `;
}

function desgloseRow(label, value) {
  return `
    <div class="flex justify-between text-slate-600">
      <span>${label}</span>
      <span class="font-medium">${fmt(value)}</span>
    </div>
  `;
}

// ============================================
// OVERRIDE RENDER GLOBAL
// ============================================

function render() {
  allProperties = getProperties();
  renderCompraPage();
}

// ============================================
// INICIALIZACIÓN
// ============================================

async function initCompra() {
  console.log(`🔑 Mi Compra ${APP_VERSION} iniciando...`);

  state.loading = true;
  renderCompraPage();

  try {
    await fetchData();
    allProperties = getProperties();
    renderCompraPage();
  } catch (e) {
    console.error('Error:', e);
    state.error = e.message;
  }

  state.loading = false;
  renderCompraPage();

  // Cargar dólar, UVA y datos de compra de la nube
  Promise.all([
    fetchDolarBNA().then(data => {
      if (data) {
        state.dolarBNA = data;
        CONFIG.DOLAR_BASE = Math.round(data.venta);
      }
    }),
    fetchUVA().then(data => {
      if (data) state.uvaData = data;
    }),
    // Cloud sync: nube es source of truth
    fetchCompraData().then(cloudData => {
      if (cloudData && cloudData.propertyKey) {
        // Nube tiene datos → usarlos
        compraState.propertyKey = cloudData.propertyKey;
        compraState.senaUSD = cloudData.senaUSD;
        saveToStorage('casita_compra', compraState);
      } else if (compraState.propertyKey && CONFIG.APPS_SCRIPT_URL) {
        // Nube vacía, local tiene datos → subir a la nube
        saveCompraData(compraState);
      }
    })
  ]).then(() => renderCompraPage());

  startAutoRefresh();
}

initCompra();
