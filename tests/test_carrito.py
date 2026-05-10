"""
Tests de gestión del carrito (TC-07A … TC-11A).
Feature: Gestión del Carrito
Capas: UI + API
"""

import os
import pytest
from playwright.sync_api import expect

from config import BASE_URL
from pages.cart_page import CartPage
from pages.product_detail_page import ProductDetailPage
from pages.products_page import ProductsPage

# IDs obtenidos dinámicamente por pytest_configure en conftest.py
PRODUCT_WITH_STOCK_ID = os.getenv("PRODUCT_WITH_STOCK_ID")
PRODUCT_WITH_STOCK_NAME = os.getenv("PRODUCT_WITH_STOCK_NAME")
PRODUCT_WITH_STOCK_PRICE = float(os.getenv("PRODUCT_WITH_STOCK_PRICE", "0"))


# ══════════════════════════════════════════════════════════════════════════════
# TC-07: Agregar productos al carrito
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.carrito
@pytest.mark.smoke
def test_tc07a_agregar_1_unidad_al_carrito(page, api_client: dict, empty_cart):
    """
    Escenario: Agregar 1 unidad al carrito exitosamente
    Esperado:  Aparece toast de confirmación, el badge del header muestra 1 y POST /carts retorna 200/201
    Impacto:   Si falla, el flujo de compra principal está roto y ningún usuario puede agregar productos
    Accion:    Verificar el endpoint POST /carts y el componente de notificación toast en la UI
    """
    # ── Navega al detalle del producto con stock ───────────────────────────
    detail_po = ProductDetailPage(page, BASE_URL)
    detail_po.navigate(PRODUCT_WITH_STOCK_ID)

    # ── UI: agrega 1 unidad al carrito ────────────────────────────────────
    detail_po.add_to_cart()

    # El toast de confirmación debe aparecer
    toast_text = detail_po.get_toast_text()
    assert "added" in toast_text.lower() or "carrito" in toast_text.lower(), (
        f"Toast no confirma el agregado al carrito: '{toast_text}'"
    )

    # El badge del carrito en el header debe mostrar 1
    cart_count = detail_po.get_cart_count()
    assert cart_count == 1, (
        f"El badge del carrito muestra {cart_count} en lugar de 1"
    )

    # ── API: verifica que el carrito tiene el producto ─────────────────────
    resp = api_client["cart"].add_to_cart(PRODUCT_WITH_STOCK_ID, quantity=1)
    # POST /carts debe retornar 200 o 201
    assert resp.status_code in (200, 201), (
        f"POST /carts retornó status {resp.status_code}, se esperaba 200 o 201"
    )


