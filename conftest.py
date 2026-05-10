"""
conftest.py
===========
Fixtures globales de pytest + generador del reporte HTML custom (reporte_po.html).

Fixtures expuestos:
  - api_token          (session)  → JWT obtenido por API
  - api_client         (function) → dict con clientes HTTP autenticados
  - browser_context    (function) → BrowserContext con sesión iniciada
  - page_products      (function) → Page ya en la página de productos
  - empty_cart         (function) → garantiza carrito vacío antes y después del test

Reporte HTML:
  - Se genera automáticamente en pytest_sessionfinish → reporte_po.html
  - Dos columnas: técnica (izquierda) | negocio (derecha)
  - Screenshot base64 siempre presente (éxito y fallo)
  - Summary bar con totales passed / failed / error
"""

from __future__ import annotations

import base64
import json
import os
import re
import textwrap
import time
from pathlib import Path
from typing import Generator

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from api.auth_client import AuthClient
from api.cart_client import CartClient
from api.products_client import ProductsClient
from pages.cart_page import CartPage
from pages.product_detail_page import ProductDetailPage
from pages.products_page import ProductsPage

import requests as _requests

load_dotenv()

# ── Allure (opcional: se omite si no está instalado) ─────────────────────────
try:
    import allure
    from allure_commons.types import Severity as _Severity
    _ALLURE_AVAILABLE = True
except ImportError:
    _ALLURE_AVAILABLE = False

_FEATURE_LABELS: dict[str, str] = {
    "busqueda": "Búsqueda de Productos",
    "filtros":  "Filtros por Categoría",
    "detalle":  "Detalle de Producto",
    "carrito":  "Gestión del Carrito",
}

from config import BASE_URL, HEADLESS  # noqa: E402

# Almacén global de resultados para el reporte HTML
_RESULTS: list[dict] = []


def pytest_configure(config):
    """Obtiene IDs frescos de productos desde la API antes de que los tests se importen."""
    api_url = os.getenv("API_URL", "https://api.practicesoftwaretesting.com")
    try:
        products = []
        page = 1
        while True:
            r = _requests.get(
                f"{api_url}/products",
                params={"page": page, "between": "price,1,100", "is_rental": "false"},
                timeout=15,
            )
            data = r.json()
            products.extend(data.get("data", []))
            if page >= data.get("last_page", 1):
                break
            page += 1

        with_stock = next(
            (p for p in products if p["name"] == "Bolt Cutters" and p.get("in_stock")),
            None,
        )
        out_of_stock = next(
            (p for p in products if p["name"] == "Long Nose Pliers" and not p.get("in_stock")),
            None,
        )

        if with_stock:
            os.environ["PRODUCT_WITH_STOCK_ID"] = with_stock["id"]
            os.environ["PRODUCT_WITH_STOCK_NAME"] = with_stock["name"]
            os.environ["PRODUCT_WITH_STOCK_PRICE"] = str(with_stock["price"])
        if out_of_stock:
            os.environ["PRODUCT_OUT_OF_STOCK_ID"] = out_of_stock["id"]
            os.environ["PRODUCT_OUT_OF_STOCK_NAME"] = out_of_stock["name"]

        print(f"\n[IDs dinamicos] Bolt Cutters={with_stock['id'] if with_stock else 'NO ENCONTRADO'}")
        print(f"[IDs dinamicos] Long Nose Pliers={out_of_stock['id'] if out_of_stock else 'NO ENCONTRADO'}")
    except Exception as e:
        print(f"\n[IDs dinamicos] Error al obtener IDs: {e}. Se usaran los del .env")


