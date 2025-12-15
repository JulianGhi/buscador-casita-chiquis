/**
 * marketData.js - Datos de mercado inmobiliario CABA
 * Fuentes: Índice M2 Real (RE/MAX + UCEMA), Zonaprop Index, Colegio de Escribanos
 * 
 * Actualizar mensualmente con datos de:
 * - https://ucema.edu.ar/novedad/ultimo-informe-indice-metro-cuadrado-real
 * - https://www.zonaprop.com.ar/noticias/zpindex/
 * - https://www.colegio-escribanos.org.ar/category/estadisticas-de-escrituras/
 */

const MARKET_DATA = {
  // Última actualización
  lastUpdate: '2025-12',
  
  // ==========================================
  // ÍNDICE M2 REAL (Precios de cierre reales)
  // Fuente: RE/MAX + UCEMA + Reporte Inmobiliario
  // ==========================================
  m2Real: {
    // Precio promedio de CIERRE (no publicación) en USD/m²
    preciosCierre: {
      general: 2161,      // Promedio general CABA
      monoambiente: 2250, // 1 ambiente
      dosAmbientes: 2180, // 2 ambientes  
      tresAmbientes: 2050 // 3 ambientes
    },
    
    // Brecha entre precio publicado y precio de cierre
    // Negativo = el cierre es menor que la publicación
    brechaPublicacionCierre: -0.0429, // -4.29% (promedio actual)
    
    // Variación mensual del índice
    variacionMensual: -0.0005, // -0.05%
    variacionAnual: 0.065,     // +6.5%
    
    // Serie histórica (para gráficos)
    historico: [
      { mes: '2025-01', precio: 2100 },
      { mes: '2025-02', precio: 2110 },
      { mes: '2025-03', precio: 2125 },
      { mes: '2025-04', precio: 2140 },
      { mes: '2025-05', precio: 2161 },
      { mes: '2025-06', precio: 2155 },
      { mes: '2025-07', precio: 2160 },
      { mes: '2025-08', precio: 2158 },
      { mes: '2025-09', precio: 2162 },
      { mes: '2025-10', precio: 2165 },
      { mes: '2025-11', precio: 2161 },
    ]
  },

  // ==========================================
  // ZONAPROP INDEX (Precios de oferta por barrio)
  // Fuente: Zonaprop.com.ar
  // ==========================================
  zonapropIndex: {
    // Promedio CABA
    promedioCABA: {
      venta: 2450,        // USD/m² promedio venta
      alquiler: 12.5,     // USD/m² promedio alquiler mensual
      rentabilidad: 5.39  // % anual bruto
    },
    
    // Precios por barrio (USD/m² venta departamentos)
    // Ordenados alfabéticamente
    barrios: {
      'Agronomía':        1850,
      'Almagro':          2280,
      'Balvanera':        2100,
      'Barracas':         2150,
      'Belgrano':         3200,
      'Boedo':            2350,
      'Caballito':        2450,
      'Chacarita':        2400,
      'Coghlan':          2650,
      'Colegiales':       2700,
      'Constitución':     1900,
      'Devoto':           2300,
      'Flores':           2100,
      'Floresta':         1890,
      'La Boca':          1650,
      'La Paternal':      2050,
      'Liniers':          1750,
      'Mataderos':        1600,
      'Monte Castro':     1950,
      'Núñez':            3100,
      'Palermo':          3400,
      'Parque Avellaneda': 1700,
      'Parque Chacabuco': 2050,
      'Parque Chas':      2200,
      'Parque Patricios': 2000,
      'Puerto Madero':    5800,
      'Recoleta':         3500,
      'Saavedra':         2450,
      'San Cristóbal':    2000,
      'San Nicolás':      2300,
      'San Telmo':        2400,
      'Vélez Sársfield':  1850,
      'Versalles':        1900,
      'Villa Crespo':     2550,
      'Villa del Parque': 2150,
      'Villa Devoto':     2300,
      'Villa General Mitre': 2100,
      'Villa Lugano':     1200,
      'Villa Luro':       1850,
      'Villa Ortúzar':    2450,
      'Villa Pueyrredón': 2100,
      'Villa Real':       1800,
      'Villa Riachuelo':  1150,
      'Villa Santa Rita': 2000,
      'Villa Soldati':    1300,
      'Villa Urquiza':    2600,
    },
    
    // Rentabilidad por barrio (% anual bruto)
    rentabilidadPorBarrio: {
      'Lugano':           9.2,
      'Nueva Pompeya':    8.4,
      'Parque Avellaneda': 7.8,
      'La Boca':          7.5,
      'Floresta':         6.8,
      'Flores':           6.2,
      'Caballito':        5.5,
      'Villa Crespo':     5.1,
      'Palermo':          4.2,
      'Núñez':            4.4,
      'Belgrano':         4.0,
      'Puerto Madero':    3.7,
    }
  },

  // ==========================================
  // COLEGIO DE ESCRIBANOS (Actividad de mercado)
  // Fuente: Colegio de Escribanos CABA
  // ==========================================
  escribanos: {
    // Último mes disponible
    ultimoMes: '2025-07',
    
    // Datos del último mes
    escrituras: 6651,
    montoTotalMillones: 976906, // en millones de pesos
    
    // Variación interanual
    variacionAnual: 0.322, // +32.2% vs julio 2024
    
    // Escrituras con hipoteca
    escriturasConHipoteca: 114,
    porcentajeHipoteca: 1.7, // % del total
    
    // Serie histórica mensual (últimos 12 meses)
    historico: [
      { mes: '2024-08', escrituras: 4850 },
      { mes: '2024-09', escrituras: 4920 },
      { mes: '2024-10', escrituras: 5100 },
      { mes: '2024-11', escrituras: 5250 },
      { mes: '2024-12', escrituras: 4800 },
      { mes: '2025-01', escrituras: 4200 },
      { mes: '2025-02', escrituras: 4450 },
      { mes: '2025-03', escrituras: 4747 },
      { mes: '2025-04', escrituras: 5471 },
      { mes: '2025-05', escrituras: 5600 },
      { mes: '2025-06', escrituras: 5762 },
      { mes: '2025-07', escrituras: 6651 },
    ]
  }
};

