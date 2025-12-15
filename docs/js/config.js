// ============================================
// CONFIGURACIÓN Y ESTADO
// ============================================

const DEFAULT_CONFIG = {
  CREDITO_ARS: 126000000,
  DOLAR_BASE: 1450,
  PRESUPUESTO: 25000,
  MARGEN_REF: 0.12,
  ESCRIBANO: 0.0242,
  SELLOS_EXENTO: 140000,
  SELLOS: 0.0175,
  REGISTRALES: 0.004,
  INMOB: 0.0484,
  HIPOTECA: 0.01,
  CERTIFICADOS: 300,
  AUTO_REFRESH: 10,
};

const DEFAULT_REF_M2 = {
  "Flores": 1953, "Parque Chacabuco": 1951, "Liniers": 1857, "Monte Castro": 1854,
  "Floresta": 1683, "Parque Avellaneda": 1750, "Villa Luro": 1785, "Vélez Sarsfield": 1663,
  "Mataderos": 1629, "Paternal": 1897, "Caballito": 2357, "Villa Crespo": 2150,
  "Villa del Parque": 2063, "Villa Devoto": 2348, "Boedo": 1876
};

const DEFAULT_CONDITIONS = {
  activo:        { label: 'Activo',         enabled: true, desc: 'Solo publicaciones online' },
  apto_credito:  { label: 'Apto crédito',   enabled: true, desc: 'Solo las que aceptan crédito' },
  ok_presupuesto:{ label: 'En presupuesto', enabled: true, desc: 'Solo las que podés pagar' },
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
const SCORING_RULES = {
  // Atributos booleanos: si/no/missing
  terraza:     { type: 'boolean', bonus: 10, penaltyMissing: 5 },
  balcon:      { type: 'boolean', bonus: 10, penaltyMissing: 5 },
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
      { max: 0, score: 8 },    // Sin expensas
      { max: 80, score: 5 },   // Bajas
      { max: 150, score: 2 },  // Medias
      { max: 250, score: 0 },  // Altas
      { min: 251, score: -4 }, // Muy altas
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
// PERSISTENCIA LOCAL
// ============================================

function loadConditions() {
  try {
    const saved = localStorage.getItem('casita_conditions');
    if (saved) {
      const parsed = JSON.parse(saved);
      const conditions = JSON.parse(JSON.stringify(DEFAULT_CONDITIONS));
      Object.keys(parsed).forEach(k => {
        if (conditions[k]) conditions[k].enabled = parsed[k];
      });
      return conditions;
    }
    return JSON.parse(JSON.stringify(DEFAULT_CONDITIONS));
  } catch { return JSON.parse(JSON.stringify(DEFAULT_CONDITIONS)); }
}

function saveConditions(conditions) {
  const toSave = {};
  Object.keys(conditions).forEach(k => { toSave[k] = conditions[k].enabled; });
  localStorage.setItem('casita_conditions', JSON.stringify(toSave));
}

function loadWeights() {
  try {
    const saved = localStorage.getItem('casita_weights');
    if (saved) {
      const parsed = JSON.parse(saved);
      const weights = JSON.parse(JSON.stringify(DEFAULT_WEIGHTS));
      Object.keys(parsed).forEach(k => {
        if (weights[k]) {
          // Soportar formato viejo (solo número) y nuevo (objeto)
          if (typeof parsed[k] === 'number') {
            weights[k].weight = parsed[k];
          } else if (typeof parsed[k] === 'object') {
            weights[k].weight = parsed[k].weight ?? weights[k].weight;
            weights[k].enabled = parsed[k].enabled ?? true;
          }
        }
      });
      return weights;
    }
    return JSON.parse(JSON.stringify(DEFAULT_WEIGHTS));
  } catch { return JSON.parse(JSON.stringify(DEFAULT_WEIGHTS)); }
}

function saveWeights(weights) {
  const toSave = {};
  Object.keys(weights).forEach(k => {
    toSave[k] = { weight: weights[k].weight, enabled: weights[k].enabled };
  });
  localStorage.setItem('casita_weights', JSON.stringify(toSave));
}

function loadConfig() {
  try {
    const saved = localStorage.getItem('casita_config');
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed.AUTO_REFRESH === 60) {
        parsed.AUTO_REFRESH = DEFAULT_CONFIG.AUTO_REFRESH;
      }
      return { ...DEFAULT_CONFIG, ...parsed };
    }
    return { ...DEFAULT_CONFIG };
  } catch { return { ...DEFAULT_CONFIG }; }
}

function loadRefM2() {
  try {
    const saved = localStorage.getItem('casita_ref_m2');
    return saved ? JSON.parse(saved) : { ...DEFAULT_REF_M2 };
  } catch { return { ...DEFAULT_REF_M2 }; }
}

function saveConfig(config) {
  localStorage.setItem('casita_config', JSON.stringify(config));
}

function saveRefM2(refM2) {
  localStorage.setItem('casita_ref_m2', JSON.stringify(refM2));
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
  loading: false,
  error: null,
  lastUpdate: null,
  filterStatus: 'todos',
  filterOk: 'todos',
  filterBarrio: 'todos',
  filterActivo: 'todos',
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
  loadingDolar: false
};

let autoRefreshInterval = null;