# ══════════════════════════════════════════════════════════════════════════════
# ALLURE METADATA  (inyección automática de labels y descripción de 2 columnas)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _allure_metadata(request):
    """
    Inyecta automáticamente en cada test:
    - Feature (pestaña Behaviors de Allure) → derivado del marcador pytest
    - Severity → smoke=critical, negativo=minor, resto=normal
    - Title    → nombre legible a partir del nombre de función
    - Description HTML con dos columnas: Técnica (azul) | Negocio (verde)
    """
    if not _ALLURE_AVAILABLE:
        yield
        return

    doc  = getattr(request.node.function, "__doc__", "") or ""
    meta = _parse_docstring(doc)

    # Feature → pestaña Behaviors (visión de negocio por feature)
    for mark_name, feature_label in _FEATURE_LABELS.items():
        if request.node.get_closest_marker(mark_name):
            allure.dynamic.feature(feature_label)
            break

    # Story → nombre legible del test
    story = (
        request.node.name
        .replace("test_", "")
        .replace("_", " ")
        .title()
    )
    allure.dynamic.story(story)
    allure.dynamic.title(story)

    # Severity
    if request.node.get_closest_marker("smoke"):
        allure.dynamic.severity(_Severity.CRITICAL)
    elif request.node.get_closest_marker("negativo"):
        allure.dynamic.severity(_Severity.MINOR)
    else:
        allure.dynamic.severity(_Severity.NORMAL)

    # Descripción HTML de dos columnas si el docstring tiene contenido
    if any(meta.values()):
        html = f"""
        <table style="width:100%;border-collapse:collapse;font-family:'Segoe UI',sans-serif;font-size:14px">
          <thead>
            <tr>
              <th style="width:50%;background:#dbeafe;color:#1e40af;padding:10px 14px;
                         border:1px solid #93c5fd;text-align:left;font-size:13px;
                         text-transform:uppercase;letter-spacing:.05em">
                Contexto Técnico — Equipo de Desarrollo
              </th>
              <th style="width:50%;background:#dcfce7;color:#15803d;padding:10px 14px;
                         border:1px solid #86efac;text-align:left;font-size:13px;
                         text-transform:uppercase;letter-spacing:.05em">
                Contexto de Negocio — Stakeholders
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="padding:12px 14px;border:1px solid #e2e8f0;vertical-align:top;
                         background:#f8faff">
                <p style="margin:0 0 8px"><strong>Escenario:</strong><br>
                   {meta.get('escenario', '—')}</p>
                <p style="margin:0"><strong>Acción correctiva:</strong><br>
                   {meta.get('accion', '—')}</p>
              </td>
              <td style="padding:12px 14px;border:1px solid #e2e8f0;vertical-align:top;
                         background:#f8fff8">
                <p style="margin:0 0 8px"><strong>Resultado esperado:</strong><br>
                   {meta.get('esperado', '—')}</p>
                <p style="margin:0"><strong>Impacto si falla:</strong><br>
                   {meta.get('impacto', '—')}</p>
              </td>
            </tr>
          </tbody>
        </table>
        """
        allure.dynamic.description_html(html)

    yield


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE API
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def api_token() -> str:
    """Login por API una sola vez en la sesión. Retorna el JWT."""
    client = AuthClient()
    return client.login()


@pytest.fixture(scope="function")
def api_client(api_token: str) -> dict:
    """Retorna un dict con instancias autenticadas de todos los clientes HTTP."""
    return {
        "auth": AuthClient(),
        "products": ProductsClient(token=api_token),
        "cart": CartClient(token=api_token),
    }


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE BROWSER / PAGE
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def _playwright():
    """Instancia única de Playwright para toda la sesión (evita relanzar el proceso)."""
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def _browser(_playwright) -> Generator[Browser, None, None]:
    """Browser reutilizable en toda la sesión."""
    browser = _playwright.chromium.launch(headless=HEADLESS)
    yield browser
    browser.close()


@pytest.fixture(scope="session")
def _auth_storage_state(_browser) -> str:
    """
    Login único por UI para capturar storage_state.
    Se reutiliza en todos los browser_context de la sesión.
    """
    context = _browser.new_context()
    page = context.new_page()
    page.goto(f"{BASE_URL}/auth/login", wait_until="domcontentloaded", timeout=30_000)

    # Rellena el formulario de login
    page.fill('[data-test="email"]', os.getenv("USER_EMAIL", ""))
    page.fill('[data-test="password"]', os.getenv("USER_PASSWORD", ""))
    page.click('[data-test="login-submit"]')

    # Espera a que la navegación salga de la página de login
    page.wait_for_url(lambda url: "/auth/login" not in url, timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=30_000)

    # Guarda el estado (cookies + localStorage) en un archivo temporal
    state_path = str(Path(__file__).parent / ".auth_state.json")
    context.storage_state(path=state_path)
    page.close()
    context.close()
    return state_path


