"""
Tests de página de detalle de producto (TC-05A … TC-06B).
Feature: Detalle de Producto
Capas: UI + API
"""

import os
import pytest
from playwright.sync_api import expect

from config import BASE_URL
from pages.product_detail_page import ProductDetailPage
from pages.products_page import ProductsPage

# IDs obtenidos dinámicamente por pytest_configure en conftest.py
PRODUCT_WITH_STOCK_ID = os.getenv("PRODUCT_WITH_STOCK_ID")
PRODUCT_WITH_STOCK_NAME = os.getenv("PRODUCT_WITH_STOCK_NAME")
PRODUCT_WITH_STOCK_PRICE = float(os.getenv("PRODUCT_WITH_STOCK_PRICE", "0"))
PRODUCT_OUT_OF_STOCK_ID = os.getenv("PRODUCT_OUT_OF_STOCK_ID")
PRODUCT_OUT_OF_STOCK_NAME = os.getenv("PRODUCT_OUT_OF_STOCK_NAME")


# ══════════════════════════════════════════════════════════════════════════════
# TC-05: Consistencia UI ↔ API en datos del producto
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.detalle
@pytest.mark.smoke
def test_tc05a_detalle_coincide_con_api(page, api_client: dict):
    """
    Escenario: Detalle de producto coincide con datos de la API
    Esperado:  El nombre y precio mostrados en UI coinciden con 'name' y 'price' de GET /products/{id}; status 200
    Impacto:   Si falla, el cliente puede ver datos incorrectos del producto y tomar decisiones de compra erróneas
    Accion:    Revisar el mapeo de la respuesta API al componente de detalle y verificar el endpoint de producto
    """
    # ── Navega a la página de productos y hace clic en el primero ─────────
    products_po = ProductsPage(page, BASE_URL)
    products_po.navigate()
    product_url = products_po.click_product(index=0)

    # Extrae el ID del producto desde la URL resultante
    product_id = product_url.rstrip("/").split("/")[-1]

    # ── UI: lee nombre y precio del Page Object ────────────────────────────
    detail_po = ProductDetailPage(page, BASE_URL)
    ui_name = detail_po.get_name()
    ui_price = detail_po.get_price()

    # ── API: GET /products/{id} ────────────────────────────────────────────
    api_data = api_client["products"].get_product(product_id)

    api_name = api_data.get("name", "")
    api_price = float(api_data.get("price", 0))

    # Compara nombre (exacto)
    assert ui_name == api_name, (
        f"Nombre en UI '{ui_name}' no coincide con API '{api_name}'"
    )

    # Compara precio con tolerancia de ±0.01 por redondeo de pantalla
    assert abs(ui_price - api_price) < 0.02, (
        f"Precio en UI {ui_price} no coincide con API {api_price}"
    )


@pytest.mark.detalle
def test_tc05b_categorias_coinciden_entre_ui_y_api(page, api_client: dict):
    """
    Escenario: Categorías del producto coinciden entre UI y API
    Esperado:  Los tags de categoría visibles en la UI coinciden con el campo 'categories' de GET /products/{id}
    Impacto:   Si falla, el usuario ve etiquetas de categoría incorrectas que confunden la navegación del catálogo
    Accion:    Verificar que el componente de detalle muestra todas las categorías devueltas por la API
    """
    # ── Navega directamente al producto de referencia con stock ───────────
    detail_po = ProductDetailPage(page, BASE_URL)
    detail_po.navigate(PRODUCT_WITH_STOCK_ID)

    # ── UI: obtiene los tags de categoría ────────────────────────────────
    ui_categories = [c.lower() for c in detail_po.get_categories()]

    # ── API: obtiene las categorías del endpoint ──────────────────────────
    api_data = api_client["products"].get_product(PRODUCT_WITH_STOCK_ID)
    api_categories = [
        cat.get("name", "").lower()
        for cat in api_data.get("categories", [])
    ]

    assert sorted(ui_categories) == sorted(api_categories), (
        f"Categorías en UI {ui_categories} no coinciden con API {api_categories}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TC-06: Estado del botón 'Añadir al carrito' según stock
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.detalle
@pytest.mark.smoke
def test_tc06a_boton_habilitado_con_stock(page, api_client: dict):
    """
    Escenario: Botón 'Añadir al carrito' habilitado para producto con stock
    Esperado:  El botón es visible y está habilitado; el selector de cantidad + está activo
    Impacto:   Si falla, el usuario no puede agregar al carrito un producto que sí tiene stock
    Accion:    Verificar que la propiedad 'is_location_allowed' / 'in_stock' de la API es true y el botón refleja ese estado
    """
    # ── Verifica en API que el producto tiene stock ────────────────────────
    api_data = api_client["products"].get_product(PRODUCT_WITH_STOCK_ID)
    assert api_data.get("is_location_allowed") or api_data.get("in_stock", True), (
        f"La API indica que '{PRODUCT_WITH_STOCK_NAME}' no tiene stock disponible"
    )

    # ── Navega al detalle del producto con stock ───────────────────────────
    detail_po = ProductDetailPage(page, BASE_URL)
    detail_po.navigate(PRODUCT_WITH_STOCK_ID)

    # El botón debe ser visible y estar habilitado
    add_btn = page.locator(ProductDetailPage.ADD_TO_CART_BTN)
    expect(add_btn).to_be_visible()
    expect(add_btn).to_be_enabled()

    # El selector de cantidad + también debe estar activo
    increase_btn = page.locator(ProductDetailPage.QUANTITY_INCREASE)
    expect(increase_btn).to_be_visible()
    expect(increase_btn).to_be_enabled()

    # La etiqueta de agotado NO debe aparecer
    assert not detail_po.is_out_of_stock_shown(), (
        "Se muestra la etiqueta 'out of stock' para un producto que tiene stock"
    )


@pytest.mark.detalle
@pytest.mark.negativo
def test_tc06b_boton_deshabilitado_sin_stock(page, api_client: dict):
    """
    Escenario: Botón 'Añadir al carrito' deshabilitado para producto agotado
    Esperado:  Se muestra la etiqueta 'Out of stock' y el botón está deshabilitado
    Impacto:   Si falla, el usuario puede intentar comprar un producto sin stock y generará errores en el pedido
    Accion:    Verificar que la UI respeta el campo 'in_stock' de la API para deshabilitar el botón correctamente
    """
    # ── Navega al producto sin stock ──────────────────────────────────────
    detail_po = ProductDetailPage(page, BASE_URL)
    detail_po.navigate(PRODUCT_OUT_OF_STOCK_ID)

    # La etiqueta de agotado debe ser visible
    out_of_stock = page.locator(ProductDetailPage.OUT_OF_STOCK_LABEL)
    expect(out_of_stock).to_be_visible()

    # El botón 'Add to cart' debe estar deshabilitado
    add_btn = page.locator(ProductDetailPage.ADD_TO_CART_BTN)
    expect(add_btn).to_be_disabled()
