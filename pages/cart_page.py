from playwright.sync_api import Page

from utils import parse_price


class CartPage:
    """Page Object para la página del carrito (/checkout)."""

    # ── Locators ─────────────────────────────────────────────────────────────

    # Ícono del carrito en el header (aparece después de agregar un item)
    CART_ICON = '[data-test="nav-cart"]'
    # Badge con el número de ítems en el header
    CART_QUANTITY_BADGE = '[data-test="cart-quantity"]'
    # Cada fila de producto en la tabla del carrito (checkout)
    CART_ITEMS = 'table.table tbody tr:has([data-test="product-title"])'
    # Nombre del producto dentro de una fila
    CART_ITEM_NAME = '[data-test="product-title"]'
    # Input de cantidad editable por fila
    CART_ITEM_QUANTITY = '[data-test="product-quantity"]'
    # Precio unitario por línea
    CART_ITEM_PRICE = '[data-test="product-price"]'
    # Botón rojo X para eliminar un ítem (sin data-test en la v5)
    CART_ITEM_REMOVE = 'a.btn-danger'
    # Total general del carrito
    CART_TOTAL = '[data-test="cart-total"]'
    # Mensaje que se muestra cuando el carrito está vacío (texto en <p>)
    EMPTY_CART_MSG = 'p:has-text("vacío"), p:has-text("empty")'
    # Notificación / toast de confirmación (usa role=alert en la v5)
    TOAST_MESSAGE = '[role="alert"]'

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    # ── Navegación ────────────────────────────────────────────────────────────

    def navigate(self) -> None:
        """Navega al carrito haciendo clic en el ícono del header."""
        self.page.click(self.CART_ICON)
        self.page.wait_for_url("**/checkout**", timeout=15_000)
        self.page.wait_for_load_state("networkidle", timeout=15_000)
        # Angular puede renderizar la tabla después de networkidle; espera al contenido
        try:
            self.page.wait_for_selector(
                f"table.table, {self.EMPTY_CART_MSG}",
                state="visible",
                timeout=8_000,
            )
        except Exception:
            pass

    def navigate_direct(self) -> None:
        """Navega directamente a la URL del checkout."""
        self.page.goto(f"{self.base_url}/checkout")
        self.page.wait_for_load_state("networkidle", timeout=30_000)

    # ── Lectura de datos ──────────────────────────────────────────────────────

    def get_cart_badge_count(self) -> int:
        """Lee el número del badge de carrito en el header."""
        try:
            text = self.page.locator(self.CART_QUANTITY_BADGE).inner_text(timeout=5_000)
            return int(text.strip())
        except Exception:
            return 0

    def get_item_count(self) -> int:
        """Retorna el número de filas (productos) en la tabla del carrito."""
        return self.page.locator(self.CART_ITEMS).count()

    def get_item_names(self) -> list[str]:
        """Retorna los nombres de todos los productos en el carrito."""
        names = self.page.locator(f"{self.CART_ITEMS} {self.CART_ITEM_NAME}")
        return [names.nth(i).inner_text().strip() for i in range(names.count())]

    def get_item_quantity(self, index: int = 0) -> int:
        """Retorna la cantidad del ítem en la posición indicada."""
        raw = self.page.locator(self.CART_ITEM_QUANTITY).nth(index).input_value()
        return int(raw)

    def get_total(self) -> float:
        """Retorna el total del carrito como número flotante."""
        raw = self.page.locator(self.CART_TOTAL).inner_text().strip()
        return parse_price(raw)

    def is_empty_message_visible(self) -> bool:
        """Retorna True si no hay items en el carrito."""
        try:
            self.page.locator(self.EMPTY_CART_MSG).wait_for(timeout=5_000)
            return True
        except Exception:
            return self.page.locator(self.CART_ITEMS).count() == 0

    def get_toast_text(self) -> str:
        """Retorna el texto de todas las notificaciones flotantes concatenadas."""
        alert = self.page.locator(self.TOAST_MESSAGE)
        alert.first.wait_for(timeout=8_000)
        texts = []
        for i in range(alert.count()):
            try:
                texts.append(alert.nth(i).inner_text(timeout=2_000).strip())
            except Exception:
                pass
        return " | ".join(texts)

    # ── Acciones ──────────────────────────────────────────────────────────────

    def update_quantity(self, index: int, quantity: int) -> None:
        """Edita directamente el campo de cantidad de un ítem."""
        qty_input = self.page.locator(self.CART_ITEM_QUANTITY).nth(index)
        qty_input.click(click_count=3)
        qty_input.type(str(quantity))
        qty_input.press("Tab")
        self.page.wait_for_timeout(1_000)

    def remove_item(self, index: int = 0) -> None:
        """Hace clic en el botón X (btn-danger) para eliminar el ítem indicado."""
        self.page.locator(self.CART_ITEM_REMOVE).nth(index).click()
        self.page.wait_for_timeout(1_500)