@pytest.fixture(scope="function")
def browser_context(_browser, _auth_storage_state) -> Generator[BrowserContext, None, None]:
    """
    BrowserContext con sesión ya autenticada.
    scope=function para aislar estado entre tests (importante para xdist).
    """
    context = _browser.new_context(storage_state=_auth_storage_state)
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(browser_context: BrowserContext, request) -> Generator[Page, None, None]:
    """
    Page fixture que almacena la referencia en el nodo de test para el hook
    de reporte (necesario para tomar screenshots automáticos).
    """
    p = browser_context.new_page()
    request.node._playwright_page = p  # referencia accesible desde el hook
    yield p
    p.close()


@pytest.fixture(scope="function")
def page_products(page: Page) -> ProductsPage:
    """Navega a la página de productos y retorna el Page Object listo para usar."""
    po = ProductsPage(page, BASE_URL)
    po.navigate()
    return po


def _clear_cart_via_ui(page: Page) -> None:
    """Navega al checkout y elimina todos los ítems via UI (botón btn-danger)."""
    try:
        page.goto(f"{BASE_URL}/checkout")
        page.wait_for_load_state("networkidle", timeout=30_000)
        remove_selector = "a.btn-danger"
        while page.locator(remove_selector).count() > 0:
            page.locator(remove_selector).first.click()
            page.wait_for_timeout(1_500)
    except Exception:
        pass


@pytest.fixture(scope="function")
def empty_cart(api_client: dict, page: Page) -> Generator[None, None, None]:
    """
    Garantiza que el carrito esté vacío ANTES y DESPUÉS del test.
    Usa la UI para limpiar (la API no expone un endpoint GET /carts sin cart_id).
    """
    _clear_cart_via_ui(page)
    yield
    _clear_cart_via_ui(page)


# ══════════════════════════════════════════════════════════════════════════════
# HOOKS DE REPORTE
# ══════════════════════════════════════════════════════════════════════════════


