"""
Tests de búsqueda de productos (TC-01A … TC-02C).
Feature: Búsqueda de Productos
Capas: UI + API
"""

import pytest
from playwright.sync_api import expect

from config import BASE_URL
from pages.products_page import ProductsPage

# ══════════════════════════════════════════════════════════════════════════════
# TC-01: Búsquedas exitosas (resultados > 0)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.busqueda
@pytest.mark.smoke
def test_tc01a_busqueda_nombre_exacto(page_products: ProductsPage, api_client: dict):
    """
    Escenario: Búsqueda exitosa por nombre exacto
    Esperado:  Se muestran productos con 'Pliers' en el nombre, status API 200 y el total UI coincide con la API
    Impacto:   Si falla, el usuario no puede encontrar productos por nombre exacto y el catálogo es inusable
    Accion:    Verificar que el endpoint GET /products?search= responde correctamente y el frontend actualiza el grid
    """
    # ── UI: ejecuta la búsqueda ────────────────────────────────────────────
    page_products.search("Pliers")

    # Verifica que se muestran resultados (al menos 1 tarjeta)
    expect(page_products.page.locator(ProductsPage.PRODUCT_CARDS).first).to_be_visible()

    # Verifica que todos los nombres visibles contienen 'pliers' (case-insensitive)
    names = page_products.get_product_names()
    assert len(names) > 0, "No se encontraron productos para 'Pliers'"
    for name in names:
        assert "plier" in name.lower(), (
            f"El producto '{name}' no contiene 'Pliers' en su nombre"
        )

    # ── API: usa el endpoint correcto de búsqueda /products/search?q= ────────
    resp_data = api_client["products"].search_products("Pliers")
    api_total = resp_data.get("total", 0)

    ui_total = page_products.get_result_total_from_ui()

    assert api_total > 0, "La API no retornó resultados para 'Pliers'"
    assert ui_total == api_total, (
        f"Total en UI ({ui_total}) no coincide con total en API ({api_total})"
    )


@pytest.mark.busqueda
def test_tc01b_busqueda_termino_parcial(page_products: ProductsPage, api_client: dict):
    """
    Escenario: Búsqueda exitosa por término parcial
    Esperado:  Se muestran productos cuyos nombres contienen 'Pli' y la API retorna los mismos
    Impacto:   Si falla, los usuarios que buscan con términos incompletos no obtienen resultados
    Accion:    Revisar la lógica de búsqueda parcial en backend y el filtrado en frontend
    """
    # ── UI: búsqueda con término parcial ──────────────────────────────────
    page_products.search("Pli")

    expect(page_products.page.locator(ProductsPage.PRODUCT_CARDS).first).to_be_visible()

    names_ui = page_products.get_product_names()
    assert len(names_ui) > 0, "No se encontraron resultados para el término parcial 'Pli'"

    # Todos los nombres deben contener 'pli' (fragmento de 'pliers')
    for name in names_ui:
        assert "pli" in name.lower(), (
            f"El producto '{name}' no contiene el término parcial 'Pli'"
        )

    # ── API: misma búsqueda usando el endpoint correcto /products/search?q= ─
    resp_data = api_client["products"].search_products("Pli")
    names_api = [p["name"] for p in resp_data.get("data", [])]

    assert sorted(names_ui) == sorted(names_api), (
        f"Los nombres en UI {names_ui} no coinciden con los de la API {names_api}"
    )


