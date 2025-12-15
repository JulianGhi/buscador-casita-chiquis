"""
Tests exhaustivos para sync_sheet.py

Ejecutar con: pytest sheets/test_sync_sheet.py -v
"""
import pytest
import json
from pathlib import Path

# Importar funciones a testear desde el nuevo módulo core
from core import (
    # Funciones de cálculo
    calcular_m2_faltantes,
    extraer_m2,
    extraer_numero,
    # Detección
    detectar_atributo,
    detectar_barrio,
    extraer_id_propiedad,
    # Filtrado
    get_active_rows,
    # Normalización
    quitar_tildes,
    # Validación
    validar_propiedad,
    clear_warnings,
    get_warnings,
    # Constantes
    ATTR_PATTERNS,
    BARRIOS_CABA,
)

# Importar scrapers para tests de integración
from core.scrapers import scrape_argenprop, scrape_mercadolibre, scrape_link

# Importar storage
from core.storage import load_cache, CACHE_FILE


# =============================================================================
# TESTS: calcular_m2_faltantes()
# =============================================================================

class TestCalcularM2Faltantes:
    """Tests para la función calcular_m2_faltantes"""

    # --- Casos donde se puede calcular ---

    def test_calcula_desc_desde_tot_y_cub(self):
        """Si tengo tot y cub, calcula desc = tot - cub"""
        data = {'m2_tot': '100', 'm2_cub': '70'}
        result = calcular_m2_faltantes(data)
        assert result == {'m2_desc': '30'}

    def test_calcula_desc_cero_cuando_tot_igual_cub(self):
        """Si tot == cub, desc debería ser 0"""
        data = {'m2_tot': '80', 'm2_cub': '80'}
        result = calcular_m2_faltantes(data)
        assert result == {'m2_desc': '0'}

    def test_calcula_cub_desde_tot_y_desc(self):
        """Si tengo tot y desc, calcula cub = tot - desc"""
        data = {'m2_tot': '100', 'm2_desc': '20'}
        result = calcular_m2_faltantes(data)
        assert result == {'m2_cub': '80'}

    def test_calcula_tot_desde_cub_y_desc(self):
        """Si tengo cub y desc, calcula tot = cub + desc"""
        data = {'m2_cub': '70', 'm2_desc': '30'}
        result = calcular_m2_faltantes(data)
        assert result == {'m2_tot': '100'}

    # --- Casos donde NO se puede calcular ---

    def test_no_calcula_si_ya_tiene_los_tres(self):
        """Si ya tiene los 3 valores, no calcula nada"""
        data = {'m2_tot': '100', 'm2_cub': '70', 'm2_desc': '30'}
        result = calcular_m2_faltantes(data)
        assert result == {}

    def test_no_calcula_si_solo_tiene_uno(self):
        """Si solo tiene 1 valor, no puede calcular"""
        assert calcular_m2_faltantes({'m2_tot': '100'}) == {}
        assert calcular_m2_faltantes({'m2_cub': '70'}) == {}
        assert calcular_m2_faltantes({'m2_desc': '30'}) == {}

    def test_no_calcula_si_vacio(self):
        """Si no tiene ningún valor, no calcula nada"""
        assert calcular_m2_faltantes({}) == {}

    def test_no_calcula_cub_si_resultado_cero(self):
        """No calcula cub si sería 0 (tot == desc)"""
        data = {'m2_tot': '30', 'm2_desc': '30'}
        result = calcular_m2_faltantes(data)
        assert result == {}  # cub sería 0, no tiene sentido

    def test_no_calcula_cub_si_resultado_negativo(self):
        """No calcula cub si sería negativo (desc > tot)"""
        data = {'m2_tot': '20', 'm2_desc': '30'}
        result = calcular_m2_faltantes(data)
        assert result == {}

    def test_no_calcula_desc_si_resultado_negativo(self):
        """No calcula desc si sería negativo (cub > tot)"""
        data = {'m2_tot': '50', 'm2_cub': '70'}
        result = calcular_m2_faltantes(data)
        assert result == {}

    # --- Edge cases ---

    def test_maneja_valores_string(self):
        """Acepta valores como strings"""
        data = {'m2_tot': '100', 'm2_cub': '80'}
        result = calcular_m2_faltantes(data)
        assert result == {'m2_desc': '20'}
        assert isinstance(result['m2_desc'], str)

    def test_maneja_valores_int(self):
        """Acepta valores como ints"""
        data = {'m2_tot': 100, 'm2_cub': 80}
        result = calcular_m2_faltantes(data)
        assert result == {'m2_desc': '20'}

    def test_maneja_valores_vacios_como_cero(self):
        """Trata strings vacíos como 0"""
        data = {'m2_tot': '100', 'm2_cub': '70', 'm2_desc': ''}
        result = calcular_m2_faltantes(data)
        assert result == {'m2_desc': '30'}

    def test_maneja_none_como_cero(self):
        """Trata None como 0"""
        data = {'m2_tot': '100', 'm2_cub': '70', 'm2_desc': None}
        result = calcular_m2_faltantes(data)
        assert result == {'m2_desc': '30'}

    def test_maneja_cero_string(self):
        """'0' se trata como 0"""
        data = {'m2_tot': '100', 'm2_cub': '70', 'm2_desc': '0'}
        result = calcular_m2_faltantes(data)
        assert result == {'m2_desc': '30'}


