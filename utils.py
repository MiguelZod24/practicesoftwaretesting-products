"""Funciones de utilidad compartidas entre Page Objects."""


def parse_price(raw: str) -> float:
    """Convierte un string de precio ('$48.41', '€12,50') a float."""
    return float(raw.replace("$", "").replace("€", "").replace(",", "").strip())
