# 🏠 Dashboard Propiedades - Setup Guide

## Arquitectura

```
┌─────────────────────┐      ┌─────────────────────┐
│   Google Sheets     │ CSV  │   GitHub Pages      │
│   (tu data)         │ ───▶ │   (dashboard)       │
│                     │      │                     │
│ • Editás desde celu │      │ • Siempre online    │
│ • Compartible       │      │ • Gratis            │
│ • Backup automático │      │ • Se actualiza      │
└─────────────────────┘      └─────────────────────┘
```

---

## Paso 1: Crear Google Sheet

### 1.1 Nueva hoja
1. Ir a [sheets.google.com](https://sheets.google.com)
2. Crear hoja nueva → "Propiedades PH"

### 1.2 Estructura (Fila 1 = headers)

| A | B | C | D | E | F | G | H | I | J | K | L | M | N | O |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| id | direccion | barrio | precio | m2_cub | m2_tot | m2_terr | amb | apto_credito | terraza | expensas | inmobiliaria | status | notas | link | online |

### 1.3 Ejemplo fila 2:

```
1 | Alberdi 4600 | Parque Avellaneda | 105000 | 70 | 140 | 70 | 3 | si | si | | GOLDEN HAUS | Por ver | 40 años | https://argenprop.com/123 | online
```

### Campos importantes:
- **precio**: número sin símbolos (95000, no $95.000)
- **m2_cub**: metros cuadrados cubiertos
- **barrio**: debe coincidir exactamente con los de referencia
- **inmobiliaria**: si tiene valor → se suma comisión 4.84%
- **status**: Por ver / Visitado / Interesado / Descartado
- **online**: online / baja / ?meli / ?zonaprop

---

## Paso 2: Publicar como CSV

1. En Google Sheets: **Archivo** → **Compartir** → **Publicar en la web**
2. En el dropdown: seleccionar la hoja (o "Documento completo")
3. Formato: **CSV** (importante!)
4. Click **Publicar**
5. Copiar la URL que te da

La URL se ve algo así:
```
https://docs.google.com/spreadsheets/d/e/2PACX-1vR.../pub?output=csv
```

---

## Paso 3: Deploy en GitHub Pages

### 3.1 Crear repositorio
1. Ir a [github.com](https://github.com) → New repository
2. Nombre: `propiedades-dashboard`
3. Público
4. Crear

### 3.2 Subir archivos

Necesitás estos archivos en el repo:

**index.html**
```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Propiedades PH</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <script src="https://unpkg.com/recharts@2/umd/Recharts.js"></script>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel" src="app.jsx"></script>
</body>
</html>
```

**app.jsx** → El archivo dashboard_gsheets.jsx (renombralo a app.jsx)

### 3.3 Activar GitHub Pages
1. Settings → Pages
2. Source: Deploy from a branch
3. Branch: main / root
4. Save

Tu dashboard estará en: `https://TU-USUARIO.github.io/propiedades-dashboard`

---

## Paso 4: Conectar Sheet al Dashboard

1. Abrir tu dashboard en GitHub Pages
2. Click ⚙️ (configuración)
3. Pegar la URL del CSV de Google Sheets
4. Click "Conectar"

---

## Actualizar datos

1. Editás la Google Sheet (desde PC o celu)
2. En el dashboard → click "↻ Refresh"
3. Los datos se actualizan al instante

---

## Barrios soportados (para referencia $/m²)

El dashboard tiene precargados estos barrios con su $/m² de referencia:

| Barrio | $/m² |
|--------|------|
| Flores | 1953 |
| Parque Chacabuco | 1951 |
| Liniers | 1857 |
| Monte Castro | 1854 |
| Floresta | 1683 |
| Parque Avellaneda | 1750 |
| Villa Luro | 1785 |
| Vélez Sarsfield | 1663 |
| Mataderos | 1629 |
| Paternal | 1897 |
| Caballito | 2357 |
| Villa Crespo | 2150 |
| Villa del Parque | 2063 |
| Villa Devoto | 2348 |
| Boedo | 1876 |

**Importante**: El nombre del barrio en tu sheet debe ser EXACTO a esta lista.

---

## Fórmulas que calcula el dashboard

| Concepto | Fórmula |
|----------|---------|
| Tu 10% | MAX(precio - 86000, precio × 10%) |
| Escribano | precio × 2% × 1.21 |
| Sellos | 0 si precio ≤ 140k, sino precio × 1.75% |
| Registrales | precio × 0.4% |
| Inmobiliaria | Si tiene → precio × 4% × 1.21 |
| Hipoteca | precio × 1% |
| Certificados | $300 fijo |
| **TOTAL** | Suma de todo |
| **OK?** | TOTAL ≤ $25.000 |

---

## Tips

- **Desde el celu**: Instalá la app Google Sheets, editá, refresh en dashboard
- **Compartir**: Podés compartir la Sheet con J para que ambos editen
- **Backup**: Google Sheets tiene historial de versiones automático
- **Offline**: El dashboard necesita internet, pero la sheet se puede editar offline

---

## Troubleshooting

**"Error cargando datos"**
- Verificá que la sheet esté publicada como CSV
- La URL debe terminar en `?output=csv` o `/pub?output=csv`

**Los barrios no muestran referencia**
- Verificá que el nombre sea exacto (mayúsculas, tildes)
- "Parque Avellaneda" ≠ "parque avellaneda" ≠ "P. Avellaneda"

**No se actualiza**
- Google Sheets puede tardar ~5 min en propagar cambios al CSV público
- Probá hacer un cambio pequeño y esperar