// ==========================================
// FUNCIONES DE CÁLCULO
// ==========================================

/**
 * Calcula el precio de cierre estimado aplicando la brecha de mercado
 * @param {number} precioPublicado - Precio publicado en USD
 * @returns {object} - { precioCierre, brecha, ahorro }
 */
function calcularPrecioCierre(precioPublicado) {
  const brecha = MARKET_DATA.m2Real.brechaPublicacionCierre;
  const precioCierre = Math.round(precioPublicado * (1 + brecha));
  const ahorro = precioPublicado - precioCierre;
  
  return {
    precioPublicado,
    precioCierre,
    brecha: brecha,
    brechaTexto: `${(brecha * 100).toFixed(1)}%`,
    ahorro,
    ahorroTexto: `$${ahorro.toLocaleString()}`
  };
}

/**
 * Compara el precio/m² de una propiedad contra el promedio del barrio
 * @param {number} precioM2 - Precio por m² de la propiedad
 * @param {string} barrio - Nombre del barrio
 * @returns {object} - { promedioBarrio, diferencia, porcentaje, esBuenPrecio }
 */
function compararConBarrio(precioM2, barrio) {
  const promedioBarrio = MARKET_DATA.zonapropIndex.barrios[barrio];
  
  if (!promedioBarrio) {
    return {
      promedioBarrio: null,
      diferencia: null,
      porcentaje: null,
      mensaje: 'Barrio no encontrado'
    };
  }
  
  const diferencia = precioM2 - promedioBarrio;
  const porcentaje = ((precioM2 - promedioBarrio) / promedioBarrio) * 100;
  
  return {
    promedioBarrio,
    diferencia: Math.round(diferencia),
    porcentaje: porcentaje.toFixed(1),
    esBuenPrecio: porcentaje < 0,
    mensaje: porcentaje < 0 
      ? `${Math.abs(porcentaje).toFixed(0)}% bajo promedio` 
      : `${porcentaje.toFixed(0)}% sobre promedio`,
    color: porcentaje < -10 ? 'green' : porcentaje < 5 ? 'yellow' : 'red'
  };
}

