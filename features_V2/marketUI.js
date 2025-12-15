/**
 * marketUI.js - Componentes UI para datos de mercado
 * Integrar con la web de Casita Chiquis
 */

// ==========================================
// 1. HEADER - Indicadores de Mercado
// ==========================================

/**
 * Genera el HTML para los indicadores de mercado en el header
 * Agregar junto al indicador del dólar existente
 */
function renderMarketIndicators() {
  const ind = getIndicadoresMercado();
  
  return `
    <span class="market-indicator" title="Escrituras ${ind.escrituras.mes}">
      📊 ${ind.escrituras.cantidad.toLocaleString()} escrituras
      <span class="trend ${ind.escrituras.tendencia === 'up' ? 'positive' : 'negative'}">
        ${ind.escrituras.tendencia === 'up' ? '↑' : '↓'}${ind.escrituras.variacion}
      </span>
    </span>
    <span class="market-indicator" title="Precio cierre real CABA (Índice M2 Real)">
      🏠 M2 Real: $${ind.m2Real.precio.toLocaleString()}
      <span class="trend ${ind.m2Real.tendencia === 'up' ? 'positive' : 'negative'}">
        ${ind.m2Real.tendencia === 'up' ? '↑' : '↓'}${ind.m2Real.variacion}
      </span>
    </span>
  `;
}

// ==========================================
// 2. MODAL - Sección de Negociación Mejorada
// ==========================================

/**
 * Genera el HTML para la sección de negociación en el modal
 * Reemplaza el "Negociar 0%" actual
 * 
 * @param {object} propiedad - Datos de la propiedad
 * @param {number} propiedad.precio - Precio publicado
 * @param {number} propiedad.m2 - Metros cuadrados
 * @param {string} propiedad.barrio - Barrio
 * @param {number} propiedad.ambientes - Cantidad de ambientes
 */
function renderNegociacionSection(propiedad) {
  const cierre = calcularPrecioCierre(propiedad.precio);
  const brecha = MARKET_DATA.m2Real.brechaPublicacionCierre;
  const porcentajeNeg = Math.abs(brecha * 100).toFixed(1);
  
  return `
    <div class="negociacion-card">
      <div class="negociacion-header">
        <span class="negociacion-icon">💰</span>
        <span class="negociacion-title">Negociar</span>
        <span class="negociacion-badge">${porcentajeNeg}%</span>
      </div>
      
      <div class="negociacion-body">
        <div class="precio-row">
          <span class="precio-label">Publicado</span>
          <span class="precio-valor precio-publicado">$${propiedad.precio.toLocaleString()}</span>
        </div>
        <div class="precio-row precio-estimado">
          <span class="precio-label">Cierre estimado</span>
          <span class="precio-valor precio-cierre">$${cierre.precioCierre.toLocaleString()}</span>
        </div>
        <div class="precio-row ahorro">
          <span class="precio-label">Ahorro potencial</span>
          <span class="precio-valor precio-ahorro">-${cierre.ahorroTexto}</span>
        </div>
      </div>
      
      <div class="negociacion-footer">
        <small>📊 Basado en Índice M2 Real (${MARKET_DATA.lastUpdate})</small>
      </div>
    </div>
  `;
}

// ==========================================
// 3. MODAL - Comparación con Mercado
// ==========================================

/**
 * Genera el HTML para la comparación de precio con el mercado
 * Nueva sección para el modal
 */
