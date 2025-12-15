/**
 * GUÍA DE INTEGRACIÓN - Casita Chiquis
 * =====================================
 * 
 * Este archivo muestra cómo integrar los datos de mercado
 * con tu código existente.
 */

// ==========================================
// PASO 1: Agregar los scripts al HTML
// ==========================================

/*
En tu index.html, agregar antes del cierre de </body>:

<script src="marketData.js"></script>
<script src="marketUI.js"></script>
*/


// ==========================================
// PASO 2: Modificar el Header
// ==========================================

/*
ANTES (tu código actual):
--------------------------
<div class="header-indicators">
  <span>💵 Dólar BNA $1465 | 1d: +0.14% | 7d: +0.14% | 30d: +2.38%</span>
</div>

DESPUÉS:
---------
<div class="header-indicators">
  <span class="dolar-indicator">💵 Dólar BNA $1465 | 1d: +0.14% | 7d: +0.14% | 30d: +2.38%</span>
  <!-- Los indicadores de mercado se insertan automáticamente aquí -->
</div>

El script marketUI.js detecta '.dolar-indicator' e inserta los nuevos indicadores.
*/


// ==========================================
// PASO 3: Modificar el Modal de Propiedad
// ==========================================

// Ejemplo de cómo modificar tu función que abre el modal

// ANTES (pseudocódigo de tu función actual):
function openPropertyModalOLD(propertyId) {
  const prop = getPropertyById(propertyId);
  
  const modalContent = `
    <h2>${prop.direccion}</h2>
    <p>${prop.barrio} · ${prop.tipo}</p>
    
    <!-- Tu sección de Negociar actual -->
    <div class="negociar-section">
      <span>💰 Negociar</span>
      <span>0%</span>  <!-- Hardcodeado -->
    </div>
    
    <!-- Resto del modal... -->
  `;
  
  showModal(modalContent);
}

// DESPUÉS (con datos de mercado):
function openPropertyModal(propertyId) {
  const prop = getPropertyById(propertyId);
  
  // Preparar objeto para las funciones de mercado
  const propiedadData = {
    precio: prop.precio,           // ej: 94000
    m2: prop.m2Cubiertos,          // ej: 54
    barrio: prop.barrio,           // ej: "Floresta"
    ambientes: prop.ambientes      // ej: 3
  };
  
  const modalContent = `
    <h2>${prop.direccion}</h2>
    <p>${prop.barrio} · ${prop.tipo}</p>
    
    <!-- NUEVO: Insights de mercado -->
    ${renderMarketInsights(propiedadData)}
    
    <!-- Tu slider de dólar estimado (mantener) -->
    <div class="dolar-slider">
      ...
    </div>
    
    <!-- Tu desglose de costos (mantener) -->
    <div class="desglose-costos">
      ...
    </div>
  `;
  
  showModal(modalContent);
}


// ==========================================
// PASO 4: Integración Mínima (Quick Win)
// ==========================================

// Si solo querés cambiar el "0%" por el dato real,
// sin todo el diseño nuevo, hacé esto:

function getNegociacionPorcentaje() {
  // Retorna el porcentaje de negociación basado en datos reales
  const brecha = MARKET_DATA.m2Real.brechaPublicacionCierre;
  return Math.abs(brecha * 100).toFixed(1) + '%';
}

function getPrecioCierreEstimado(precioPublicado) {
  const brecha = MARKET_DATA.m2Real.brechaPublicacionCierre;
  return Math.round(precioPublicado * (1 + brecha));
}

// Uso en tu código:
// En vez de: <span>Negociar 0%</span>
// Usá: <span>Negociar ${getNegociacionPorcentaje()}</span>

// Y agregá el precio de cierre:
// <span>Cierre estimado: $${getPrecioCierreEstimado(prop.precio).toLocaleString()}</span>


// ==========================================
// PASO 5: Columna "vs Ref" mejorada
// ==========================================

// Tu columna actual muestra +3%, -15%, etc.
// Podés agregar un tooltip con más contexto:

