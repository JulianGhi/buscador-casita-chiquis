# Casita Chiquis - Product Overview

## El Problema

Comprar una propiedad con crédito hipotecario en Argentina es un proceso complejo:

1. **Fragmentación**: Hay que buscar en 3-4 portales (Zonaprop, Argenprop, MercadoLibre, etc.)
2. **Cálculos manuales**: ¿Me alcanza? ¿Cuánto tengo que juntar? Nadie te lo dice
3. **Variables cambiantes**: El dólar, el crédito, la negociación... todo afecta
4. **Sin priorización**: Miles de resultados, ¿cuál mirar primero?
5. **Tracking manual**: Planillas Excel, capturas de pantalla, caos

## La Solución

**Casita Chiquis** es una plataforma que centraliza la búsqueda de propiedades y responde la pregunta clave: **"¿Me alcanza para esta propiedad?"**

---

## Funcionalidades Implementadas (MVP)

### 1. Agregador Multi-Portal
- Scraping de **Argenprop**, **Zonaprop** y **MercadoLibre**
- Base de datos unificada con deduplicación
- Actualización manual o programable

### 2. Dashboard Interactivo
- **Vista tabla** (desktop) y **cards** (mobile)
- Filtros: barrio, status, apto crédito, precio
- Ordenamiento por "mejor candidato"
- Búsqueda de texto libre

### 3. Sistema de Scoring Inteligente
- **5 Tiers** de prioridad (T1 = mejor candidato)
- **Score numérico** basado en preferencias personalizables:
  - Precio vs mercado
  - Metros cuadrados
  - Ambientes, baños, antigüedad
  - Amenities: terraza, balcón, patio, cochera
  - Luminosidad, disposición
- Penalización por datos faltantes (incentiva completar info)

### 4. Calculadora de Costos Completa
- Anticipo (mínimo 10% o diferencia real)
- Gastos de escrituración:
  - Escribano (~2%)
  - Sellos (~1.2%, exento hasta cierto monto)
  - Registrales (~0.6%)
  - Hipoteca (~0.45%)
  - Certificados (fijo)
- Comisión inmobiliaria (si aplica)
- **Total "a juntar"** vs tu presupuesto disponible

### 5. Simulador de Escenarios
- **Slider de negociación**: ¿Y si consigo 10% de descuento?
- **Slider de dólar**: ¿Y si el dólar sube a $1500?
- Recálculo en tiempo real de todo
- Indicador de uso del crédito (% utilizado)
- Sugerencia de "quita necesaria" para que entre en presupuesto

### 6. Detección de Inconsistencias
- Warnings automáticos:
  - m² que no cierran (cub + desc ≠ total)
  - Balcón/terraza declarado pero sin m² descubiertos
  - Datos faltantes que afectan el score
- Visualización clara en tabla y modal

### 7. Sistema de Backups (Prints)
- Guardado de PDFs de avisos
- Detección automática por ID de portal
- Comparación de 3 fuentes: Sheet vs Web vs PDF
- Alertas de discrepancias (¿cambió el precio?)

### 8. Sync con Google Sheets
- Bidireccional: pull y push
- Scraping automático de links nuevos
- Validaciones al guardar
- Cálculo automático de m² faltantes

### 9. Cotización Dólar en Tiempo Real
- Dólar BNA actualizado
- Variación día/semana/mes
- Impacto en crédito visible

### 10. Mobile-First
- Dashboard responsive
- Sliders touch-friendly
- Cards optimizadas para scroll vertical

---

## Roadmap: Qué Podríamos Implementar

### Fase 2: Multi-Usuario (3-4 semanas)

| Feature | Descripción | Impacto |
|---------|-------------|---------|
| **Auth** | Login con Google/email | Crítico |
| **Perfiles** | Cada usuario con su config (crédito, presupuesto, pesos) | Crítico |
| **DB en la nube** | Migrar de JSON/SQLite a PostgreSQL/Supabase | Crítico |
| **Onboarding** | Wizard: "¿Cuánto crédito tenés? ¿Presupuesto?" | Alto |

### Fase 3: Alertas y Automatización (2-3 semanas)

| Feature | Descripción | Impacto |
|---------|-------------|---------|
| **Alertas email** | "Nueva propiedad en Caballito que entra en tu presupuesto" | Alto |
| **Push notifications** | Para app mobile | Medio |
| **Scraping automático** | Cron job cada 6 horas | Alto |
| **Detección de bajadas** | "Esta propiedad se vendió" | Medio |

### Fase 4: Inteligencia de Mercado (4-6 semanas)

| Feature | Descripción | Impacto |
|---------|-------------|---------|
| **Historial de precios** | Ver evolución del precio de cada propiedad | Alto |
| **Precio/m² por barrio** | Benchmarks automáticos | Alto |
| **Comparables** | "Propiedades similares se vendieron a $X" | Medio |
| **Score de oportunidad** | "Esta está 15% bajo mercado" | Alto |
| **Predicción de negociación** | Basado en tiempo publicado | Bajo |