function renderComparacionMercado(propiedad) {
  const precioM2 = propiedad.precio / propiedad.m2;
  const vsBarrio = compararConBarrio(precioM2, propiedad.barrio);
  const vsM2Real = compararConM2Real(precioM2, propiedad.ambientes);
  
  // Determinar color del indicador
  const getColorClass = (porcentaje) => {
    const p = parseFloat(porcentaje);
    if (p < -10) return 'muy-bueno';
    if (p < 0) return 'bueno';
    if (p < 10) return 'normal';
    return 'caro';
  };
  
  return `
    <div class="comparacion-mercado">
      <div class="comparacion-header">
        <span>📈</span>
        <span>$/m² vs Mercado</span>
      </div>
      
      <div class="comparacion-body">
        <!-- Precio actual -->
        <div class="comparacion-row actual">
          <div class="comparacion-icon">🏠</div>
          <div class="comparacion-info">
            <span class="comparacion-label">Este inmueble</span>
            <span class="comparacion-valor">$${Math.round(precioM2).toLocaleString()}/m²</span>
          </div>
        </div>
        
        <!-- vs Barrio -->
        ${vsBarrio.promedioBarrio ? `
        <div class="comparacion-row ${getColorClass(vsBarrio.porcentaje)}">
          <div class="comparacion-icon">📍</div>
          <div class="comparacion-info">
            <span class="comparacion-label">${propiedad.barrio} promedio</span>
            <span class="comparacion-valor">$${vsBarrio.promedioBarrio.toLocaleString()}/m²</span>
          </div>
          <div class="comparacion-diff ${parseFloat(vsBarrio.porcentaje) < 0 ? 'positive' : 'negative'}">
            ${parseFloat(vsBarrio.porcentaje) < 0 ? '↓' : '↑'}${Math.abs(vsBarrio.porcentaje)}%
          </div>
        </div>
        ` : ''}
        
        <!-- vs M2 Real CABA -->
        <div class="comparacion-row ${getColorClass(vsM2Real.porcentaje)}">
          <div class="comparacion-icon">🏙️</div>
          <div class="comparacion-info">
            <span class="comparacion-label">CABA cierre real</span>
            <span class="comparacion-valor">$${vsM2Real.precioM2Real.toLocaleString()}/m²</span>
          </div>
          <div class="comparacion-diff ${parseFloat(vsM2Real.porcentaje) < 0 ? 'positive' : 'negative'}">
            ${parseFloat(vsM2Real.porcentaje) < 0 ? '↓' : '↑'}${Math.abs(vsM2Real.porcentaje)}%
          </div>
        </div>
      </div>
      
      <div class="comparacion-footer">
        ${parseFloat(vsBarrio.porcentaje) < -10 
          ? '<span class="badge badge-green">✨ Muy buen precio</span>' 
          : parseFloat(vsBarrio.porcentaje) < 0 
            ? '<span class="badge badge-yellow">👍 Buen precio</span>'
            : parseFloat(vsBarrio.porcentaje) < 10
              ? '<span class="badge badge-gray">📊 Precio de mercado</span>'
              : '<span class="badge badge-red">⚠️ Sobre precio de mercado</span>'
        }
      </div>
    </div>
  `;
}

// ==========================================
// 4. MODAL - Rentabilidad (para inversores)
// ==========================================

/**
 * Genera el HTML para mostrar rentabilidad estimada
 * Útil si también evalúan como inversión
 */
