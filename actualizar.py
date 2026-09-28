"""
Consulta el tipo de cambio (compra/venta USD) de cada banco definido en bancos.py
y escribe un archivo de texto por banco en docs/.

Uso:
  python actualizar.py                 # actualiza todos y escribe en docs/
  python actualizar.py --probar        # prueba todos SIN escribir nada
  python actualizar.py --probar bcp    # prueba solo un banco
  python actualizar.py --debug bcp     # muestra HTML/texto para depurar
"""
import argparse
import html as htmllib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bancos import BANCOS

DOCS = Path("docs")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# Formatos numéricos aceptados: 6.96 / 6,96 / 6.9600 / 6,9600
NUM = r"(\d{1,2}[.,]\d{1,4}|\d{1,2})"
PATRON_COMPRA = r"compra\D{0,80}?" + NUM
PATRON_VENTA = r"venta\D{0,80}?" + NUM

MIN_OK, MAX_OK = 5.0, 20.0          # rango razonable Bs por USD
BOLIVIA = timezone(timedelta(hours=-4))


# ---------------------------------------------------------------------------
# Sesión HTTP con reintentos y cabeceras realistas
# ---------------------------------------------------------------------------
def crear_sesion():
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-BO,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })
    return s


SESION = crear_sesion()


# ---------------------------------------------------------------------------
# Descarga del HTML (requests o Playwright)
# ---------------------------------------------------------------------------
def descargar(b, debug=False):
    modo = b.get("modo", "requests")

    if modo == "playwright":
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            nav = p.chromium.launch(headless=True)
            ctx = nav.new_context(
                user_agent=UA,
                locale="es-BO",
                extra_http_headers={
                    "Accept-Language": "es-BO,es;q=0.9,en;q=0.8",
                },
            )
            page = ctx.new_page()
            page.goto(b["url"], wait_until="domcontentloaded", timeout=60000)

            # Si el banco define un selector a esperar, lo respetamos
            selector = b.get("esperar_selector")
            if selector:
                try:
                    page.wait_for_selector(selector, timeout=30000)
                except Exception:
                    pass
            else:
                # Espera corta por si carga por JS
                page.wait_for_timeout(2500)

            # Scroll para forzar lazy-load si aplica
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1000)

            contenido = page.content()
            if debug:
                print("----- HTML (Playwright) -----")
                print(contenido[:3000])
            nav.close()
            return contenido

    # modo requests
    headers = dict(SESION.headers)
    if b.get("referer"):
        headers["Referer"] = b["referer"]
    else:
        headers["Referer"] = b["url"]

    r = SESION.get(
        b["url"],
        timeout=b.get("timeout", 30),
        headers=headers,
        verify=b.get("ssl_verify", True),
    )
    r.raise_for_status()

    # Forzar detección correcta de encoding si el banco no lo declara
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"

    if debug:
        print("----- HTML (requests) -----")
        print(r.text[:3000])
    return r.text


# ---------------------------------------------------------------------------
# Extracción de datos
# ---------------------------------------------------------------------------
def normalizar_numero(s):
    """Convierte '6,96' o '6.96' a float."""
    return float(s.replace(",", "."))


def buscar_regex(texto, patron):
    for m in re.finditer(patron, texto, re.I):
        try:
            v = normalizar_numero(m.group(1))
        except ValueError:
            continue
        if MIN_OK <= v <= MAX_OK:
            return v
    return None


def buscar_selector(soup, selector):
    """Devuelve el primer número válido dentro del selector CSS."""
    if not selector:
        return None
    nodo = soup.select_one(selector)
    if not nodo:
        return None
    texto = nodo.get_text(" ", strip=True)
    m = re.search(NUM, texto)
    if not m:
        return None
    try:
        v = normalizar_numero(m.group(1))
    except ValueError:
        return None
    return v if MIN_OK <= v <= MAX_OK else None


def extraer(contenido, b, debug=False):
    soup = BeautifulSoup(contenido, "html.parser")
    texto = soup.get_text(" ", strip=True)

    if debug:
        print("----- TEXTO -----")
        print(texto[:3000])
        print("-----------------")

    # 1) Intento por selector CSS (más estable si está definido)
    compra = buscar_selector(soup, b.get("selector_compra"))
    venta = buscar_selector(soup, b.get("selector_venta"))

    # 2) Fallback a regex sobre todo el texto
    if compra is None:
        compra = buscar_regex(texto, b.get("regex_compra", PATRON_COMPRA))
    if venta is None:
        venta = buscar_regex(texto, b.get("regex_venta", PATRON_VENTA))

    if compra is None or venta is None:
        faltan = []
        if compra is None:
            faltan.append("compra")
        if venta is None:
            faltan.append("venta")
        raise ValueError(f"no se encontró {'/'.join(faltan)} en la página")

    return fmt(compra), fmt(venta)


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    if "." not in s:
        s += ".00"
    ent, dec = s.split(".")
    return f"{ent}.{dec.ljust(2, '0')[:2]}"


