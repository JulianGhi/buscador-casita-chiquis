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
  bajo_mercado:  { label: 'Bajo mercado',   weight: 7,  enabled: true, desc: 'Precio bajo vs promedio barrio' },
  m2:            { label: 'M² cubiertos',   weight: 5,  enabled: true, desc: 'Más m² = mejor' },
  terraza:       { label: 'Terraza',        weight: 5,  enabled: true, desc: 'Tiene terraza' },
  balcon:        { label: 'Balcón',         weight: 3,  enabled: true, desc: 'Tiene balcón' },
  cochera:       { label: 'Cochera',        weight: 4,  enabled: true, desc: 'Tiene cochera' },
  luminosidad:   { label: 'Luminoso',       weight: 4,  enabled: true, desc: 'Es luminoso' },
  frente:        { label: 'Al frente',      weight: 3,  enabled: true, desc: 'Disposición frente' },
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
