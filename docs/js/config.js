// ============================================
// CONFIGURACIÓN Y ESTADO
// ============================================

const APP_VERSION = 'v7.6-20241218';  // Cambiar en cada deploy

// ============================================
// TEMA DE COLORES (Tailwind classes)
// ============================================
const THEME = {
  // Estados semánticos
  success: {
    bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200',
    bgSolid: 'bg-green-500', textLight: 'text-green-600', textDark: 'text-green-800'
  },
  warning: {
    bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-200',
    bgSolid: 'bg-yellow-500', textLight: 'text-yellow-600', textDark: 'text-yellow-800'
  },
  error: {
    bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200',
    bgSolid: 'bg-red-500', textLight: 'text-red-600', textDark: 'text-red-800'
  },
  info: {
    bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200',
    bgSolid: 'bg-blue-500', textLight: 'text-blue-600', textDark: 'text-blue-800'
  },
  neutral: {
    bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200',
    bgSolid: 'bg-slate-500', textLight: 'text-slate-600', textDark: 'text-slate-800'
  },
  // Colores específicos del dominio
  negociar: {
    bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-200',
    bgSolid: 'bg-orange-500', textLight: 'text-orange-600'
  },
  purple: {
    bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-200',
    bgSolid: 'bg-purple-500', textLight: 'text-purple-600'
  }
};

// ============================================
// SISTEMA DE ICONOS
// ============================================
const ICONS = {
  // Acciones
  check: '✓',
  cross: '✗',
  question: '?',
  refresh: '↻',
  external: '↗',
  close: '×',

  // Navegación
  arrowUp: '↑',
  arrowDown: '↓',

  // Propiedades
  terraza: '🌿',
  balcon: '🪴',
  patio: '🌳',
  cochera: '🚗',
  banos: '🚿',
  ambientes: '🚪',
  m2: '📐',
  precio: '💰',
  expensas: '💵',
  antiguedad: '✨',
  luminosidad: '☀️',
  frente: '🪟',

  // UI
  star: '⭐',
  calendar: '📅',
  phone: '📞',
  house: '🏠',
  building: '🏢',
  notes: '📝',
  chart: '📊',
  mobile: '📱',
  config: '⚙️',
  print: '📄',
  printOld: '📄',
  printMissing: '○',
  help: '?',
  filter: '🔍',
  dolar: '💵',
  handshake: '🤝',
  lightbulb: '💡',
  warning: '⚠️',
  info: 'ⓘ'
};

// ============================================
// CONFIGURACIÓN DE STATUS
// ============================================
const STATUS_CONFIG = {
  'visita programada': { theme: 'info', label: 'Visita programada' },
  'visitado':   { theme: 'info',    label: 'Visitado' },
  'interesado': { theme: 'success', label: 'Interesado' },
  'descartado': { theme: 'error',   label: 'Descartado' },
  'por ver':    { theme: 'warning', label: 'Por ver' },
  'default':    { theme: 'warning', label: null }
};

const DEFAULT_CONFIG = {
  CREDITO_UVA: 75109.30,
  CUOTA_UVA: 450.66,
  UVA_BASE: 1764,       // Fallback hasta que cargue la API
  UVA_MANUAL: null,      // Override manual (tiene prioridad sobre API)
  DOLAR_BASE: 1450,
  PRESUPUESTO: 35000,
  NEGOCIACION: 0,  // % de negociación base (0-15)
  MARGEN_REF: 0.12,
  ESCRIBANO: 0.0242,
  SELLOS_EXENTO: 140000,
  SELLOS: 0.0175,
  REGISTRALES: 0.004,
  INMOB: 0.0484,
  HIPOTECA: 0.01,
  CERTIFICADOS: 300,
  AUTO_REFRESH: 10,
  DIAS_NUEVA: 3,           // Días para considerar propiedad como "Nueva"
  DIAS_VENDIDA_RECIENTE: 3, // Días para mostrar badge "Vendida recientemente"
  PRECIO_COMPRA: 0,        // USD. 0 = feature deshabilitada
  SENA_USD: 0,             // Seña ya pagada en USD
};

const DEFAULT_REF_M2 = {
  "Almagro": 2000, "Boedo": 1876, "Caballito": 2357, "Flores": 1953,
  "Floresta": 1683, "Liniers": 1857, "Mataderos": 1629, "Monte Castro": 1854,
  "Parque Avellaneda": 1750, "Parque Chacabuco": 1951, "Paternal": 1897,
  "Villa Crespo": 2150, "Villa del Parque": 2063, "Villa Devoto": 2348,
  "Villa Luro": 1785, "Villa Santa Rita": 1750, "Vélez Sarsfield": 1663
};

