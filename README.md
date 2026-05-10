# QA Automation Portfolio – practicesoftwaretesting.com

**Stack:** Python · Playwright · Pytest · Requests · pytest-xdist · Allure

---

## Estructura

```
practicesoftwaretesting-products/
├── api/
│   ├── auth_client.py        # POST /users/login → JWT
│   ├── products_client.py    # GET /products, GET /products/{id}
│   └── cart_client.py        # GET/POST /carts, DELETE /carts/{id}/product/{id}
├── pages/
│   ├── products_page.py      # Catálogo: búsqueda, filtros, grid
│   ├── product_detail_page.py # Detalle: nombre, precio, add-to-cart
│   └── cart_page.py          # Carrito: cantidad, total, eliminar
├── tests/
│   ├── test_busqueda.py      # TC-01A…TC-02C  (6 tests)
│   ├── test_filtros.py       # TC-03A…TC-04B  (4 tests)
│   ├── test_detalle.py       # TC-05A…TC-06B  (4 tests)
│   └── test_carrito.py       # TC-07A…TC-11A  (7 tests)
├── conftest.py               # Fixtures + reporte reporte_po.html
├── pytest.ini                # Marks + opciones por defecto
├── requirements.txt
└── .env                      # Variables de entorno (no subir al repo)
```

---

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Ejecución

```bash
# Todos los tests
pytest

# Todos los tests en paralelo (1 worker por feature)
pytest -n 4

# Un feature específico
pytest tests/test_busqueda.py

# Solo smoke tests
pytest -m smoke

# Parallel + Allure
pytest -n 4 --alluredir=allure-results
allure serve allure-results
```

El reporte `reporte_po.html` se genera automáticamente al finalizar cada sesión.

---

## Casos de prueba (21 total)

| ID | Descripción | Capas |
|----|-------------|-------|
| TC-01A | Búsqueda por nombre exacto "Pliers" | UI+API |
| TC-01B | Búsqueda por término parcial "Pli" | UI+API |
| TC-01C | Búsqueda case-insensitive "PLIERS" | UI+API |
| TC-02A | Término inexistente → 0 resultados | UI+API |
| TC-02B | Campo vacío → no ejecuta búsqueda | UI |
| TC-02C | Solo espacios → 0 resultados | UI+API |
| TC-03A | Filtrar por "Other" aplica filtro | UI+API |
| TC-03B | Desmarcar restaura todos los productos | UI |
| TC-04A | Múltiples categorías acumulan resultados | UI+API |
| TC-04B | Desmarcar una de múltiples categorías | UI |
| TC-05A | Detalle coincide con datos de la API | UI+API |
| TC-05B | Categorías coinciden entre UI y API | UI+API |
| TC-06A | Botón habilitado para producto con stock | UI+API |
| TC-06B | Botón deshabilitado para producto agotado | UI |
| TC-07A | Agregar 1 unidad al carrito | UI+API |
| TC-07B | Agregar múltiples unidades | UI+API |
| TC-08A | Carrito persiste al navegar | UI+API |
| TC-08B | Carrito persiste al recargar | UI+API |
| TC-09A | Actualizar cantidad en el carrito | UI+API |
| TC-10A | Eliminar producto del carrito | UI+API |
| TC-11A | Carrito vacío al eliminar último producto | UI+API |

*QA Automation Portfolio · MiguelZod24 · practicesoftwaretesting.com*