def _parse_docstring(doc: str) -> dict:
    """
    Extrae campos del docstring con formato:
      Escenario: ...
      Esperado:  ...
      Impacto:   ...
      Accion:    ...
    """
    fields = {"escenario": "", "esperado": "", "impacto": "", "accion": ""}
    if not doc:
        return fields
    mapping = {
        "escenario": r"Escenario\s*:\s*(.+)",
        "esperado": r"Esperado\s*:\s*(.+)",
        "impacto": r"Impacto\s*:\s*(.+)",
        "accion": r"Accion\s*:\s*(.+)",
    }
    for key, pattern in mapping.items():
        m = re.search(pattern, doc, re.IGNORECASE)
        if m:
            fields[key] = m.group(1).strip()
    return fields


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Captura resultado, screenshot y metadatos de cada test tras su ejecución."""
    outcome = yield
    report = outcome.get_result()

    # Solo registramos en la fase "call" (la ejecución real del test)
    if call.when != "call":
        return

    # ── Screenshot ──────────────────────────────────────────────────────────
    page: Page | None = getattr(item, "_playwright_page", None)
    screenshot_b64 = ""
    if page:
        try:
            screenshot_bytes = page.screenshot(full_page=False)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception:
            pass  # si la página ya cerró, no hay screenshot

    # ── Determina estado ─────────────────────────────────────────────────────
    if report.passed:
        status = "passed"
    elif report.failed:
        status = "failed"
    else:
        status = "error"

    # ── Extrae metadatos del docstring ───────────────────────────────────────
    doc = getattr(item.function, "__doc__", "") or ""
    meta = _parse_docstring(doc)

    # ── URL actual del browser ───────────────────────────────────────────────
    url = BASE_URL
    if page:
        try:
            url = page.url
        except Exception:
            pass

    _RESULTS.append(
        {
            "file": Path(str(item.fspath)).name,
            "function": item.name,
            "status": status,
            "duration": f"{report.duration:.2f}s",
            "error": str(report.longrepr) if report.failed or status == "error" else "",
            "screenshot": screenshot_b64,
            "url": url,
            **meta,
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
# GENERADOR DEL REPORTE HTML
# ══════════════════════════════════════════════════════════════════════════════

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>QA Report – practicesoftwaretesting.com</title>
<style>
  :root {{
    --green:#22c55e; --red:#ef4444; --orange:#f97316;
    --blue:#3b82f6;  --gray:#6b7280; --bg:#f8fafc;
    --border:#e2e8f0; --card:#ffffff;
  }}
  * {{ box-sizing: border-box; margin:0; padding:0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background:var(--bg); color:#1e293b; }}
  header {{
    background:#1e293b; color:#f8fafc; padding:1.5rem 2rem;
    display:flex; align-items:center; gap:1rem;
  }}
  header h1 {{ font-size:1.25rem; font-weight:700; }}
  header span {{ font-size:.85rem; color:#94a3b8; }}
  .summary-bar {{
    display:flex; gap:1rem; padding:1rem 2rem; background:#fff;
    border-bottom:1px solid var(--border);
  }}
  .badge {{
    display:inline-flex; align-items:center; gap:.4rem;
    padding:.35rem .8rem; border-radius:9999px;
    font-weight:700; font-size:.9rem;
  }}
  .badge-passed  {{ background:#dcfce7; color:#16a34a; }}
  .badge-failed  {{ background:#fee2e2; color:#dc2626; }}
  .badge-error   {{ background:#ffedd5; color:#ea580c; }}
  .badge-total   {{ background:#e0e7ff; color:#4338ca; }}
  main {{ padding:1.5rem 2rem; display:flex; flex-direction:column; gap:1rem; }}
  .test-card {{
    background:var(--card); border:1px solid var(--border);
    border-radius:.75rem; overflow:hidden;
    box-shadow:0 1px 3px rgba(0,0,0,.06);
  }}
  .test-card-header {{
    display:flex; align-items:center; gap:.75rem;
    padding:.75rem 1rem; border-bottom:1px solid var(--border);
    background:#f1f5f9;
  }}
  .status-dot {{
    width:10px; height:10px; border-radius:50%; flex-shrink:0;
  }}
  .passed  {{ background:var(--green); }}
  .failed  {{ background:var(--red);   }}
  .error   {{ background:var(--orange);}}
  .test-card-header h2 {{
    font-size:.9rem; font-weight:600; flex:1;
  }}
  .duration {{ font-size:.8rem; color:var(--gray); }}
  .test-card-body {{
    display:grid; grid-template-columns:1fr 1fr; gap:0;
  }}
  .col {{ padding:1rem; }}
  .col:first-child {{ border-right:1px solid var(--border); }}
  .col h3 {{
    font-size:.75rem; font-weight:700; text-transform:uppercase;
    letter-spacing:.05em; color:var(--gray); margin-bottom:.5rem;
  }}
  .meta-row {{ margin-bottom:.4rem; font-size:.85rem; }}
  .meta-label {{ font-weight:600; color:#475569; }}
  .url {{ word-break:break-all; color:var(--blue); font-size:.8rem; }}
  .error-log {{
    background:#fef2f2; border:1px solid #fecaca;
    border-radius:.5rem; padding:.75rem;
    font-family:monospace; font-size:.75rem;
    white-space:pre-wrap; word-break:break-all;
    max-height:200px; overflow-y:auto; margin-top:.5rem;
    color:#dc2626;
  }}
  .screenshot-wrap {{ margin-top:.75rem; }}
  .screenshot-wrap img {{
    max-width:100%; border-radius:.5rem;
    border:1px solid var(--border); cursor:pointer;
  }}
  .biz-field {{ margin-bottom:.75rem; }}
  .biz-field .label {{
    font-size:.7rem; font-weight:700; text-transform:uppercase;
    letter-spacing:.05em; color:var(--gray); margin-bottom:.2rem;
  }}
  .biz-field .value {{ font-size:.875rem; line-height:1.5; }}
  footer {{
    text-align:center; padding:1.5rem; color:var(--gray);
    font-size:.8rem; border-top:1px solid var(--border);
  }}
</style>
</head>
<body>
<header>
  <div>
    <h1>QA Automation Report</h1>
    <span>practicesoftwaretesting.com &nbsp;|&nbsp; {generated_at}</span>
  </div>
</header>
<div class="summary-bar">
  <span class="badge badge-total">Total: {total}</span>
  <span class="badge badge-passed">✓ Passed: {passed}</span>
  <span class="badge badge-failed">✗ Failed: {failed}</span>
  <span class="badge badge-error">⚠ Error: {errors}</span>
</div>
<main>
{cards}
</main>
<footer>QA Automation Portfolio · MiguelZod24 · Generated {generated_at}</footer>
</body>
</html>
"""