const DEFAULT_CONDITIONS = {
  activo:        { label: 'Activo',         enabled: true, desc: 'Solo publicaciones online' },
  apto_credito:  { label: 'Apto crédito',   enabled: true, desc: 'Solo las que aceptan crédito' },
  ok_presupuesto:{ label: 'En presupuesto', enabled: true, desc: 'Solo las que podés pagar' },
};

// Descripciones de tiers para el filtro
const TIER_INFO = {
  1: { label: 'T1 - Ideales', color: 'green',  desc: 'Apto crédito + en presupuesto' },
  2: { label: 'T2 - Negociar', color: 'blue',   desc: 'Apto crédito, hay que negociar precio' },
  3: { label: 'T3 - Averiguar', color: 'yellow', desc: 'No sabemos si acepta crédito' },
  4: { label: 'T4 - Difícil', color: 'orange', desc: 'No acepta crédito' },
  5: { label: 'T5 - Inactivas', color: 'red',    desc: 'Dadas de baja o sin link' },
};

const DEFAULT_WEIGHTS = {
  bajo_mercado:  { label: '💰 Bajo mercado', weight: 7,  enabled: true, desc: '↑ peso = prioriza precio bajo vs barrio' },
  m2:            { label: '📐 M² grandes',   weight: 5,  enabled: true, desc: '↑ peso = prioriza más m² (70m²+ ideal)' },
  ambientes:     { label: '🚪 Ambientes',    weight: 3,  enabled: true, desc: '↑ peso = prioriza 3+ ambientes' },
  banos:         { label: '🚿 Baños',        weight: 2,  enabled: true, desc: '↑ peso = prioriza 2+ baños' },
  antiguedad:    { label: '✨ Nuevo',        weight: 3,  enabled: true, desc: '↑ peso = prioriza propiedades nuevas (<15 años)' },
  expensas:      { label: '💵 Exp. bajas',   weight: 2,  enabled: true, desc: '↑ peso = prioriza expensas bajas (<$80k)' },
  terraza:       { label: '🌿 Terraza',      weight: 5,  enabled: true, desc: '↑ peso = prioriza con terraza' },
  balcon:        { label: '🏠 Balcón',       weight: 3,  enabled: true, desc: '↑ peso = prioriza con balcón' },
  patio:         { label: '🌳 Patio',        weight: 5,  enabled: true, desc: '↑ peso = prioriza con patio' },
  cochera:       { label: '🚗 Cochera',      weight: 4,  enabled: true, desc: '↑ peso = prioriza con cochera' },
  luminosidad:   { label: '☀️ Luminoso',     weight: 4,  enabled: true, desc: '↑ peso = prioriza luminosidad' },
  frente:        { label: '🪟 Al frente',    weight: 3,  enabled: true, desc: '↑ peso = prioriza disposición frente' },
};

// ============================================
// CONFIGURACIÓN DE TIERS (centralizada)
// ============================================
const TIER_CONFIG = {
  1: {
    label: 'T1', name: 'Ideal',
    title: 'Activo + Apto crédito + OK$',
    css: 'bg-green-100 text-green-700',
    chart: { bg: 'rgba(34, 197, 94, 0.7)', border: 'rgb(22, 163, 74)' },
    pointStyle: 'circle', pointRadius: 10, borderWidth: 2
  },
  2: {
    label: 'T2', name: 'Negociar',
    title: 'Activo + Apto crédito + Caro',
    css: 'bg-blue-100 text-blue-700',
    chart: { bg: 'rgba(59, 130, 246, 0.7)', border: 'rgb(37, 99, 235)' },
    pointStyle: 'circle', pointRadius: 8, borderWidth: 2
  },
  3: {
    label: 'T3', name: 'Verificar',
    title: 'Activo + Crédito?',
    css: 'bg-yellow-100 text-yellow-700',
    chart: { bg: 'rgba(234, 179, 8, 0.7)', border: 'rgb(202, 138, 4)' },
    pointStyle: 'rectRot', pointRadius: 6, borderWidth: 1
  },
  4: {
    label: 'T4', name: 'No apto',
    title: 'Activo + No apto crédito',
    css: 'bg-orange-100 text-orange-700',
    chart: { bg: 'rgba(249, 115, 22, 0.7)', border: 'rgb(234, 88, 12)' },
    pointStyle: 'triangle', pointRadius: 6, borderWidth: 1
  },
  5: {
    label: 'T5', name: 'Inactivo',
    title: 'Inactivo o sin link',
    css: 'bg-red-100 text-red-700 opacity-60',
    chart: { bg: 'rgba(248, 113, 113, 0.4)', border: 'rgb(239, 68, 68)' },
    pointStyle: 'crossRot', pointRadius: 6, borderWidth: 1
  }
};