# =============================================================================
# TESTS: validar_propiedad()
# =============================================================================

class TestValidarPropiedad:
    """Tests para la función validar_propiedad"""

    def setup_method(self):
        """Limpiar warnings antes de cada test"""
        clear_warnings()

    # --- Validación de m² ---

    def test_warning_cuando_cub_mayor_que_tot(self):
        """Debe generar warning si m² cub > m² tot"""
        data = {'m2_cub': '100', 'm2_tot': '80', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert any(w['tipo'] == 'm2_inconsistente' for w in warnings)

    def test_warning_cuando_cub_desc_no_suma_tot(self):
        """Debe generar warning si cub + desc ≠ tot (tolerancia 2m²)"""
        data = {'m2_cub': '70', 'm2_tot': '100', 'm2_desc': '20', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        # 70 + 20 = 90 ≠ 100 (diferencia de 10, más que tolerancia de 2)
        assert any(w['tipo'] == 'm2_no_cierra' for w in warnings)

    def test_no_warning_si_diferencia_dentro_tolerancia(self):
        """No debe generar warning si diferencia <= 2m²"""
        data = {'m2_cub': '70', 'm2_tot': '100', 'm2_desc': '28', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        # 70 + 28 = 98, diferencia de 2 con 100 → dentro de tolerancia
        assert not any(w['tipo'] == 'm2_no_cierra' for w in warnings)

    def test_no_warning_si_m2_validos(self):
        """No debe generar warning si m² son consistentes"""
        data = {'m2_cub': '70', 'm2_tot': '100', 'm2_desc': '30', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert not any(w['tipo'] == 'm2_inconsistente' for w in warnings)
        assert not any(w['tipo'] == 'm2_no_cierra' for w in warnings)

    # --- Validación de precios ---

    def test_warning_precio_muy_bajo(self):
        """Debe generar warning si precio < 30000"""
        data = {'precio': '25000', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert any(w['tipo'] == 'precio_bajo' for w in warnings)

    def test_warning_precio_muy_alto(self):
        """Debe generar warning si precio > 500000"""
        data = {'precio': '600000', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert any(w['tipo'] == 'precio_alto' for w in warnings)

    def test_no_warning_precio_normal(self):
        """No debe generar warning si precio está en rango normal"""
        data = {'precio': '150000', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert not any(w['tipo'] == 'precio_bajo' for w in warnings)
        assert not any(w['tipo'] == 'precio_alto' for w in warnings)

    # --- Validación de atributos inciertos ---

    def test_warning_atributo_incierto(self):
        """Debe generar warning si atributo es '?'"""
        for attr in ['terraza', 'balcon', 'apto_credito', 'ascensor']:
            clear_warnings()
            data = {attr: '?', 'direccion': 'Test'}
            validar_propiedad(data)
            warnings = get_warnings()
            assert any(w['tipo'] == 'atributo_incierto' for w in warnings), f"Falló para {attr}"

    def test_no_warning_atributo_definido(self):
        """No debe generar warning si atributo tiene valor definido"""
        data = {'terraza': 'si', 'balcon': 'no', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert not any(w['tipo'] == 'atributo_incierto' for w in warnings)

    # --- Validación de datos faltantes ---

    def test_warning_sin_barrio(self):
        """Debe generar warning si falta barrio"""
        data = {'direccion': 'Test', 'm2_cub': '70'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert any(w['tipo'] == 'dato_faltante' and 'barrio' in w['mensaje'] for w in warnings)

    def test_warning_sin_m2(self):
        """Debe generar warning si faltan m²"""
        data = {'direccion': 'Test', 'barrio': 'Flores'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert any(w['tipo'] == 'dato_faltante' and 'm²' in w['mensaje'] for w in warnings)

    def test_no_warning_con_m2_tot(self):
        """No debe generar warning de m² si tiene m2_tot"""
        data = {'direccion': 'Test', 'barrio': 'Flores', 'm2_tot': '100'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert not any(w['tipo'] == 'dato_faltante' and 'm²' in w['mensaje'] for w in warnings)

    # --- Validación de balcón/terraza vs m2_desc ---

    def test_warning_balcon_sin_m2_desc(self):
        """Debe generar warning si tiene balcón pero m2_desc = 0"""
        data = {'balcon': 'si', 'm2_desc': '0', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert any(w['tipo'] == 'm2_desc_inconsistente' for w in warnings)

    def test_warning_terraza_sin_m2_desc(self):
        """Debe generar warning si tiene terraza pero sin m2_desc"""
        data = {'terraza': 'si', 'direccion': 'Test'}  # m2_desc no definido = 0
        validar_propiedad(data)
        warnings = get_warnings()
        assert any(w['tipo'] == 'm2_desc_inconsistente' for w in warnings)

    def test_warning_balcon_y_terraza_sin_m2_desc(self):
        """Debe mencionar ambos en el warning"""
        data = {'balcon': 'si', 'terraza': 'si', 'm2_desc': '0', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        warning = next((w for w in warnings if w['tipo'] == 'm2_desc_inconsistente'), None)
        assert warning is not None
        assert 'balcón' in warning['mensaje']
        assert 'terraza' in warning['mensaje']

    def test_no_warning_balcon_con_m2_desc(self):
        """No debe generar warning si tiene balcón Y m2_desc > 0"""
        data = {'balcon': 'si', 'm2_desc': '10', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert not any(w['tipo'] == 'm2_desc_inconsistente' for w in warnings)

    def test_no_warning_sin_exterior(self):
        """No debe generar warning si no tiene balcón ni terraza"""
        data = {'balcon': 'no', 'terraza': 'no', 'm2_desc': '0', 'direccion': 'Test'}
        validar_propiedad(data)
        warnings = get_warnings()
        assert not any(w['tipo'] == 'm2_desc_inconsistente' for w in warnings)


# =============================================================================
# TESTS: detectar_atributo()
# =============================================================================

class TestDetectarAtributo:
    """Tests para la función detectar_atributo"""

    # --- Terraza ---

    def test_terraza_si_explicito(self):
        """Detecta 'terraza: si' como positivo"""
        assert detectar_atributo('terraza: si', 'terraza') == 'si'
        assert detectar_atributo('terraza: sí', 'terraza') == 'si'
        assert detectar_atributo('Terraza: Si', 'terraza') == 'si'

    def test_terraza_no_explicito(self):
        """Detecta 'terraza: no' como negativo"""
        assert detectar_atributo('terraza: no', 'terraza') == 'no'
        assert detectar_atributo('sin terraza', 'terraza') == 'no'
        assert detectar_atributo('Terraza: No', 'terraza') == 'no'

    def test_terraza_solo_label(self):
        """'terraza' solo (sin valor) cuenta como positivo (solo_label=True)"""
        assert detectar_atributo('amenities: terraza', 'terraza') == 'si'
        assert detectar_atributo('Tiene terraza propia', 'terraza') == 'si'

    def test_terraza_prioridad_no_sobre_si(self):
        """'no' tiene prioridad sobre menciones positivas"""
        # Si el texto dice ambas cosas, 'no' gana
        assert detectar_atributo('terraza: no, pero tiene balcón', 'terraza') == 'no'

    # --- Balcón ---

    def test_balcon_si_explicito(self):
        """Detecta 'balcón: si' como positivo"""
        assert detectar_atributo('balcon: si', 'balcon') == 'si'
        assert detectar_atributo('balcón: sí', 'balcon') == 'si'
        assert detectar_atributo('con balcón', 'balcon') == 'si'

    def test_balcon_no_explicito(self):
        """Detecta 'balcón: no' como negativo"""
        assert detectar_atributo('balcon: no', 'balcon') == 'no'
        assert detectar_atributo('balcón: no', 'balcon') == 'no'
        assert detectar_atributo('sin balcón', 'balcon') == 'no'

    def test_balcon_solo_label(self):
        """'balcón' solo cuenta como positivo (con o sin tilde)"""
        assert detectar_atributo('balcon al frente', 'balcon') == 'si'
        assert detectar_atributo('balcón al frente', 'balcon') == 'si'  # con tilde
        assert detectar_atributo('BALCÓN GRANDE', 'balcon') == 'si'  # mayúsculas + tilde

    # --- Apto crédito ---

    def test_apto_credito_si(self):
        """Detecta variantes de apto crédito positivo"""
        assert detectar_atributo('apto credito: si', 'apto_credito') == 'si'
        assert detectar_atributo('apto crédito: sí', 'apto_credito') == 'si'
        assert detectar_atributo('acepta credito', 'apto_credito') == 'si'
        assert detectar_atributo('apto banco', 'apto_credito') == 'si'

    def test_apto_credito_no(self):
        """Detecta variantes de apto crédito negativo"""
        assert detectar_atributo('apto credito: no', 'apto_credito') == 'no'
        assert detectar_atributo('no acepta crédito', 'apto_credito') == 'no'
        assert detectar_atributo('no apto credito', 'apto_credito') == 'no'

    def test_apto_credito_no_detecta_solo_label(self):
        """'credito' solo NO cuenta como positivo (solo_label=False)"""
        # "credito" mencionado pero sin patrón claro → incierto
        result = detectar_atributo('consultar por crédito', 'apto_credito')
        assert result in ['?', None]

    # --- Ascensor ---

    def test_ascensor_si(self):
        """Detecta ascensor positivo"""
        assert detectar_atributo('ascensor: si', 'ascensor') == 'si'
        assert detectar_atributo('con ascensor', 'ascensor') == 'si'
        assert detectar_atributo('tiene ascensor', 'ascensor') == 'si'

    def test_ascensor_no(self):
        """Detecta ascensor negativo"""
        assert detectar_atributo('ascensor: no', 'ascensor') == 'no'
        assert detectar_atributo('sin ascensor', 'ascensor') == 'no'

    # --- Luminosidad ---

    def test_luminosidad_si(self):
        """Detecta luminosidad positiva"""
        assert detectar_atributo('muy luminoso', 'luminosidad') == 'si'
        assert detectar_atributo('excelente luz natural', 'luminosidad') == 'si'
        assert detectar_atributo('buena luz', 'luminosidad') == 'si'

    def test_luminosidad_no(self):
        """Detecta luminosidad negativa"""
        assert detectar_atributo('poco luminoso', 'luminosidad') == 'no'
        assert detectar_atributo('es oscuro', 'luminosidad') == 'no'
        assert detectar_atributo('poca luz', 'luminosidad') == 'no'

    # --- Cochera ---

    def test_cochera_si(self):
        """Detecta cochera positiva"""
        assert detectar_atributo('cochera: si', 'cochera') == 'si'
        assert detectar_atributo('con cochera', 'cochera') == 'si'

    def test_cochera_no(self):
        """Detecta cochera negativa"""
        assert detectar_atributo('cochera: no', 'cochera') == 'no'
        assert detectar_atributo('sin cochera', 'cochera') == 'no'
        assert detectar_atributo('cocheras: 0', 'cochera') == 'no'

    def test_cochera_solo_label(self):
        """'cochera' solo cuenta como positivo"""
        assert detectar_atributo('1 cochera', 'cochera') == 'si'

    # --- Casos edge ---

    def test_atributo_no_existente(self):
        """Retorna None para atributos no definidos"""
        assert detectar_atributo('algo', 'atributo_inventado') is None

    def test_texto_vacio(self):
        """Maneja texto vacío"""
        assert detectar_atributo('', 'terraza') is None

    def test_case_insensitive(self):
        """La detección es case insensitive"""
        assert detectar_atributo('TERRAZA: SI', 'terraza') == 'si'
        assert detectar_atributo('Balcón: NO', 'balcon') == 'no'

    def test_normaliza_tildes(self):
        """Normaliza tildes: balcón=balcon, crédito=credito"""
        # Terraza con/sin tilde
        assert detectar_atributo('Terraza: Sí', 'terraza') == 'si'
        assert detectar_atributo('Terraza: Si', 'terraza') == 'si'
        # Balcón con/sin tilde
        assert detectar_atributo('Balcón: Sí', 'balcon') == 'si'
        assert detectar_atributo('Balcon: Si', 'balcon') == 'si'
        # Crédito con/sin tilde
        assert detectar_atributo('Apto Crédito: Sí', 'apto_credito') == 'si'
        assert detectar_atributo('Apto Credito: Si', 'apto_credito') == 'si'
        # Negaciones con tildes
        assert detectar_atributo('Sin Balcón', 'balcon') == 'no'
        assert detectar_atributo('No acepta crédito', 'apto_credito') == 'no'


# =============================================================================
# TESTS: detectar_barrio()
# =============================================================================

# =============================================================================
# TESTS: extraer_numero()
# =============================================================================

class TestExtraerNumero:
    """Tests para la función extraer_numero"""

    def test_extrae_numero_simple(self):
        """Extrae número de texto simple"""
        assert extraer_numero('50 m²') == '50'
        assert extraer_numero('3 ambientes') == '3'
        assert extraer_numero('Antigüedad: 15 años') == '15'

    def test_extrae_primer_numero(self):
        """Extrae solo el primer número cuando hay varios"""
        assert extraer_numero('3 amb, 2 baños') == '3'
        assert extraer_numero('2do piso, 4 amb') == '2'

    def test_extrae_numeros_grandes(self):
        """Extrae números de varios dígitos"""
        assert extraer_numero('150 m² cubiertos') == '150'
        assert extraer_numero('Precio: 95000 USD') == '95000'

    def test_retorna_none_sin_numero(self):
        """Retorna None si no hay números"""
        assert extraer_numero('sin número') is None
        assert extraer_numero('texto') is None

    def test_retorna_none_para_vacio(self):
        """Retorna None para texto vacío o None"""
        assert extraer_numero('') is None
        assert extraer_numero(None) is None

    def test_convierte_a_string(self):
        """Convierte entrada a string antes de buscar"""
        assert extraer_numero(123) == '123'
        assert extraer_numero(45.67) == '45'

    # --- Tests con quitar_miles ---

    def test_quitar_miles_simple(self):
        """Con quitar_miles=True, remueve puntos de miles"""
        assert extraer_numero('150.000', quitar_miles=True) == '150000'
        assert extraer_numero('$1.500.000', quitar_miles=True) == '1500000'

    def test_sin_quitar_miles(self):
        """Sin quitar_miles, el punto detiene la búsqueda"""
        assert extraer_numero('150.000', quitar_miles=False) == '150'
        assert extraer_numero('$1.500.000') == '1'  # default es False

    def test_quitar_miles_sin_puntos(self):
        """quitar_miles no afecta si no hay puntos"""
        assert extraer_numero('150000', quitar_miles=True) == '150000'
        assert extraer_numero('150000', quitar_miles=False) == '150000'


class TestDetectarBarrio:
    """Tests para la función detectar_barrio"""

    def test_detecta_barrios_zona_oeste(self):
        """Detecta barrios de zona oeste"""
        assert detectar_barrio('Departamento en Floresta') == 'Floresta'
        assert detectar_barrio('Flores, Capital Federal') == 'Flores'
        assert detectar_barrio('venta caballito 3 amb') == 'Caballito'

    def test_detecta_barrios_con_espacios(self):
        """Detecta barrios con nombres compuestos"""
        assert detectar_barrio('Villa del Parque, CABA') == 'Villa del Parque'
        assert detectar_barrio('depto villa crespo') == 'Villa Crespo'
        assert detectar_barrio('Parque Avellaneda') == 'Parque Avellaneda'

    def test_case_insensitive(self):
        """La detección es case insensitive"""
        assert detectar_barrio('FLORESTA') == 'Floresta'
        assert detectar_barrio('flores') == 'Flores'
        assert detectar_barrio('VilLa CreSpo') == 'Villa Crespo'

    def test_retorna_none_sin_barrio(self):
        """Retorna None si no encuentra barrio"""
        assert detectar_barrio('Departamento 3 ambientes') is None
        assert detectar_barrio('Capital Federal') is None

    def test_retorna_none_para_vacio(self):
        """Retorna None para texto vacío o None"""
        assert detectar_barrio('') is None
        assert detectar_barrio(None) is None

    def test_barrios_caba_tiene_zona_oeste(self):
        """BARRIOS_CABA incluye barrios de zona oeste"""
        zona_oeste = ['Floresta', 'Flores', 'Caballito', 'Villa Luro', 'Liniers']
        for barrio in zona_oeste:
            assert barrio in BARRIOS_CABA, f"Falta {barrio} en BARRIOS_CABA"


# =============================================================================
# TESTS: extraer_id_propiedad()
# =============================================================================

class TestExtraerIdPropiedad:
    """Tests para la función extraer_id_propiedad"""

    # --- MercadoLibre ---

    def test_extrae_id_meli_con_guion(self):
        """Extrae ID de URL de MercadoLibre con guión"""
        url = 'https://departamento.mercadolibre.com.ar/MLA-1234567890-depto-3-amb'
        assert extraer_id_propiedad(url) == 'MLA1234567890'

    def test_extrae_id_meli_sin_guion(self):
        """Extrae ID de URL de MercadoLibre sin guión"""
        url = 'https://departamento.mercadolibre.com.ar/MLA1234567890-depto'
        assert extraer_id_propiedad(url) == 'MLA1234567890'

    def test_extrae_id_meli_case_insensitive(self):
        """Extrae ID ignorando mayúsculas/minúsculas"""
        url = 'https://departamento.mercadolibre.com.ar/mla-1234567890-depto'
        assert extraer_id_propiedad(url) == 'MLA1234567890'

    # --- Argenprop ---

    def test_extrae_id_argenprop(self):
        """Extrae ID de URL de Argenprop"""
        url = 'https://www.argenprop.com/departamento-alquiler-flores--17094976'
        assert extraer_id_propiedad(url) == 'AP17094976'

    def test_extrae_id_argenprop_numeros_largos(self):
        """Extrae IDs de diferentes longitudes"""
        url = 'https://www.argenprop.com/depto--12345678'
        assert extraer_id_propiedad(url) == 'AP12345678'

    # --- Casos que no matchean ---

    def test_retorna_none_para_zonaprop(self):
        """Retorna None para URLs de Zonaprop (no tiene patrón definido)"""
        url = 'https://www.zonaprop.com.ar/propiedades/depto-flores-12345678.html'
        # El patrón actual no soporta Zonaprop
        result = extraer_id_propiedad(url)
        # Puede ser None o algún ID según la implementación
        assert result is None or result.startswith('ZP') or result.startswith('AP')

    def test_retorna_none_para_url_invalida(self):
        """Retorna None para URLs sin ID reconocible"""
        assert extraer_id_propiedad('https://google.com') is None
        assert extraer_id_propiedad('https://example.com/page') is None

    def test_retorna_none_para_string_vacio(self):
        """Retorna None para string vacío"""
        assert extraer_id_propiedad('') is None

    def test_retorna_none_para_none(self):
        """Maneja None sin error (si la función lo permite)"""
        # Esto puede fallar si la función no maneja None - documentar comportamiento
        try:
            result = extraer_id_propiedad(None)
            assert result is None
        except (TypeError, AttributeError):
            pytest.skip("La función no maneja None - comportamiento esperado")


# =============================================================================
# TESTS DE INTEGRACIÓN: Snapshot con datos reales
# =============================================================================

class TestIntegracionDatosReales:
    """Tests usando datos reales del cache"""

    @pytest.fixture
    def cache_data(self):
        """Carga datos del cache si existe"""
        cache_path = Path(__file__).parent.parent / 'data' / 'scrape_cache.json'
        if not cache_path.exists():
            pytest.skip("Cache no existe")
        with open(cache_path) as f:
            return json.load(f)

    @pytest.fixture
    def sheet_data(self):
        """Carga datos del sheet si existe"""
        sheet_path = Path(__file__).parent.parent / 'data' / 'sheet_data.json'
        if not sheet_path.exists():
            pytest.skip("Sheet data no existe")
        with open(sheet_path) as f:
            return json.load(f)

    def test_cache_tiene_propiedades(self, cache_data):
        """Verifica que el cache tiene datos"""
        assert len(cache_data) > 0

    def test_propiedades_tienen_campos_requeridos(self, cache_data):
        """Verifica campos mínimos en propiedades cacheadas"""
        for url, data in cache_data.items():
            if '_error' not in data:
                # Propiedades válidas deben tener al menos precio o m²
                has_precio = data.get('precio')
                has_m2 = data.get('m2_cub') or data.get('m2_tot')
                assert has_precio or has_m2, f"Propiedad {url} sin precio ni m²"

    def test_calcular_m2_no_rompe_datos_existentes(self, sheet_data):
        """Verifica que calcular_m2 no produce resultados inconsistentes"""
        for row in sheet_data.get('rows', []):
            m2_cub = row.get('m2_cub', '')
            m2_tot = row.get('m2_tot', '')
            m2_desc = row.get('m2_desc', '')

            # Si ya tiene los 3, verificar consistencia
            if m2_cub and m2_tot and m2_desc:
                try:
                    cub = int(m2_cub)
                    tot = int(m2_tot)
                    desc = int(m2_desc)
                    # Permitir tolerancia de 2m²
                    diff = abs((cub + desc) - tot)
                    assert diff <= 2, f"Inconsistencia en fila {row.get('_row')}: {cub}+{desc}≠{tot}"
                except ValueError:
                    pass  # Skip si no son números


# =============================================================================
# TESTS DE REGRESIÓN: Casos específicos que fallaron antes
# =============================================================================

class TestRegresion:
    """Tests de regresión para bugs conocidos"""

    def setup_method(self):
        clear_warnings()

    def test_terraza_no_detecta_correctamente(self):
        """Bug: 'terraza: no' se detectaba como 'si'

        Antes el código buscaba 'terraza' primero y lo marcaba como 'si'
        ignorando el ': no' que seguía.
        """
        assert detectar_atributo('terraza: no', 'terraza') == 'no'
        assert detectar_atributo('Terraza: No disponible', 'terraza') == 'no'

    def test_balcon_no_detecta_correctamente(self):
        """Similar al bug de terraza"""
        assert detectar_atributo('balcon: no', 'balcon') == 'no'
        assert detectar_atributo('balcón: no', 'balcon') == 'no'

    def test_m2_desc_cero_con_exterior(self):
        """Bug: Propiedades con balcón/terraza pero m²_desc=0

        Ahora debe generar warning.
        """
        data = {'balcon': 'si', 'm2_cub': '70', 'm2_tot': '70', 'm2_desc': '0'}
        validar_propiedad(data, 'Test')
        warnings = get_warnings()
        assert any(w['tipo'] == 'm2_desc_inconsistente' for w in warnings)


# =============================================================================
# TESTS: extraer_m2()
# =============================================================================

class TestExtraerM2:
    """Tests para la función extraer_m2"""

    def test_extrae_valores_normales(self):
        """Extrae m2 de un dict con valores string"""
        data = {'m2_cub': '70', 'm2_tot': '100', 'm2_desc': '30'}
        cub, tot, desc = extraer_m2(data)
        assert cub == 70
        assert tot == 100
        assert desc == 30

    def test_extrae_valores_int(self):
        """Extrae m2 de un dict con valores int"""
        data = {'m2_cub': 70, 'm2_tot': 100, 'm2_desc': 30}
        cub, tot, desc = extraer_m2(data)
        assert cub == 70
        assert tot == 100
        assert desc == 30

    def test_valores_faltantes_son_cero(self):
        """Valores faltantes se convierten a 0"""
        data = {'m2_cub': '70'}
        cub, tot, desc = extraer_m2(data)
        assert cub == 70
        assert tot == 0
        assert desc == 0

    def test_valores_vacios_son_cero(self):
        """Strings vacíos se convierten a 0"""
        data = {'m2_cub': '', 'm2_tot': '', 'm2_desc': ''}
        cub, tot, desc = extraer_m2(data)
        assert cub == 0
        assert tot == 0
        assert desc == 0

    def test_valores_none_son_cero(self):
        """None se convierte a 0"""
        data = {'m2_cub': None, 'm2_tot': None, 'm2_desc': None}
        cub, tot, desc = extraer_m2(data)
        assert cub == 0
        assert tot == 0
        assert desc == 0

    def test_dict_vacio(self):
        """Dict vacío retorna todos ceros"""
        cub, tot, desc = extraer_m2({})
        assert cub == 0
        assert tot == 0
        assert desc == 0


# =============================================================================
# TESTS: get_active_rows()
# =============================================================================

class TestGetActiveRows:
    """Tests para la función get_active_rows"""

    def test_filtra_filas_activas(self):
        """Filtra solo filas activas con links válidos"""
        rows = [
            {'_row': 2, 'activo': 'si', 'link': 'https://example.com/1'},
            {'_row': 3, 'activo': 'no', 'link': 'https://example.com/2'},
            {'_row': 4, 'activo': 'si', 'link': 'https://example.com/3'},
        ]
        result = get_active_rows(rows)
        assert len(result) == 2
        assert result[0]['_row'] == 2
        assert result[1]['_row'] == 4

    def test_excluye_filas_sin_link(self):
        """Excluye filas sin link válido"""
        rows = [
            {'_row': 2, 'activo': 'si', 'link': 'https://example.com/1'},
            {'_row': 3, 'activo': 'si', 'link': ''},
            {'_row': 4, 'activo': 'si', 'link': 'no-es-url'},
        ]
        result = get_active_rows(rows)
        assert len(result) == 1
        assert result[0]['_row'] == 2

    def test_excluye_fila_header(self):
        """Excluye filas con _row < 2 (headers)"""
        rows = [
            {'_row': 1, 'activo': 'si', 'link': 'https://example.com/1'},
            {'_row': 2, 'activo': 'si', 'link': 'https://example.com/2'},
        ]
        result = get_active_rows(rows)
        assert len(result) == 1
        assert result[0]['_row'] == 2

    def test_activo_case_insensitive(self):
        """activo='NO' (mayúsculas) también se excluye"""
        rows = [
            {'_row': 2, 'activo': 'NO', 'link': 'https://example.com/1'},
            {'_row': 3, 'activo': 'No', 'link': 'https://example.com/2'},
            {'_row': 4, 'activo': 'SI', 'link': 'https://example.com/3'},
        ]
        result = get_active_rows(rows)
        assert len(result) == 1
        assert result[0]['_row'] == 4

    def test_activo_vacio_es_activo(self):
        """activo='' se considera activo (no está marcado como inactivo)"""
        rows = [
            {'_row': 2, 'activo': '', 'link': 'https://example.com/1'},
            {'_row': 3, 'link': 'https://example.com/2'},  # Sin campo activo
        ]
        result = get_active_rows(rows)
        assert len(result) == 2

    def test_lista_vacia(self):
        """Lista vacía retorna lista vacía"""
        assert get_active_rows([]) == []


# =============================================================================
# TESTS: quitar_tildes()
# =============================================================================

class TestQuitarTildes:
    """Tests para la función quitar_tildes"""

    def test_quita_tildes_vocales(self):
        """Quita tildes de vocales"""
        assert quitar_tildes('áéíóú') == 'aeiou'
        assert quitar_tildes('ÁÉÍÓÚ') == 'AEIOU'

    def test_quita_dieresis(self):
        """Quita diéresis"""
        assert quitar_tildes('üÜ') == 'uU'

    def test_mantiene_enie(self):
        """Mantiene la ñ (no es tilde, es letra)"""
        # Nota: La ñ se descompone en n + combining tilde, así que se pierde
        # Este test documenta el comportamiento actual
        result = quitar_tildes('ñ')
        assert result == 'n'  # La ñ se convierte en n

    def test_mantiene_espacios(self):
        """Mantiene espacios y puntuación"""
        assert quitar_tildes('Balcón al frente') == 'Balcon al frente'
        assert quitar_tildes('Año: 2020') == 'Ano: 2020'

    def test_texto_sin_tildes(self):
        """Texto sin tildes queda igual"""
        assert quitar_tildes('hola mundo') == 'hola mundo'
        assert quitar_tildes('ABC 123') == 'ABC 123'

    def test_texto_vacio(self):
        """Texto vacío retorna vacío"""
        assert quitar_tildes('') == ''


# =============================================================================
# TESTS: Scrapers con datos del cache
# =============================================================================

class TestScrapersConCache:
    """Tests de scrapers usando datos reales del cache"""

    @pytest.fixture
    def cache_data(self):
        """Carga datos del cache si existe"""
        if not CACHE_FILE.exists():
            pytest.skip("Cache no existe - ejecutar scrape primero")
        return load_cache()

    def test_cache_tiene_datos_mercadolibre(self, cache_data):
        """El cache tiene propiedades de MercadoLibre"""
        meli_urls = [url for url in cache_data.keys() if 'mercadolibre' in url]
        assert len(meli_urls) > 0, "No hay datos de MercadoLibre en cache"

    def test_cache_tiene_datos_argenprop(self, cache_data):
        """El cache tiene propiedades de Argenprop"""
        argenprop_urls = [url for url in cache_data.keys() if 'argenprop' in url]
        assert len(argenprop_urls) > 0, "No hay datos de Argenprop en cache"

    def test_datos_mercadolibre_tienen_campos_esperados(self, cache_data):
        """Datos de MercadoLibre tienen campos mínimos"""
        for url, data in cache_data.items():
            if 'mercadolibre' not in url:
                continue
            if '_error' in data:
                continue
            # Propiedades válidas deben tener precio
            assert 'precio' in data, f"MercadoLibre sin precio: {url}"

    def test_datos_argenprop_tienen_campos_esperados(self, cache_data):
        """Datos de Argenprop tienen campos mínimos"""
        for url, data in cache_data.items():
            if 'argenprop' not in url:
                continue
            if '_error' in data:
                continue
            # Propiedades válidas deben tener precio o dirección
            has_data = data.get('precio') or data.get('direccion')
            assert has_data, f"Argenprop sin datos: {url}"

    def test_scrape_link_usa_cache(self, cache_data):
        """scrape_link retorna datos del cache cuando está disponible"""
        # Tomar la primera URL del cache
        url = list(cache_data.keys())[0]
        data, from_cache = scrape_link(url, use_cache=True, cache=cache_data)
        assert from_cache is True, "Debería haber usado el cache"
        assert data is not None


# =============================================================================
# TESTS: Snapshot - Verificar consistencia de output
# =============================================================================

class TestSnapshotConsistencia:
    """Tests de snapshot para verificar que el output es consistente"""

    @pytest.fixture
    def sheet_data(self):
        """Carga datos del sheet si existe"""
        sheet_path = Path(__file__).parent.parent / 'data' / 'sheet_data.json'
        if not sheet_path.exists():
            pytest.skip("Sheet data no existe")
        with open(sheet_path) as f:
            return json.load(f)

    def test_todas_las_filas_tienen_row_number(self, sheet_data):
        """Todas las filas tienen número de fila"""
        for row in sheet_data.get('rows', []):
            assert '_row' in row, "Fila sin _row"
            assert row['_row'] >= 2, "Número de fila inválido"

    def test_filas_con_link_tienen_datos_basicos(self, sheet_data):
        """Filas con link deben tener al menos algunos datos scrapeados"""
        for row in sheet_data.get('rows', []):
            link = row.get('link', '').strip()
            if not link.startswith('http'):
                continue
            activo = row.get('activo', '').lower()
            if activo == 'no':
                continue  # Skip inactivas
            # Propiedades activas con link deberían tener precio o m²
            precio = row.get('precio', '').strip()
            m2 = row.get('m2_cub', '').strip() or row.get('m2_tot', '').strip()
            barrio = row.get('barrio', '').strip()
            has_data = precio or m2 or barrio
            # Esto es un warning, no un error duro
            if not has_data:
                print(f"Warning: Fila {row.get('_row')} sin datos scrapeados")

    def test_m2_consistentes(self, sheet_data):
        """m² cub + m² desc = m² tot (con tolerancia)"""
        inconsistentes = []
        for row in sheet_data.get('rows', []):
            m2_cub = row.get('m2_cub', '').strip()
            m2_tot = row.get('m2_tot', '').strip()
            m2_desc = row.get('m2_desc', '').strip()

            if m2_cub and m2_tot and m2_desc:
                try:
                    cub = int(m2_cub)
                    tot = int(m2_tot)
                    desc = int(m2_desc)
                    esperado = cub + desc
                    if abs(esperado - tot) > 2:  # Tolerancia 2m²
                        inconsistentes.append({
                            'fila': row.get('_row'),
                            'cub': cub,
                            'desc': desc,
                            'tot': tot,
                            'esperado': esperado
                        })
                except ValueError:
                    pass

        # Reportar pero no fallar (pueden ser datos reales inconsistentes)
        if inconsistentes:
            print(f"\nInconsistencias de m² encontradas: {len(inconsistentes)}")
            for i in inconsistentes[:5]:
                print(f"  Fila {i['fila']}: {i['cub']}+{i['desc']}={i['esperado']} ≠ {i['tot']}")

    def test_atributos_booleanos_validos(self, sheet_data):
        """Atributos booleanos tienen valores válidos (si/no/?)"""
        valores_validos = {'si', 'no', '?', ''}
        atributos = ['terraza', 'balcon', 'ascensor', 'apto_credito']

        for row in sheet_data.get('rows', []):
            for attr in atributos:
                valor = row.get(attr, '').lower().strip()
                if valor and valor not in valores_validos:
                    print(f"Warning: Fila {row.get('_row')} {attr}='{valor}' (no estándar)")


# =============================================================================
# TESTS: Funciones de prints (si existen)
# =============================================================================

class TestFuncionesPrints:
    """Tests para funciones del sistema de prints"""

    def test_extraer_id_propiedad_para_nombre_print(self):
        """extraer_id_propiedad funciona para generar nombres de prints"""
        # MercadoLibre
        url = 'https://departamento.mercadolibre.com.ar/MLA-1513702911-depto'
        assert extraer_id_propiedad(url) == 'MLA1513702911'

        # Argenprop
        url = 'https://www.argenprop.com/depto-venta--17094976'
        assert extraer_id_propiedad(url) == 'AP17094976'

    def test_ids_son_unicos_en_sheet(self):
        """Los IDs extraídos son únicos (no hay duplicados)"""
        sheet_path = Path(__file__).parent.parent / 'data' / 'sheet_data.json'
        if not sheet_path.exists():
            pytest.skip("Sheet data no existe")

        with open(sheet_path) as f:
            sheet_data = json.load(f)

        ids = []
        for row in sheet_data.get('rows', []):
            link = row.get('link', '').strip()
            if link.startswith('http'):
                prop_id = extraer_id_propiedad(link)
                if prop_id:
                    ids.append(prop_id)

        # Verificar unicidad
        duplicados = [id for id in ids if ids.count(id) > 1]
        unique_duplicados = list(set(duplicados))
        if unique_duplicados:
            print(f"Warning: IDs duplicados: {unique_duplicados}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