function getVsRefTooltip(prop) {
  const precioM2 = prop.precio / prop.m2;
  const vsBarrio = compararConBarrio(precioM2, prop.barrio);
  const vsM2Real = compararConM2Real(precioM2, prop.ambientes);
  
  return `
    vs ${prop.barrio}: ${vsBarrio.mensaje}
    vs CABA cierre: ${vsM2Real.mensaje}
  `;
}

// En tu tabla:
// <td title="${getVsRefTooltip(prop)}">${prop.vsRef}</td>


// ==========================================
// PASO 6: Actualización de Datos
// ==========================================

/*
Los datos en marketData.js necesitan actualizarse mensualmente.

Fuentes para actualizar:

1. ÍNDICE M2 REAL (precio cierre + brecha):
   https://ucema.edu.ar/novedad/ultimo-informe-indice-metro-cuadrado-real
   - PDF mensual con tablas de datos
   - Actualizar: m2Real.preciosCierre y brechaPublicacionCierre

2. ZONAPROP INDEX (precios por barrio):
   https://www.zonaprop.com.ar/noticias/zpindex/
   - PDF mensual con precios por barrio
   - Actualizar: zonapropIndex.barrios

3. ESCRIBANOS (volumen de mercado):
   https://www.colegio-escribanos.org.ar/category/estadisticas-de-escrituras/
   - Informe mensual de escrituras
   - Actualizar: escribanos.escrituras y variacionAnual

Opcional: Podés automatizar con un script que scrapee estos PDFs.
*/


// ==========================================
// EJEMPLO COMPLETO: Modal con todo integrado
// ==========================================

function renderFullModal(prop) {
  const propData = {
    precio: prop.precio,
    m2: prop.m2,
    barrio: prop.barrio,
    ambientes: prop.ambientes
  };
  
  const cierre = calcularPrecioCierre(prop.precio);
  const vsBarrio = compararConBarrio(prop.precio / prop.m2, prop.barrio);
  
  return `
    <div class="modal-property">
      <!-- Header -->
      <div class="modal-header">
        <h2>${prop.direccion}</h2>
        <p>${prop.barrio} · ${prop.tipo}</p>
        
        <div class="modal-badges">
          <span class="badge">Por ver</span>
          <span class="badge badge-green">✓ Apto crédito</span>
          ${vsBarrio.esBuenPrecio ? '<span class="badge badge-green">📉 Bajo mercado</span>' : ''}
        </div>
      </div>
      
      <!-- Specs -->
      <div class="modal-specs">
        <div class="spec">
          <span class="spec-label">Tipo</span>
          <span class="spec-value">${prop.tipo}</span>
        </div>
        <div class="spec">
          <span class="spec-label">Ambientes</span>
          <span class="spec-value">${prop.ambientes}</span>
        </div>
        <div class="spec">
          <span class="spec-label">m² totales</span>
          <span class="spec-value">${prop.m2}</span>
        </div>
        <div class="spec">
          <span class="spec-label">Antigüedad</span>
          <span class="spec-value">${prop.antiguedad} años</span>
        </div>
      </div>
      
      <!-- Precio principal -->
      <div class="modal-precio">
        <div class="precio-main">
          <span class="precio-valor">$${prop.precio.toLocaleString()}</span>
          <span class="precio-label">Precio</span>
        </div>
        <div class="precio-m2">
          <span class="precio-valor">$${Math.round(prop.precio / prop.m2).toLocaleString()}</span>
          <span class="precio-label">$/m²</span>
        </div>
        <div class="precio-cierre">
          <span class="precio-valor" style="color: #4ade80;">$${cierre.precioCierre.toLocaleString()}</span>
          <span class="precio-label">Cierre estimado</span>
        </div>
      </div>
      
      <!-- Market Insights (nuevo) -->
      ${renderMarketInsights(propData)}
      
      <!-- Slider dólar (tu código existente) -->
      <div class="dolar-slider-container">
        <!-- ... tu slider ... -->
      </div>
      
      <!-- Desglose de costos (tu código existente) -->
      <div class="desglose-container">
        <!-- ... tu desglose ... -->
      </div>
    </div>
  `;
}
