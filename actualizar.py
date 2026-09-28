"""
Consulta el tipo de cambio (compra/venta USD) de cada banco de bancos.py
y escribe un archivo de texto por banco en docs/.

Uso:
  python actualizar.py                 # actualiza todos y escribe en docs/
  python actualizar.py --probar        # prueba todos SIN escribir nada
  python actualizar.py --probar bcp    # prueba solo un banco
"""
import argparse
import html as htmllib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from bancos import BANCOS

DOCS = Path("docs")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleTrapp/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36").replace("AppleTrapp", "AppleWebKit")
NUM = r"(\d{1,2}[.,]\d{1,4})"
PATRON_COMPRA = r"compra\D{0,60}?" + NUM
PATRON_VENTA = r"venta\D{0,60}?" + NUM
MIN_OK, MAX_OK = 5.0, 20.0          # rango razonable Bs por USD
BOLIVIA = timezone(timedelta(hours=-4))


def descargar(b):
    if b.get("modo") == "playwright":
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            nav = p.chromium.launch()
            page = nav.new_page(user_agent=UA)
            page.goto(b["url"], wait_until="networkidle", timeout=60000)
            contenido = page.content()
            nav.close()
            return contenido
    r = requests.get(b["url"], timeout=30, headers={"User-Agent": UA},
                     verify=b.get("ssl_verify", True))
    r.raise_for_status()
    return r.text


def buscar(texto, patron):
    for m in re.finditer(patron, texto, re.I):
        v = float(m.group(1).replace(",", "."))
        if MIN_OK <= v <= MAX_OK:
            return v
    return None


def fmt(v):
    s = f"{v:.4f}".rstrip("0")
    ent, dec = s.split(".")
    return f"{ent}.{dec.ljust(2, '0')}"


def extraer(contenido, b):
    texto = BeautifulSoup(contenido, "html.parser").get_text(" ", strip=True)
    compra = buscar(texto, b.get("regex_compra", PATRON_COMPRA))
    venta = buscar(texto, b.get("regex_venta", PATRON_VENTA))
    if compra is None or venta is None:
        raise ValueError("no se encontraron compra/venta en la página")
    return fmt(compra), fmt(venta)


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


def generar_indice():
    filas, resumen = [], {}
    ahora = datetime.now(BOLIVIA).strftime("%Y-%m-%d %H:%M")
    for b in BANCOS:
        d = leer_txt(DOCS / f"{b['id']}.txt")
        e = htmllib.escape
        if d:
            resumen[b["id"]] = d
            filas.append(f"<tr><td>{e(b['nombre'])}</td><td>{e(d['compra'])}</td>"
                         f"<td>{e(d['venta'])}</td><td>{e(d['actualizado'])}</td>"
                         f"<td><a href=\"{b['id']}.txt\">txt</a></td></tr>")
        else:
            filas.append(f"<tr><td>{e(b['nombre'])}</td><td colspan=\"4\">sin datos</td></tr>")
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
    escribir_si_cambia(DOCS / "index.html", plantilla.replace("{{FILAS}}", "\n".join(filas)))
    escribir_si_cambia(DOCS / "todos.json",
                       json.dumps(resumen, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probar", nargs="?", const="todos", help="probar sin escribir (opcional: id de banco)")
    args = ap.parse_args()
    DOCS.mkdir(exist_ok=True)

    bancos = BANCOS
    if args.probar and args.probar != "todos":
        bancos = [b for b in BANCOS if b["id"] == args.probar]
        if not bancos:
            sys.exit(f"Banco desconocido: {args.probar}")

    ok, fallos = 0, []
    for b in bancos:
        try:
            compra, venta = extraer(descargar(b), b)
        except Exception as e:
            fallos.append(b["id"])
            print(f"[FALLO] {b['id']}: {e}")
            continue
        ok += 1
        print(f"[OK]    {b['id']}: compra={compra} venta={venta}")
        if args.probar:
            continue
        ruta = DOCS / f"{b['id']}.txt"
        previo = leer_txt(ruta)
        if previo and previo.get("compra") == compra and previo.get("venta") == venta:
            continue  # sin cambios: no tocar el archivo (evita commits inútiles)
        ahora = datetime.now(BOLIVIA).strftime("%Y-%m-%d %H:%M (hora Bolivia)")
        ruta.write_text(f"banco={b['nombre']}\ncompra={compra}\nventa={venta}\nactualizado={ahora}\n",
                        encoding="utf-8")

    if not args.probar:
        generar_indice()
    print(f"\nResumen: {ok} OK, {len(fallos)} con fallo {fallos if fallos else ''}")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