// ============================================
// REGLAS DE SCORING (centralizada)
// ============================================
// ============================================
// CONFIGURACIÓN DE CHARTS
// ============================================
const CHART_CONFIG = {
  // Estilos comunes
  trend: {
    borderColor: 'rgba(100, 116, 139, 0.5)',
    borderWidth: 2,
    borderDash: [5, 5]
  },
  grid: { color: 'rgba(0,0,0,0.05)' },
  // Datalabels
  datalabels: {
    color: '#fff',
    font: { size: 9, weight: 'bold' },
    textStrokeColor: 'rgba(0,0,0,0.5)',
    textStrokeWidth: 2
  }
};

const SCORING_RULES = {
  // Atributos booleanos: si/no/missing
  terraza:     { type: 'boolean', bonus: 10, penaltyMissing: 5 },
  balcon:      { type: 'boolean', bonus: 10, penaltyMissing: 5 },
  patio:       { type: 'boolean', bonus: 10, penaltyMissing: 5 },
  luminosidad: { type: 'boolean', bonus: 10, penaltyMissing: 5 },

  // Atributos numéricos (cocheras)
  cochera:     { type: 'numeric', bonus: 10, penaltyMissing: 5 },

  // Disposición (frente/contrafrente)
  frente:      { type: 'disposicion', bonus: 10, penaltyMissing: 5 },

  // Atributos con umbrales
  ambientes: {
    type: 'threshold',
    thresholds: [
      { min: 4, score: 8 },  // 4+ ambientes = muy bien
      { min: 3, score: 4 },  // 3 ambientes = bien
    ],
    penaltyMissing: 3
  },
  banos: {
    type: 'threshold',
    thresholds: [
      { min: 2, score: 6 },  // 2+ baños = bonus
    ],
    penaltyMissing: 3
  },
  antiguedad: {
    type: 'range',
    ranges: [
      { max: 0, score: 10 },   // A estrenar
      { max: 15, score: 6 },   // <15 años
      { max: 30, score: 3 },   // 15-30 años
      { max: 50, score: 0 },   // 30-50 años
      { min: 51, score: -3 },  // >50 años
    ],
    penaltyMissing: 3
  },
  expensas: {
    type: 'range',
    ranges: [
      { max: 0, score: 8 },       // Sin expensas
      { max: 80000, score: 5 },   // Bajas (<$80k)
      { max: 150000, score: 2 },  // Medias ($80-150k)
      { max: 250000, score: 0 },  // Altas ($150-250k)
      { min: 250001, score: -4 }, // Muy altas (>$250k)
    ],
    penaltyMissing: 2
  },
  m2: {
    type: 'threshold',
    thresholds: [
      { min: 70, score: 4 },  // Grande
      { min: 50, score: 2 },  // Mediano
      { min: 40, score: 1 },  // Chico pero OK
    ],
    penaltyMissing: 3
  },
  bajo_mercado: {
    type: 'vsRef',
    ranges: [
      { max: -0.15, score: 15 }, // Muy bajo mercado
      { max: -0.05, score: 8 },  // Bajo mercado
      { max: 0, score: 3 },      // Levemente bajo
      { min: 0.15, score: -5 },  // Sobre mercado
    ]
  }
};

const API_KEY = 'AIzaSyClZvK5NbmLEtxi9tqf1fcKxRIKEUqYnu0';
const SHEET_ID = '16n92ghEe8Vr1tiLdqbccF3i97kiwhHin9OPWY-O50L4';

const SAMPLE_CSV = `direccion,barrio,precio,m2_cub,m2_tot,m2_terr,amb,apto_credito,terraza,expensas,inmobiliaria,status,notas,link,activo,contacto,fecha_contacto,fecha_visita,antiguedad,estado,luminosidad,rating
Av Juan B Alberdi 4600,Parque Avellaneda,105000,70,140,70,3,si,si,0,GOLDEN HAUS,Visitado,Visita 30/8. Norte/Frente. 40 años.,https://www.argenprop.com/ficha--17094976,si,,,,,Bueno,Buena,`;

// ============================================
// HELPERS DE FORMATO
// ============================================

// Conversión decimal <-> porcentaje
const toPct = (decimal, decimals = 2) => (decimal * 100).toFixed(decimals);
const fromPct = (pct) => parseFloat(pct) / 100;