### Fase 5: Integraciones (6-8 semanas)

| Feature | Descripción | Impacto |
|---------|-------------|---------|
| **Simulador de bancos** | Conectar con APIs de Banco Nación, Hipotecario, etc. | Alto |
| **Precalificación** | "Con tu perfil, podrías acceder a $X de crédito" | Alto |
| **Contacto directo** | Enviar consulta desde la app | Medio |
| **Agenda de visitas** | Calendario integrado | Bajo |

### Fase 6: App Mobile Nativa (8-12 semanas)

| Feature | Descripción | Impacto |
|---------|-------------|---------|
| **React Native / Flutter** | App nativa iOS/Android | Alto |
| **Modo offline** | Ver propiedades guardadas sin conexión | Medio |
| **Cámara** | Escanear QR de avisos, sacar fotos en visitas | Bajo |
| **GPS** | "Propiedades cerca de tu ubicación" | Medio |

---

## Stack Técnico Actual

| Componente | Tecnología |
|------------|------------|
| **Backend/Scraping** | Python, httpx, Playwright, BeautifulSoup |
| **Base de datos** | SQLite + JSON (local) |
| **Dashboard** | Vanilla JS, Tailwind CSS, Chart.js |
| **Hosting** | GitHub Pages (estático) |
| **Sync** | Google Sheets API |
| **CLI** | Typer + Rich |

### Stack Propuesto para Escalar

| Componente | Tecnología |
|------------|------------|
| **Backend** | FastAPI o Django |
| **Base de datos** | PostgreSQL + Supabase |
| **Auth** | Supabase Auth / Auth0 |
| **Frontend** | React o Vue (o seguir vanilla) |
| **Hosting** | Vercel / Railway |
| **Scraping** | Celery + Redis (jobs en background) |
| **Mobile** | React Native / PWA |

---

## Modelo de Negocio

### Opción A: Freemium B2C

| Plan | Precio | Incluye |
|------|--------|---------|
| **Free** | $0 | 10 propiedades, 1 búsqueda guardada |
| **Pro** | $5-10 USD/mes | Ilimitado, alertas, historial |
| **Family** | $15 USD/mes | 3 usuarios, compartir favoritos |

### Opción B: B2B para Brokers Hipotecarios

| Plan | Precio | Incluye |
|------|--------|---------|
| **Broker** | $50 USD/mes | White-label, hasta 50 clientes |
| **Inmobiliaria** | $200 USD/mes | Ilimitado, API, analytics |

### Opción C: Afiliación

- Comisión por crédito hipotecario originado (0.1-0.5% del monto)
- Requiere partnership con bancos

---

## Métricas de Éxito

| Métrica | Objetivo Año 1 |
|---------|----------------|
| **Usuarios registrados** | 5,000 |
| **Usuarios activos (MAU)** | 1,000 |
| **Propiedades trackeadas** | 50,000 |
| **Conversión Free→Pro** | 5% |
| **MRR** | $2,500 USD |

---

## Competencia

| Competidor | Qué hace | Diferencial nuestro |
|------------|----------|---------------------|
| **Zonaprop/Argenprop** | Portal de avisos | No calculan affordability |
| **Properati** | Comparador + analytics | Enfocado en inversores, no crédito |
| **Bancos** | Simuladores de crédito | No buscan propiedades |
| **Brokers** | Servicio manual | No escala, depende de personas |

**Nuestro diferencial**: Somos el único que une **búsqueda de propiedades + cálculo de affordability con crédito hipotecario** en una sola herramienta.

---

## Equipo Necesario

| Rol | Dedicación | Para qué |
|-----|------------|----------|
| **Founder/Product** | Full-time | Visión, producto, usuarios |
| **Full-stack Dev** | Full-time | Backend, frontend, infra |
| **Growth/Marketing** | Part-time | Adquisición, contenido |
| **Legal** | Consultor | Términos, scraping, datos |

---

## Inversión Estimada (MVP → Producto)

| Concepto | Costo |
|----------|-------|
| **Desarrollo** (6 meses, 1 dev) | $15,000 - $25,000 USD |
| **Infra** (servers, DB, etc.) | $100 - $300 USD/mes |
| **Legal** (términos, privacidad) | $1,000 - $2,000 USD |
| **Marketing inicial** | $2,000 - $5,000 USD |
| **Total MVP comercial** | ~$25,000 - $35,000 USD |

---

## Próximos Pasos

1. **Validar demanda**: Landing page + waitlist
2. **10 usuarios beta**: Amigos/conocidos buscando con crédito
3. **Iterar**: ¿Qué funciona? ¿Qué falta?
4. **Decidir modelo**: B2C freemium vs B2B
5. **Buscar funding** (si aplica) o bootstrappear

---

## Contacto

**Proyecto**: Casita Chiquis
**Repo**: github.com/JulianGhi/buscador-casita-chiquis
**Versión actual**: v7.6 (MVP funcional)
**Estado**: En uso personal, listo para expandir