@pytest.mark.busqueda
def test_tc01c_busqueda_case_insensitive(page_products: ProductsPage, api_client: dict):
    """
    Escenario: Búsqueda case-insensitive
    Esperado:  Buscar 'PLIERS' en mayúsculas retorna los mismos 4 resultados que 'Pliers'
    Impacto:   Si falla, usuarios que escriben en mayúsculas no obtienen resultados correctos
    Accion:    Verificar que el backend normaliza la búsqueda a minúsculas antes de filtrar
    """
    # ── Búsqueda en minúscula como referencia ──────────────────────────────
    page_products.search("Pliers")
    names_lower = sorted(page_products.get_product_names())
    count_lower = len(names_lower)

    # ── Misma búsqueda en mayúscula ────────────────────────────────────────
    page_products.search("PLIERS")
    names_upper = sorted(page_products.get_product_names())
    count_upper = len(names_upper)

    assert count_upper == count_lower, (
        f"'PLIERS' retornó {count_upper} resultados pero 'Pliers' retornó {count_lower}"
    )
    assert names_upper == names_lower, (
        "Los resultados difieren entre búsqueda en mayúsculas y minúsculas"
    )

    # ── API: confirma que ambas búsquedas devuelven el mismo total ─────────
    api_lower = api_client["products"].search_products("Pliers").get("total", 0)
    api_upper = api_client["products"].search_products("PLIERS").get("total", 0)
    assert api_lower == api_upper, (
        f"La API retorna {api_lower} para 'Pliers' pero {api_upper} para 'PLIERS'"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TC-02: Búsquedas negativas (0 resultados / sin acción)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.busqueda
@pytest.mark.negativo
def test_tc02a_busqueda_termino_inexistente(page_products: ProductsPage, api_client: dict):
    """
    Escenario: Búsqueda sin resultados – término inexistente
    Esperado:  Se muestra mensaje de 'sin resultados' y el contador indica 0; la API retorna 'data' vacío
    Impacto:   Si falla, el usuario ve un grid vacío sin feedback claro sobre la ausencia de resultados
    Accion:    Verificar que el componente de resultados muestra el mensaje vacío cuando 'data' es []
    """
    # ── UI: busca un término que no existe ────────────────────────────────
    page_products.search("xyzabc123")

    # El mensaje de 'sin resultados' debe aparecer
    assert page_products.no_results_message_visible(), (
        "No se muestra el mensaje de 'sin resultados' para un término inexistente"
    )

    # El contador debe mostrar 0
    ui_total = page_products.get_result_total_from_ui()
    assert ui_total == 0, f"El contador muestra {ui_total} pero debería ser 0"

    # ── API: el endpoint de búsqueda no debe retornar resultados ─────────────
    resp_data = api_client["products"].search_products("xyzabc123")
    api_data = resp_data.get("data", [])
    assert api_data == [], (
        f"La API devolvió productos para un término inexistente: {api_data}"
    )


@pytest.mark.busqueda
@pytest.mark.negativo
def test_tc02b_busqueda_campo_vacio(page_products: ProductsPage):
    """
    Escenario: Búsqueda con campo vacío no ejecuta búsqueda
    Esperado:  No ocurre ninguna acción visible; los productos originales permanecen sin cambios
    Impacto:   Si falla, el usuario podría ver un estado inconsistente del catálogo al dejar el campo vacío
    Accion:    Verificar que el botón 'Search' no dispara la llamada API cuando el campo está vacío
    """
    # ── Captura la cantidad inicial de productos ───────────────────────────
    initial_count = page_products.get_product_count()
    assert initial_count > 0, "El catálogo debería mostrar productos por defecto"

    # ── Intenta buscar con campo vacío ────────────────────────────────────
    page_products.page.fill(ProductsPage.SEARCH_INPUT, "")
    page_products.page.click(ProductsPage.SEARCH_BUTTON)
    page_products.page.wait_for_timeout(2_000)

    # Los productos originales deben permanecer y no aparecer mensaje de 'sin resultados'
    final_count = page_products.get_product_count()
    assert final_count == initial_count, (
        f"La búsqueda vacía cambió el número de productos: {initial_count} → {final_count}"
    )
    assert not page_products.no_results_message_visible(), (
        "Se muestra mensaje de 'sin resultados' para búsqueda vacía, no debería"
    )


@pytest.mark.busqueda
@pytest.mark.negativo
def test_tc02c_busqueda_solo_espacios(page_products: ProductsPage, api_client: dict):
    """
    Escenario: Búsqueda con solo espacios muestra 0 resultados
    Esperado:  Se muestra el mensaje de 'sin resultados' y el contador indica 0 para ' '
    Impacto:   Si falla, búsquedas con espacios podrían retornar todos los productos o causar error
    Accion:    Verificar que el backend trata la búsqueda de espacios como término vacío sin resultados
    """
    # ── UI: busca con espacios en blanco ──────────────────────────────────
    page_products.search("   ")

    # Debe aparecer el mensaje de 'sin resultados' O el contador debe ser 0
    ui_total = page_products.get_result_total_from_ui()
    no_results = page_products.no_results_message_visible()

    assert no_results or ui_total == 0, (
        f"La búsqueda con espacios retornó {ui_total} resultados sin mensaje de 'sin resultados'"
    )