# ---------------------------------------------------------------------------
# Utilidades de archivo
# ---------------------------------------------------------------------------
def leer_txt(ruta):
    if not ruta.exists():
        return None
    datos = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if "=" in linea:
            k, v = linea.split("=", 1)
            datos[k.strip()] = v.strip()
    return datos


def escribir_si_cambia(ruta, contenido):
    if ruta.exists() and ruta.read_text(encoding="utf-8") == contenido:
        return False
    ruta.write_text(contenido, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Generación de índice HTML + JSON
# ---------------------------------------------------------------------------
def generar_indice():
    filas, resumen = [], {}
    for b in BANCOS:
        d = leer_txt(DOCS / f"{b['id']}.txt")
        e = htmllib.escape
        if d:
            resumen[b["id"]] = d
            filas.append(
                f"<tr><td>{e(b['nombre'])}</td><td>{e(d['compra'])}</td>"
                f"<td>{e(d['venta'])}</td><td>{e(d['actualizado'])}</td>"
                f"<td><a href=\"{b['id']}.txt\">txt</a></td></tr>"
            )
        else:
            filas.append(
                f"<tr><td>{e(b['nombre'])}</td><td colspan=\"4\">sin datos</td></tr>"
            )

    plantilla = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tipo de cambio bancos de Bolivia</title>
<style>
body{font-family:system-ui,sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem}
table{border-collapse:collapse;width:100%}
th,td{border-bottom:1px solid #8884;padding:.5rem;text-align:left}
</style></head><body>
<h1>Tipo de cambio USD - Bancos de Bolivia</h1>
<table><tr><th>Banco</th><th>Compra (Bs)</th><th>Venta (Bs)</th><th>Último cambio</th><th>Archivo</th></tr>
{{FILAS}}
</table>
<p><a href="todos.json">todos.json</a></p>
</body></html>
"""
    escribir_si_cambia(
        DOCS / "index.html",
        plantilla.replace("{{FILAS}}", "\n".join(filas)),
    )
    escribir_si_cambia(
        DOCS / "todos.json",
        json.dumps(resumen, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probar", nargs="?", const="todos",
                    help="probar sin escribir (opcional: id de banco)")
    ap.add_argument("--debug", nargs="?", const="todos",
                    help="mostrar HTML/texto extraído (opcional: id de banco)")
    args = ap.parse_args()

    DOCS.mkdir(exist_ok=True)

    bancos = BANCOS
    filtro = args.debug if args.debug and args.debug != "todos" else (
        args.probar if args.probar and args.probar != "todos" else None
    )
    if filtro:
        bancos = [b for b in BANCOS if b["id"] == filtro]
        if not bancos:
            sys.exit(f"Banco desconocido: {filtro}")

    solo_probar = bool(args.probar)
    debug = bool(args.debug)

    ok, fallos = 0, []
    for b in bancos:
        try:
            contenido = descargar(b, debug=debug)
            compra, venta = extraer(contenido, b, debug=debug)
        except Exception as e:
            fallos.append(b["id"])
            print(f"[FALLO] {b['id']}: {type(e).__name__}: {e}")
            continue

        ok += 1
        print(f"[OK]    {b['id']}: compra={compra} venta={venta}")

        if solo_probar:
            continue

        ruta = DOCS / f"{b['id']}.txt"
        previo = leer_txt(ruta)
        if previo and previo.get("compra") == compra and previo.get("venta") == venta:
            continue

        ahora = datetime.now(BOLIVIA).strftime("%Y-%m-%d %H:%M (hora Bolivia)")
        ruta.write_text(
            f"banco={b['nombre']}\ncompra={compra}\nventa={venta}\nactualizado={ahora}\n",
            encoding="utf-8",
        )

        # pequeña pausa entre bancos para no disparar anti-bot
        time.sleep(0.5)

    if not solo_probar:
        generar_indice()

    print(f"\nResumen: {ok} OK, {len(fallos)} con fallo {fallos if fallos else ''}")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
