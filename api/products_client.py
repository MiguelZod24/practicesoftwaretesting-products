import requests

from config import API_URL


class ProductsClient:
    """Cliente HTTP para el recurso /products de la API."""

    def __init__(self, token: str = None):
        self.base_url = API_URL
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def get_products(self, category_slug: str = None, page: int = 1) -> dict:
        """GET /products con filtros opcionales. Retorna dict con 'data' y 'total'."""
        params: dict = {"page": page}
        if category_slug:
            params["by_category_slug"] = category_slug
        resp = requests.get(
            f"{self.base_url}/products", params=params, headers=self.headers, timeout=15
        )
        resp.raise_for_status()
        return resp.json()

    def search_products(self, q: str) -> dict:
        """GET /products/search?q={q} → búsqueda real de productos por nombre."""
        resp = requests.get(
            f"{self.base_url}/products/search",
            params={"q": q},
            headers=self.headers,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def get_product(self, product_id: str) -> dict:
        """GET /products/{id} → detalle completo del producto."""
        resp = requests.get(
            f"{self.base_url}/products/{product_id}", headers=self.headers, timeout=15
        )
        resp.raise_for_status()
        return resp.json()