// Formato de variación con signo
const formatPctSign = (val) => (parseFloat(val) > 0 ? '+' : '') + val + '%';

// Formato de moneda (USD)
const fmt = (n) => n != null && !isNaN(n) ? '$' + n.toLocaleString() : '-';
const fmtNum = (n) => n != null && !isNaN(n) ? n.toLocaleString() : '-';

// ============================================
// PERSISTENCIA LOCAL (helpers genéricos)
// ============================================

function loadFromStorage(key, defaultValue) {
  try {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : null;
  } catch { return null; }
}

function saveToStorage(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function cloneDefault(obj) {
  return JSON.parse(JSON.stringify(obj));
}

// ============================================
// FUNCIONES DE CARGA ESPECÍFICAS
// ============================================

function loadConditions() {
  const saved = loadFromStorage('casita_conditions');
  const conditions = cloneDefault(DEFAULT_CONDITIONS);
  if (saved) {
    Object.keys(saved).forEach(k => {
      if (conditions[k]) conditions[k].enabled = saved[k];
    });
  }
  return conditions;
}

function loadWeights() {
  const saved = loadFromStorage('casita_weights');
  const weights = cloneDefault(DEFAULT_WEIGHTS);
  if (saved) {
    Object.keys(saved).forEach(k => {
      if (weights[k]) {
        // Soportar formato viejo (solo número) y nuevo (objeto)
        if (typeof saved[k] === 'number') {
          weights[k].weight = saved[k];
        } else if (typeof saved[k] === 'object') {
          weights[k].weight = saved[k].weight ?? weights[k].weight;
          weights[k].enabled = saved[k].enabled ?? true;
        }
      }
    });
  }
  return weights;
}

function loadConfig() {
  const saved = loadFromStorage('casita_config');
  if (saved) {
    // Migración: valor viejo de auto-refresh
    if (saved.AUTO_REFRESH === 60) saved.AUTO_REFRESH = DEFAULT_CONFIG.AUTO_REFRESH;
    // Migración: CREDITO_ARS viejo → usar defaults UVA nuevos
    if (saved.CREDITO_ARS !== undefined) {
      delete saved.CREDITO_ARS;
    }
    return { ...DEFAULT_CONFIG, ...saved };
  }
  return { ...DEFAULT_CONFIG };
}

function loadRefM2() {
  return loadFromStorage('casita_ref_m2') || { ...DEFAULT_REF_M2 };
}

// ============================================
// FUNCIONES DE GUARDADO ESPECÍFICAS
// ============================================

function saveConditions(conditions) {
  const toSave = {};
  Object.keys(conditions).forEach(k => { toSave[k] = conditions[k].enabled; });
  saveToStorage('casita_conditions', toSave);
}

function saveWeights(weights) {
  const toSave = {};
  Object.keys(weights).forEach(k => {
    toSave[k] = { weight: weights[k].weight, enabled: weights[k].enabled };
  });
  saveToStorage('casita_weights', toSave);
}

function saveConfig(config) {
  saveToStorage('casita_config', config);
}

function saveRefM2(refM2) {
  saveToStorage('casita_ref_m2', refM2);
}

// ============================================
// ESTADO GLOBAL
// ============================================

let CONDITIONS = loadConditions();
let WEIGHTS = loadWeights();
let CONFIG = loadConfig();
let REF_M2 = loadRefM2();

let state = {
  rawData: '',
  dataHash: null,  // Hash para detectar cambios en datos
  loading: false,
  error: null,
  lastUpdate: null,
  filterStatus: 'todos',
  filterOk: 'todos',
  filterBarrio: 'todos',
  filterActivo: 'todos',
  filterTier: 'todos',      // Filtro por tier (1-5)
  filterCredito: 'todos',   // Filtro apto crédito (si/no/?)
  searchText: '',           // Búsqueda por texto
  // Filtros booleanos (todos/si/no)
  filterTerraza: 'todos',
  filterBalcon: 'todos',
  filterPatio: 'todos',
  filterCochera: 'todos',
  filterLuminoso: 'todos',
  showFiltersExpanded: false,  // Filtros de atributos colapsados en mobile
  showHelp: false,
  sortBy: 'score',
  sortDir: 'desc',
  showConfig: false,
  configTab: 'general',
  autoRefreshEnabled: CONFIG.AUTO_REFRESH > 0,
  selectedProperty: null,
  viewMode: 'auto',
  negotiationPct: 0,
  dolarEstimado: null,
  dolarBNA: null,
  loadingDolar: false,
  uvaData: null,
  loadingUVA: false
};

let autoRefreshInterval = null;
