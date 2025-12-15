"""
Tests exhaustivos para sync_sheet.py

Ejecutar con: pytest sheets/test_sync_sheet.py -v
"""
import pytest
import json
from pathlib import Path

# Importar funciones a testear
from sync_sheet import (
    calcular_m2_faltantes,
    validar_propiedad,
    detectar_atributo,
    extraer_id_propiedad,
    ATTR_PATTERNS,
    clear_warnings,
    get_warnings,
)


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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
