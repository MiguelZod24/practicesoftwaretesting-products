from playwright.sync_api import Page

from utils import parse_price


class ProductDetailPage:
    """Page Object para la página de detalle de producto (/product/{id})."""

    # ── Locators ─────────────────────────────────────────────────────────────

    # Nombre del producto en el encabezado
    PRODUCT_NAME = '[data-test="product-name"]'
    # Precio del producto
    PRODUCT_PRICE = '[data-test="unit-price"]'
    # Tags de categoría debajo del nombre
    CATEGORY_TAGS = '[data-test="product-category"]'
    # Botón para agregar al carrito
    ADD_TO_CART_BTN = '[data-test="add-to-cart"]'
    # Etiqueta "Out of stock" para productos agotados
    OUT_OF_STOCK_LABEL = '[data-test="out-of-stock"]'
    # Selector numérico de cantidad (input)
    QUANTITY_INPUT = '[data-test="quantity"]'
    # Botón + para incrementar cantidad
    QUANTITY_INCREASE = '[data-test="increase-quantity"]'
    # Botón - para disminuir cantidad
    QUANTITY_DECREASE = '[data-test="decrease-quantity"]'
    # Mensaje flotante / toast de confirmación (usa role=alert en la v5)
    TOAST_MESSAGE = '[role="alert"]'
    # Contador del carrito en el header
    CART_QUANTITY = '[data-test="cart-quantity"]'

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    # ── Navegación ────────────────────────────────────────────────────────────

    def navigate(self, product_id: str) -> None:
        """Navega directamente a la página de detalle del producto."""
        self.page.goto(f"{self.base_url}/product/{product_id}")
        # Espera a que el nombre del producto sea visible para asegurar carga completa
        self.page.wait_for_selector(self.PRODUCT_NAME, timeout=30_000)

    # ── Lectura de datos ──────────────────────────────────────────────────────

    def get_name(self) -> str:
        """Retorna el nombre del producto visible en pantalla."""
        return self.page.locator(self.PRODUCT_NAME).inner_text().strip()

    def get_price(self) -> float:
        """Retorna el precio numérico del producto (sin símbolo de moneda)."""
        raw = self.page.locator(self.PRODUCT_PRICE).inner_text().strip()
        return parse_price(raw)

    def get_categories(self) -> list[str]:
        """Retorna la lista de categorías mostradas como tags en la página."""
        tags = self.page.locator(self.CATEGORY_TAGS)
        return [tags.nth(i).inner_text().strip() for i in range(tags.count())]

    def get_current_product_id(self) -> str:
        """Extrae el ID del producto desde la URL actual."""
        # La URL tiene el formato: .../product/{id}
        return self.page.url.rstrip("/").split("/")[-1]

    # ── Acciones ──────────────────────────────────────────────────────────────

    def set_quantity(self, quantity: int) -> None:
        """Establece la cantidad usando el botón + hasta alcanzar el valor deseado."""
        # Parte de 1 (valor inicial) e incrementa hasta llegar a la cantidad deseada
        for _ in range(quantity - 1):
            self.page.click(self.QUANTITY_INCREASE)

    def add_to_cart(self) -> None:
        """Hace clic en el botón 'Add to cart' y espera la respuesta de la API."""
        with self.page.expect_response(
            lambda r: "/carts" in r.url and r.request.method == "POST",
            timeout=10_000,
        ):
            self.page.click(self.ADD_TO_CART_BTN)
        self.page.wait_for_timeout(500)

    # ── Estado de los controles ───────────────────────────────────────────────

    def is_add_to_cart_enabled(self) -> bool:
        """Retorna True si el botón 'Add to cart' está habilitado."""
        return self.page.locator(self.ADD_TO_CART_BTN).is_enabled()

    def is_out_of_stock_shown(self) -> bool:
        """Retorna True si se muestra la etiqueta de producto agotado."""
        return self.page.locator(self.OUT_OF_STOCK_LABEL).is_visible()

    def get_cart_count(self) -> int:
        """Lee el número del badge del carrito en el header."""
        try:
            text = self.page.locator(self.CART_QUANTITY).inner_text(timeout=5_000)
            return int(text.strip())
        except Exception:
            return 0

    def get_toast_text(self) -> str:
        """Retorna el texto del mensaje flotante de confirmación."""
        return self.page.locator(self.TOAST_MESSAGE).inner_text(timeout=8_000).strip()