/**
 * Compara el precio/m² contra el precio de cierre real de CABA
 * @param {number} precioM2 - Precio por m² de la propiedad
 * @param {number} ambientes - Cantidad de ambientes (1, 2 o 3)
 * @returns {object}
 */
function compararConM2Real(precioM2, ambientes = null) {
  let precioRef;
  
  if (ambientes === 1) {
    precioRef = MARKET_DATA.m2Real.preciosCierre.monoambiente;
  } else if (ambientes === 2) {
    precioRef = MARKET_DATA.m2Real.preciosCierre.dosAmbientes;
  } else if (ambientes === 3) {
    precioRef = MARKET_DATA.m2Real.preciosCierre.tresAmbientes;
  } else {
    precioRef = MARKET_DATA.m2Real.preciosCierre.general;
  }
  
  const diferencia = precioM2 - precioRef;
  const porcentaje = ((precioM2 - precioRef) / precioRef) * 100;
  
  return {
    precioM2Real: precioRef,
    diferencia: Math.round(diferencia),
    porcentaje: porcentaje.toFixed(1),
    esBuenPrecio: porcentaje < 0,
    mensaje: porcentaje < 0 
      ? `${Math.abs(porcentaje).toFixed(0)}% bajo cierre real` 
      : `${porcentaje.toFixed(0)}% sobre cierre real`
  };
}

/**
 * Obtiene indicadores de mercado para mostrar en el header
 * @returns {object}
 */
function getIndicadoresMercado() {
  const esc = MARKET_DATA.escribanos;
  const m2 = MARKET_DATA.m2Real;
  
  return {
    escrituras: {
      cantidad: esc.escrituras,
      variacion: `${(esc.variacionAnual * 100).toFixed(0)}%`,
      tendencia: esc.variacionAnual > 0 ? 'up' : 'down',
      mes: esc.ultimoMes
    },
    m2Real: {
      precio: m2.preciosCierre.general,
      variacion: `${(m2.variacionAnual * 100).toFixed(1)}%`,
      tendencia: m2.variacionAnual > 0 ? 'up' : 'down'
    },
    brecha: {
      porcentaje: `${(m2.brechaPublicacionCierre * 100).toFixed(1)}%`,
      texto: 'Negociación promedio'
    }
  };
}

/**
 * Calcula la rentabilidad estimada de una propiedad
 * @param {number} precioVenta - Precio de venta en USD
 * @param {string} barrio - Nombre del barrio
 * @param {number} m2 - Metros cuadrados
 * @returns {object}
 */
function calcularRentabilidad(precioVenta, barrio, m2) {
  // Usar rentabilidad del barrio o promedio CABA
  const rentAnual = MARKET_DATA.zonapropIndex.rentabilidadPorBarrio[barrio] 
    || MARKET_DATA.zonapropIndex.promedioCABA.rentabilidad;
  
  const alquilerMensualEstimado = (precioVenta * (rentAnual / 100)) / 12;
  const alquilerM2 = alquilerMensualEstimado / m2;
  const aniosRecupero = 100 / rentAnual;
  
  return {
    rentabilidadAnual: rentAnual,
    alquilerMensualEstimado: Math.round(alquilerMensualEstimado),
    alquilerM2: Math.round(alquilerM2 * 100) / 100,
    aniosRecupero: Math.round(aniosRecupero * 10) / 10
  };
}

// Exportar para uso en módulos
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MARKET_DATA,
    calcularPrecioCierre,
    compararConBarrio,
    compararConM2Real,
    getIndicadoresMercado,
    calcularRentabilidad
  };
}
