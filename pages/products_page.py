import re

from playwright.sync_api import Page


class ProductsPage:
    """Page Object para la página de listado de productos (/)."""

    # ── Locators ─────────────────────────────────────────────────────────────

    # Campo de texto de búsqueda
    SEARCH_INPUT = '[data-test="search-query"]'
    # Botón que dispara la búsqueda
    SEARCH_BUTTON = '[data-test="search-submit"]'
    # Cada tarjeta de producto en el grid (el sitio usa data-test="product-{id}")
    PRODUCT_CARDS = '[data-test^="product-"]:has([data-test="product-name"])'
    # Nombre dentro de cada tarjeta de producto
    PRODUCT_NAME = '[data-test="product-name"]'
    # Precio dentro de cada tarjeta de producto
    PRODUCT_PRICE = '[data-test="product-price"]'
    # Texto que indica cuántos productos se encontraron (ej: "4 productos encontrados")
    RESULT_COUNT = '[data-test="search-result-count"]'
    # Mensaje que aparece cuando no hay resultados
    NO_RESULTS_MSG = '[data-test="no-results"]'
    # Contenedor del sidebar de filtros de categoría
    FILTER_SIDEBAR = '[data-test="filters"]'
    # Cada checkbox de categoría dentro del sidebar
    CATEGORY_CHECKBOX = 'input[data-test="category-{slug}"]'
    # Paginación – botón de página siguiente
    PAGINATION_NEXT = '[aria-label="Next"]'
    # Paginación – todos los ítems (para contar páginas)
    PAGINATION_ITEMS = '.page-item'

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    # ── Navegación ────────────────────────────────────────────────────────────

    def navigate(self) -> None:
        """Abre la página de catálogo de productos."""
        self.page.goto(f"{self.base_url}/")
        # Espera a que al menos un producto sea visible antes de interactuar
        self.page.wait_for_selector(self.PRODUCT_CARDS, timeout=30_000)

    # ── Acciones de búsqueda ──────────────────────────────────────────────────

    def search(self, term: str) -> None:
        """Escribe en el campo de búsqueda y pulsa el botón Search."""
        self.page.fill(self.SEARCH_INPUT, term)
        self.page.click(self.SEARCH_BUTTON)
        # Espera breve a que la UI reaccione (red latency del filtrado)
        self.page.wait_for_timeout(1_500)

    def get_search_input_value(self) -> str:
        """Devuelve el valor actual del campo de búsqueda."""
        return self.page.input_value(self.SEARCH_INPUT)

    # ── Lectura de resultados ─────────────────────────────────────────────────

    def get_product_names(self) -> list[str]:
        """Retorna los nombres de todos los productos visibles en el grid."""
        cards = self.page.locator(f"{self.PRODUCT_CARDS} {self.PRODUCT_NAME}")
        return cards.all_inner_texts()

    def get_product_count(self) -> int:
        """Cuenta los productos visibles en la página actual."""
        return self.page.locator(self.PRODUCT_CARDS).count()

    def get_result_total_from_ui(self) -> int:
        """Extrae el número del texto de resultados (ej: 'There are 4 results' → 4)."""
        try:
            text = self.page.locator(self.RESULT_COUNT).inner_text(timeout=5_000)
            numbers = re.findall(r"\d+", text)
            return int(numbers[0]) if numbers else 0
        except Exception:
            return 0

    def no_results_message_visible(self) -> bool:
        """Retorna True si se muestra el mensaje de 'sin resultados'."""
        return self.page.locator(self.NO_RESULTS_MSG).is_visible()

    # ── Acciones de filtrado por categoría ───────────────────────────────────

    def click_category(self, category_label: str) -> None:
        """Marca o desmarca el checkbox de la categoría indicada por su texto visible."""
        self.page.locator("label").filter(has_text=category_label).click()
        # El filtro se aplica automáticamente (sin botón extra)
        self.page.wait_for_timeout(1_500)

    def get_checked_categories(self) -> list[str]:
        """Retorna los nombres de las categorías actualmente marcadas."""
        checked_inputs = self.page.locator('input[data-test^="category-"]:checked')
        checked = []
        for i in range(checked_inputs.count()):
            try:
                text = checked_inputs.nth(i).evaluate(
                    "el => el.parentElement.textContent.trim()"
                )
                checked.append(text)
            except Exception:
                pass
        return checked

    # ── Navegación a detalle ──────────────────────────────────────────────────

    def click_product(self, index: int = 0) -> str:
        """Hace clic en el producto en la posición indicada. Retorna la URL resultante."""
        self.page.locator(self.PRODUCT_CARDS).nth(index).click()
        self.page.wait_for_url("**/product/**", timeout=10_000)
        return self.page.url

    def click_product_by_name(self, name: str) -> None:
        """Hace clic en el primer producto cuyo nombre contiene el texto indicado."""
        self.page.locator(
            f"{self.PRODUCT_CARDS}:has({self.PRODUCT_NAME}:has-text('{name}'))"
        ).first.click()
        self.page.wait_for_url("**/product/**", timeout=10_000)
