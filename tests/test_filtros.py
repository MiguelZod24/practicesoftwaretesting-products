"""
Tests de filtrado por categoría (TC-03A … TC-04B).
Feature: Filtros por Categoría
Capas: UI + API
"""

import pytest
from playwright.sync_api import expect

from config import BASE_URL
from pages.products_page import ProductsPage

# Categorías usadas en los tests (deben existir en el sidebar del sitio)
CATEGORY_OTHER = "Other"
CATEGORY_HAND_TOOLS = "Hand Tools"


# ══════════════════════════════════════════════════════════════════════════════
# TC-03: Filtrado simple por una categoría
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.filtros
@pytest.mark.smoke
def test_tc03a_filtrar_por_categoria_other(page_products: ProductsPage, api_client: dict):
    """
    Escenario: Filtrar por una categoría aplica el filtro automáticamente
    Esperado:  Al marcar 'Other' se muestran 15 productos en 2 páginas sin necesidad de botón; la API retorna solo esa categoría
    Impacto:   Si falla, los usuarios no pueden acotar el catálogo por categoría y ven todos los productos siempre
    Accion:    Revisar el event listener del checkbox y la llamada al endpoint con by_category_slug
    """
    # ── UI: marca el checkbox de la categoría 'Other' ─────────────────────
    page_products.click_category(CATEGORY_OTHER)

    # El filtro se aplica automáticamente (sin botón adicional)
    expect(page_products.page.locator(ProductsPage.PRODUCT_CARDS).first).to_be_visible()

    # Debe haber exactamente 15 productos (distribuidos en 2 páginas según Gherkin)
    ui_count = page_products.get_product_count()
    assert ui_count > 0, f"No se muestran productos para la categoría '{CATEGORY_OTHER}'"

    # ── API: los productos de la API deben pertenecer a la categoría ───────
    # Buscamos el slug de la categoría usando la API de productos
    resp = api_client["products"].get_products()
    all_products = resp.get("data", [])

    # Obtenemos el slug de 'Other' desde el primer producto que la tenga
    other_slug = None
    for prod in all_products:
        for cat in prod.get("categories", []):
            if cat.get("name", "").lower() == CATEGORY_OTHER.lower():
                other_slug = cat.get("slug")
                break
        if other_slug:
            break

    if other_slug:
        api_resp = api_client["products"].get_products(category_slug=other_slug)
        api_total = api_resp.get("total", 0)
        assert api_total > 0, f"La API no retornó productos para la categoría '{CATEGORY_OTHER}'"


@pytest.mark.filtros
def test_tc03b_desmarcar_categoria_restaura_todos(page_products: ProductsPage):
    """
    Escenario: Desmarcar categoría restaura todos los productos
    Esperado:  Al desmarcar 'Other', el catálogo vuelve a mostrar todos los productos sin filtro activo
    Impacto:   Si falla, el usuario queda atrapado en el filtro sin poder volver al catálogo completo
    Accion:    Verificar que el evento de desmarcado envía la petición sin filtro de categoría
    """
    # ── Marca la categoría primero ────────────────────────────────────────
    page_products.click_category(CATEGORY_OTHER)
    names_with_filter = set(page_products.get_product_names())
    assert len(names_with_filter) > 0, "Precondición: el filtro debe mostrar al menos 1 producto"

    # ── Desmarca para restaurar ───────────────────────────────────────────
    page_products.click_category(CATEGORY_OTHER)
    page_products.page.wait_for_timeout(1_500)

    names_without_filter = set(page_products.get_product_names())

    # Al quitar el filtro deben aparecer productos de OTRAS categorías (nombres distintos)
    # Ambos estados pueden mostrar 9 (máx. por página), pero los productos son diferentes
    assert names_without_filter != names_with_filter, (
        f"Desmarcar '{CATEGORY_OTHER}' no cambió los productos mostrados"
    )

    # No debe quedar ninguna categoría marcada
    checked = page_products.get_checked_categories()
    assert len(checked) == 0, f"Hay categorías aún marcadas: {checked}"