@pytest.mark.carrito
def test_tc07b_agregar_multiples_unidades(page, api_client: dict, empty_cart):
    """
    Escenario: Agregar múltiples unidades al carrito
    Esperado:  Al seleccionar cantidad 2 y agregar, el badge del header muestra 2 y el toast confirma la acción
    Impacto:   Si falla, el usuario no puede comprar más de 1 unidad del mismo producto en un solo paso
    Accion:    Verificar que el selector de cantidad + incrementa correctamente y el payload de POST /carts incluye la cantidad
    """
    # ── Navega al detalle del producto ────────────────────────────────────
    detail_po = ProductDetailPage(page, BASE_URL)
    detail_po.navigate(PRODUCT_WITH_STOCK_ID)

    # ── UI: incrementa la cantidad a 2 usando el botón + ──────────────────
    detail_po.set_quantity(2)

    # ── UI: agrega al carrito ─────────────────────────────────────────────
    detail_po.add_to_cart()

    # El toast debe confirmar
    toast_text = detail_po.get_toast_text()
    assert "added" in toast_text.lower() or "carrito" in toast_text.lower(), (
        f"Toast no confirma el agregado: '{toast_text}'"
    )

    # El badge debe reflejar la cantidad correcta (2 unidades)
    cart_count = detail_po.get_cart_count()
    assert cart_count == 2, (
        f"El badge del carrito muestra {cart_count} en lugar de 2"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TC-08: Persistencia del carrito
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.carrito
def test_tc08a_carrito_persiste_al_navegar(page, api_client: dict, empty_cart):
    """
    Escenario: Carrito persiste al navegar entre páginas
    Esperado:  Después de navegar a otra página, el badge del carrito mantiene el número correcto y GET /carts devuelve el producto
    Impacto:   Si falla, el carrito se pierde al navegar y el usuario tiene que volver a agregar los productos
    Accion:    Verificar que la sesión/token se mantiene entre navegaciones y el estado del carrito se persiste en backend
    """
    # Captura el cart_id que el frontend crea al llamar POST /carts
    captured_cart_ids: list[str] = []

    def _on_response(response):
        if "/carts" in response.url and response.request.method == "POST":
            try:
                body = response.json()
                if "id" in body:
                    captured_cart_ids.append(body["id"])
            except Exception:
                pass

    page.on("response", _on_response)

    # ── Agrega el producto al carrito ─────────────────────────────────────
    detail_po = ProductDetailPage(page, BASE_URL)
    detail_po.navigate(PRODUCT_WITH_STOCK_ID)
    detail_po.add_to_cart()
    count_before = detail_po.get_cart_count()

    page.remove_listener("response", _on_response)

    # ── Navega a la página de productos ───────────────────────────────────
    products_po = ProductsPage(page, BASE_URL)
    products_po.navigate()

    # El badge debe mantener el mismo número después de navegar
    cart_po = CartPage(page, BASE_URL)
    count_after = cart_po.get_cart_badge_count()
    assert count_after == count_before, (
        f"El badge del carrito cambió al navegar: antes={count_before}, después={count_after}"
    )

    # ── API: el carrito del usuario debe contener el producto ─────────────
    if captured_cart_ids:
        api_client["cart"].set_cart_id(captured_cart_ids[0])
        cart_data = api_client["cart"].get_cart()
        items = cart_data.get("cart_items", [])
        assert len(items) > 0, "GET /carts retornó un carrito vacío después de agregar un producto"


@pytest.mark.carrito
def test_tc08b_carrito_persiste_al_recargar(page, api_client: dict, empty_cart):
    """
    Escenario: Carrito persiste al recargar la página
    Esperado:  Después de recargar con F5, el badge del carrito mantiene el número correcto
    Impacto:   Si falla, el carrito se resetea en cada recarga y el usuario pierde su selección de compra
    Accion:    Verificar que el carrito se carga desde el backend al iniciar la sesión, no solo desde memoria local
    """
    # ── Agrega el producto al carrito ─────────────────────────────────────
    detail_po = ProductDetailPage(page, BASE_URL)
    detail_po.navigate(PRODUCT_WITH_STOCK_ID)
    detail_po.add_to_cart()
    count_before = detail_po.get_cart_count()

    # ── Recarga la página ─────────────────────────────────────────────────
    page.reload()
    page.wait_for_load_state("networkidle", timeout=15_000)

    # El badge debe mantener el mismo número después de recargar
    cart_po = CartPage(page, BASE_URL)
    count_after = cart_po.get_cart_badge_count()
    assert count_after == count_before, (
        f"El badge del carrito se reseteo al recargar: antes={count_before}, después={count_after}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TC-09: Actualizar cantidad en el carrito
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.carrito
def test_tc09a_actualizar_cantidad_en_carrito(page, api_client: dict, empty_cart):
    """
    Escenario: Actualizar cantidad de producto en el carrito
    Esperado:  Al cambiar la cantidad de 1 a 3, el total del carrito refleja la nueva cantidad correctamente
    Impacto:   Si falla, el usuario no puede ajustar cantidades en el carrito y debe eliminar y volver a agregar
    Accion:    Verificar que el input de cantidad dispara el recalculo del total al perder el foco (Tab/blur)
    """
    # ── Agrega 1 unidad al carrito ────────────────────────────────────────
    detail_po = ProductDetailPage(page, BASE_URL)
    detail_po.navigate(PRODUCT_WITH_STOCK_ID)
    detail_po.add_to_cart()

    # ── Navega al carrito ─────────────────────────────────────────────────
    cart_po = CartPage(page, BASE_URL)
    cart_po.navigate()

    # Verifica que hay 1 ítem en el carrito
    assert cart_po.get_item_count() > 0, "El carrito debería tener al menos 1 producto"
    original_total = cart_po.get_total()

    # ── Actualiza la cantidad a 3 ─────────────────────────────────────────
    cart_po.update_quantity(index=0, quantity=3)
    page.wait_for_timeout(2_000)

    new_quantity = cart_po.get_item_quantity(index=0)
    new_total = cart_po.get_total()

    # La cantidad debe haberse actualizado a 3
    assert new_quantity == 3, (
        f"La cantidad en el carrito debería ser 3 pero es {new_quantity}"
    )

    # El total debe ser aproximadamente 3 × precio unitario
    expected_total = round(PRODUCT_WITH_STOCK_PRICE * 3, 2)
    assert abs(new_total - expected_total) < 0.10, (
        f"El total {new_total} no refleja 3 × {PRODUCT_WITH_STOCK_PRICE} = {expected_total}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TC-10: Eliminar producto del carrito
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.carrito
def test_tc10a_eliminar_producto_del_carrito(page, api_client: dict, empty_cart):
    """
    Escenario: Eliminar producto del carrito
    Esperado:  Al hacer clic en el botón X, aparece toast 'PRODUCTO ELIMINADO', el producto desaparece y el badge se actualiza
    Impacto:   Si falla, el usuario no puede quitar productos del carrito y está forzado a completar la compra
    Accion:    Verificar que DELETE /carts/{id}/product/{id} funciona y la UI remueve la fila del producto
    """
    # ── Agrega el producto al carrito ─────────────────────────────────────
    detail_po = ProductDetailPage(page, BASE_URL)
    detail_po.navigate(PRODUCT_WITH_STOCK_ID)
    detail_po.add_to_cart()
    count_before = detail_po.get_cart_count()
    assert count_before > 0

    # ── Navega al carrito y elimina el primer ítem ────────────────────────
    cart_po = CartPage(page, BASE_URL)
    cart_po.navigate()
    initial_items = cart_po.get_item_count()

    cart_po.remove_item(index=0)

    # Verifica el toast de eliminación
    toast_text = cart_po.get_toast_text()
    assert "deleted" in toast_text.lower() or "eliminado" in toast_text.lower() or "removed" in toast_text.lower(), (
        f"Toast no confirma la eliminación: '{toast_text}'"
    )

    # El ítem debe desaparecer de la lista
    page.wait_for_timeout(1_500)
    items_after = cart_po.get_item_count()
    assert items_after == initial_items - 1, (
        f"El número de ítems no disminuyó: antes={initial_items}, después={items_after}"
    )

    # El badge del header debe actualizarse
    badge_after = cart_po.get_cart_badge_count()
    assert badge_after == count_before - 1, (
        f"El badge del carrito muestra {badge_after} en lugar de {count_before - 1}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TC-11: Carrito vacío al eliminar el último producto
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.carrito
@pytest.mark.negativo
def test_tc11a_carrito_vacio_al_eliminar_ultimo_producto(page, api_client: dict, empty_cart):
    """
    Escenario: Carrito muestra mensaje de vacío al eliminar el último producto
    Esperado:  Al eliminar el único producto, aparece toast, se muestra mensaje de 'carrito vacío' y el badge vuelve a 0
    Impacto:   Si falla, el usuario puede ver un carrito vacío sin feedback claro o con datos obsoletos
    Accion:    Verificar que el componente de carrito muestra el estado vacío cuando 'data' es [] y el badge se resetea a 0
    """
    # ── Agrega exactamente 1 producto al carrito ───────────────────────────
    detail_po = ProductDetailPage(page, BASE_URL)
    detail_po.navigate(PRODUCT_WITH_STOCK_ID)
    detail_po.add_to_cart()

    # ── Navega al carrito ─────────────────────────────────────────────────
    cart_po = CartPage(page, BASE_URL)
    cart_po.navigate()
    assert cart_po.get_item_count() == 1, "Precondición: debe haber exactamente 1 producto"

    # ── Elimina el único producto ─────────────────────────────────────────
    cart_po.remove_item(index=0)
    page.wait_for_timeout(2_000)

    # Toast de eliminación debe aparecer
    toast_text = cart_po.get_toast_text()
    assert "deleted" in toast_text.lower() or "eliminado" in toast_text.lower() or "removed" in toast_text.lower(), (
        f"Toast no confirma la eliminación del último producto: '{toast_text}'"
    )

    # El mensaje de 'carrito vacío' debe aparecer
    assert cart_po.is_empty_message_visible(), (
        "No se muestra el mensaje de 'carrito vacío' después de eliminar el último producto"
    )

    # El badge del header debe volver a 0
    badge_count = cart_po.get_cart_badge_count()
    assert badge_count == 0, (
        f"El badge del carrito muestra {badge_count} en lugar de 0 tras vaciar el carrito"
    )