function renderRentabilidad(propiedad) {
  const rent = calcularRentabilidad(propiedad.precio, propiedad.barrio, propiedad.m2);
  
  return `
    <div class="rentabilidad-card">
      <div class="rentabilidad-header">
        <span>💹</span>
        <span>Rentabilidad estimada</span>
      </div>
      
      <div class="rentabilidad-body">
        <div class="rentabilidad-main">
          <span class="rentabilidad-valor">${rent.rentabilidadAnual}%</span>
          <span class="rentabilidad-label">anual bruto</span>
        </div>
        
        <div class="rentabilidad-details">
          <div class="rentabilidad-row">
            <span>Alquiler estimado</span>
            <span>~$${rent.alquilerMensualEstimado.toLocaleString()}/mes</span>
          </div>
          <div class="rentabilidad-row">
            <span>Recupero inversión</span>
            <span>~${rent.aniosRecupero} años</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ==========================================
// 5. ESTILOS CSS
// ==========================================

const MARKET_STYLES = `
<style>
/* Header indicators */
.market-indicator {
  margin-left: 1rem;
  padding: 0.25rem 0.5rem;
  background: rgba(255,255,255,0.1);
  border-radius: 4px;
  font-size: 0.85rem;
}

.market-indicator .trend {
  margin-left: 0.25rem;
  font-weight: 600;
}

.trend.positive { color: #4ade80; }
.trend.negative { color: #f87171; }

/* Negociación card */
.negociacion-card {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.negociacion-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.negociacion-title {
  font-weight: 600;
  color: #fbbf24;
}

.negociacion-badge {
  background: #fbbf24;
  color: #000;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 700;
}

.precio-row {
  display: flex;
  justify-content: space-between;
  padding: 0.35rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.precio-row:last-child { border-bottom: none; }

.precio-label { color: #94a3b8; font-size: 0.9rem; }
.precio-valor { font-weight: 600; }

.precio-publicado { color: #94a3b8; text-decoration: line-through; }
.precio-cierre { color: #4ade80; font-size: 1.1rem; }
.precio-ahorro { color: #fbbf24; }

.negociacion-footer {
  margin-top: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.negociacion-footer small {
  color: #64748b;
  font-size: 0.75rem;
}

/* Comparación mercado */
.comparacion-mercado {
  background: #1e293b;
  border-radius: 12px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.comparacion-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: #e2e8f0;
}

.comparacion-row {
  display: flex;
  align-items: center;
  padding: 0.5rem;
  border-radius: 8px;
  margin-bottom: 0.25rem;
}

.comparacion-row.actual {
  background: rgba(99, 102, 241, 0.2);
}

.comparacion-row.muy-bueno { background: rgba(34, 197, 94, 0.15); }
.comparacion-row.bueno { background: rgba(250, 204, 21, 0.1); }
.comparacion-row.normal { background: rgba(148, 163, 184, 0.1); }
.comparacion-row.caro { background: rgba(239, 68, 68, 0.1); }

.comparacion-icon {
  font-size: 1.25rem;
  margin-right: 0.5rem;
}

.comparacion-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.comparacion-label {
  font-size: 0.8rem;
  color: #94a3b8;
}

.comparacion-valor {
  font-weight: 600;
  color: #e2e8f0;
}

.comparacion-diff {
  font-weight: 700;
  font-size: 0.9rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.comparacion-diff.positive {
  color: #4ade80;
  background: rgba(34, 197, 94, 0.2);
}

.comparacion-diff.negative {
  color: #f87171;
  background: rgba(239, 68, 68, 0.2);
}

.comparacion-footer {
  margin-top: 0.75rem;
  text-align: center;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 600;
}

.badge-green { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
.badge-yellow { background: rgba(250, 204, 21, 0.2); color: #fbbf24; }
.badge-gray { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
.badge-red { background: rgba(239, 68, 68, 0.2); color: #f87171; }

/* Rentabilidad */
.rentabilidad-card {
  background: linear-gradient(135deg, #064e3b 0%, #022c22 100%);
  border-radius: 12px;
  padding: 1rem;
}

.rentabilidad-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.rentabilidad-main {
  text-align: center;
  padding: 0.75rem 0;
}

.rentabilidad-valor {
  font-size: 2rem;
  font-weight: 700;
  color: #4ade80;
}

.rentabilidad-label {
  display: block;
  color: #94a3b8;
  font-size: 0.85rem;
}

.rentabilidad-details {
  border-top: 1px solid rgba(255,255,255,0.1);
  padding-top: 0.75rem;
}

.rentabilidad-row {
  display: flex;
  justify-content: space-between;
  padding: 0.25rem 0;
  font-size: 0.9rem;
  color: #94a3b8;
}
</style>
`;

// ==========================================
// 6. FUNCIÓN DE INTEGRACIÓN
// ==========================================

/**
 * Integra todos los componentes en el modal existente
 * Llamar cuando se abre el modal de una propiedad
 * 
 * @param {object} propiedad - Datos de la propiedad seleccionada
 * @returns {string} - HTML completo para insertar en el modal
 */
function renderMarketInsights(propiedad) {
  return `
    ${MARKET_STYLES}
    <div class="market-insights">
      ${renderNegociacionSection(propiedad)}
      ${renderComparacionMercado(propiedad)}
    </div>
  `;
}

/**
 * Actualiza el header con indicadores de mercado
 * Llamar una vez al cargar la página
 */
function initMarketHeader() {
  // Buscar el contenedor del dólar en el header
  const dolarIndicator = document.querySelector('.dolar-indicator');
  
  if (dolarIndicator) {
    // Insertar después del indicador del dólar
    const marketHtml = renderMarketIndicators();
    dolarIndicator.insertAdjacentHTML('afterend', marketHtml);
  }
}

// Inicializar cuando el DOM esté listo
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', initMarketHeader);
}

// Exportar funciones
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    renderMarketIndicators,
    renderNegociacionSection,
    renderComparacionMercado,
    renderRentabilidad,
    renderMarketInsights,
    initMarketHeader
  };
}