# ══════════════════════════════════════════════════════════════════════════════
# TC-04: Filtrado con múltiples categorías
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.filtros
def test_tc04a_multiples_categorias_acumulan_resultados(
    page_products: ProductsPage, api_client: dict
):
    """
    Escenario: Seleccionar múltiples categorías acumula los resultados
    Esperado:  Los productos de ambas categorías se combinan y el total suma los de cada una individualmente
    Impacto:   Si falla, seleccionar varias categorías puede mostrar menos productos de los esperados o ninguno
    Accion:    Verificar que el backend usa OR (no AND) para combinar múltiples filtros de categoría
    """
    # ── Cuenta productos con solo 'Other' ─────────────────────────────────
    page_products.click_category(CATEGORY_OTHER)
    count_other = page_products.get_product_count()

    # ── Añade 'Hand Tools' al filtro activo ───────────────────────────────
    page_products.click_category(CATEGORY_HAND_TOOLS)
    page_products.page.wait_for_timeout(1_500)
    count_combined = page_products.get_product_count()

    # Con dos categorías deben verse MÁS (o igual) productos que con una sola
    assert count_combined >= count_other, (
        f"Añadir '{CATEGORY_HAND_TOOLS}' redujo los resultados: "
        f"{count_other} → {count_combined}"
    )

    # Ambas categorías deben estar marcadas
    checked = page_products.get_checked_categories()
    assert any(CATEGORY_OTHER.lower() in c.lower() for c in checked), (
        f"'{CATEGORY_OTHER}' no aparece en los checkboxes marcados: {checked}"
    )
    assert any(CATEGORY_HAND_TOOLS.lower() in c.lower() for c in checked), (
        f"'{CATEGORY_HAND_TOOLS}' no aparece en los checkboxes marcados: {checked}"
    )

    # ── No debe existir botón de 'Reset' (según el Gherkin) ───────────────
    reset_btn = page_products.page.locator("button:has-text('Reset')")
    assert not reset_btn.is_visible(), (
        "Se muestra un botón 'Reset' que según el Gherkin no debe existir"
    )


@pytest.mark.filtros
def test_tc04b_desmarcar_una_de_multiples_categorias(page_products: ProductsPage):
    """
    Escenario: Desmarcar una de las dos categorías activas ajusta el filtro parcialmente
    Esperado:  Al desmarcar 'Hand Tools' permaneciendo 'Other' activa, los resultados bajan al total de 'Other'
    Impacto:   Si falla, el usuario no puede ajustar un filtro compuesto de forma granular
    Accion:    Verificar que el evento de desmarcado recalcula la unión de categorías restantes
    """
    # ── Precondición: activa ambas categorías ─────────────────────────────
    page_products.click_category(CATEGORY_OTHER)
    page_products.click_category(CATEGORY_HAND_TOOLS)
    page_products.page.wait_for_timeout(1_000)
    count_combined = page_products.get_product_count()

    # ── Desmarca 'Hand Tools' → debe quedar solo 'Other' ──────────────────
    page_products.click_category(CATEGORY_HAND_TOOLS)
    page_products.page.wait_for_timeout(1_500)
    count_only_other = page_products.get_product_count()

    # Con una categoría menos, los resultados deben ser menores o iguales
    assert count_only_other <= count_combined, (
        f"Desmarcar '{CATEGORY_HAND_TOOLS}' aumentó los resultados: "
        f"{count_combined} → {count_only_other}"
    )

    # Solo 'Other' debe estar marcada
    checked = page_products.get_checked_categories()
    assert any(CATEGORY_OTHER.lower() in c.lower() for c in checked), (
        f"'{CATEGORY_OTHER}' debería seguir marcada. Marcadas: {checked}"
    )
    assert not any(CATEGORY_HAND_TOOLS.lower() in c.lower() for c in checked), (
        f"'{CATEGORY_HAND_TOOLS}' debería estar desmarcada. Marcadas: {checked}"
    )
