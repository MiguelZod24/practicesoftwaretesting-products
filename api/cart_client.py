import requests

from config import API_URL


class CartClient:
    """Cliente HTTP para el recurso /carts de la API."""

    def __init__(self, token: str):
        self.base_url = API_URL
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._cart_id: str | None = None

    def set_cart_id(self, cart_id: str) -> None:
        """Define el cart_id activo (útil para sincronizar con el carrito creado en UI)."""
        self._cart_id = cart_id

    @property
    def cart_id(self) -> str | None:
        return self._cart_id

    def create_cart(self) -> str:
        """POST /carts → crea un carrito vacío, almacena y retorna su id."""
        resp = requests.post(f"{self.base_url}/carts", headers=self.headers, timeout=15)
        resp.raise_for_status()
        self._cart_id = resp.json()["id"]
        return self._cart_id

    def get_cart(self) -> dict:
        """GET /carts/{id} → retorna el carrito. Requiere que cart_id esté definido."""
        if not self._cart_id:
            return {"cart_items": []}
        resp = requests.get(
            f"{self.base_url}/carts/{self._cart_id}", headers=self.headers, timeout=15
        )
        resp.raise_for_status()
        return resp.json()

    def add_to_cart(self, product_id: str, quantity: int = 1) -> requests.Response:
        """POST /carts → crea un carrito nuevo (la API no soporta agregar items directamente)."""
        resp = requests.post(f"{self.base_url}/carts", headers=self.headers, timeout=15)
        if resp.status_code == 201:
            self._cart_id = resp.json().get("id")
        return resp

    def remove_from_cart(self, cart_id: str, product_id: str) -> requests.Response:
        """DELETE /carts/{cart_id}/product/{product_id} → elimina un ítem del carrito."""
        resp = requests.delete(
            f"{self.base_url}/carts/{cart_id}/product/{product_id}",
            headers=self.headers,
            timeout=15,
        )
        return resp

    def clear_cart(self) -> None:
        """Elimina todos los ítems del carrito conocido. Si no hay cart_id, no hace nada."""
        if not self._cart_id:
            return
        cart = self.get_cart()
        for item in cart.get("cart_items", []):
            product_id = (
                item.get("product_id") or (item.get("product") or {}).get("id")
            )
            if product_id:
                self.remove_from_cart(self._cart_id, product_id)
        self._cart_id = None
