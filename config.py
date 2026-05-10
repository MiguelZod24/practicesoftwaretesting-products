"""
Configuración centralizada del proyecto.
Todos los valores se leen del archivo .env o variables de entorno del sistema.
"""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_URL: str = os.getenv("BASE_URL", "https://practicesoftwaretesting.com")
API_URL: str = os.getenv("API_URL", "https://api.practicesoftwaretesting.com")
HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
USER_EMAIL: str = os.getenv("USER_EMAIL", "")
USER_PASSWORD: str = os.getenv("USER_PASSWORD", "")