_CARD_TEMPLATE = """\
<div class="test-card">
  <div class="test-card-header">
    <div class="status-dot {status}"></div>
    <h2>{function}</h2>
    <span class="duration">{duration}</span>
  </div>
  <div class="test-card-body">
    <!-- COLUMNA IZQUIERDA: detalles técnicos -->
    <div class="col">
      <h3>Detalles Técnicos</h3>
      <div class="meta-row"><span class="meta-label">Archivo:</span> {file}</div>
      <div class="meta-row"><span class="meta-label">URL:</span>
        <span class="url">{url}</span>
      </div>
      <div class="meta-row"><span class="meta-label">Duración:</span> {duration}</div>
      {error_block}
      {screenshot_block}
    </div>
    <!-- COLUMNA DERECHA: contexto de negocio -->
    <div class="col">
      <h3>Contexto de Negocio</h3>
      <div class="biz-field">
        <div class="label">Escenario</div>
        <div class="value">{escenario}</div>
      </div>
      <div class="biz-field">
        <div class="label">Esperado</div>
        <div class="value">{esperado}</div>
      </div>
      <div class="biz-field">
        <div class="label">Impacto</div>
        <div class="value">{impacto}</div>
      </div>
      <div class="biz-field">
        <div class="label">Acción si falla</div>
        <div class="value">{accion}</div>
      </div>
    </div>
  </div>
</div>
"""


def _build_card(result: dict) -> str:
    error_block = ""
    if result["error"]:
        # Trunca el error a 2000 caracteres para no inflar el HTML
        error_text = result["error"][:2000]
        error_block = f'<div class="error-log">{error_text}</div>'

    screenshot_block = ""
    if result["screenshot"]:
        screenshot_block = (
            '<div class="screenshot-wrap">'
            f'<img src="data:image/png;base64,{result["screenshot"]}" '
            'alt="screenshot" title="Screenshot del test"/>'
            "</div>"
        )

    return _CARD_TEMPLATE.format(
        status=result["status"],
        function=result["function"],
        file=result["file"],
        url=result["url"],
        duration=result["duration"],
        error_block=error_block,
        screenshot_block=screenshot_block,
        escenario=result.get("escenario", ""),
        esperado=result.get("esperado", ""),
        impacto=result.get("impacto", ""),
        accion=result.get("accion", ""),
    )


def pytest_sessionfinish(session, exitstatus):
    """Genera reporte_po.html al finalizar todos los tests."""
    if not _RESULTS:
        return

    passed = sum(1 for r in _RESULTS if r["status"] == "passed")
    failed = sum(1 for r in _RESULTS if r["status"] == "failed")
    errors = sum(1 for r in _RESULTS if r["status"] == "error")
    total = len(_RESULTS)

    cards_html = "\n".join(_build_card(r) for r in _RESULTS)

    from datetime import datetime
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = _HTML_TEMPLATE.format(
        total=total,
        passed=passed,
        failed=failed,
        errors=errors,
        cards=cards_html,
        generated_at=generated_at,
    )

    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    output_path = reports_dir / "reporte_po.html"
    output_path.write_text(html, encoding="utf-8")
    print(f"\nReporte HTML generado: {output_path}")
