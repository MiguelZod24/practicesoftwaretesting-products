import requests

from config import API_URL, USER_EMAIL, USER_PASSWORD


class AuthClient:
    """Cliente HTTP para autenticación contra la API de practicesoftwaretesting."""

    def __init__(self):
        self.base_url = API_URL
        self.token: str | None = None

    def login(self, email: str = None, password: str = None) -> str:
        """POST /users/login → retorna access_token."""
        payload = {
            "email": email or USER_EMAIL,
            "password": password or USER_PASSWORD,
        }
        resp = requests.post(f"{self.base_url}/users/login", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "access_token" not in data:
            raise ValueError(f"La respuesta de login no contiene access_token: {data}")
        self.token = data["access_token"]
        return self.token

    def get_token(self) -> str:
        """Devuelve el token vigente; hace login automático si no existe."""
        if not self.token:
            self.login()
        return self.token
