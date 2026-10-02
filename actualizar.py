"""
Consulta las tasas USD configuradas y guarda el valor actual más una línea
histórica por banco en docs/historial/.

Uso:
  python actualizar.py                 # actualiza todos y escribe en docs/
  python actualizar.py --probar        # prueba todos SIN escribir nada
  python actualizar.py --probar bcp    # prueba solo un banco
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bancos import BANCOS

DOCS = Path("docs")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleTrapp/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36").replace("AppleTrapp", "AppleWebKit")
NUM = r"([\d]{1,2}[.,][\d]{1,5})"
PATRON_COMPRA = r"compra\D{0,60}?" + NUM
PATRON_VENTA = r"venta\D{0,60}?" + NUM
MIN_OK, MAX_OK = 5.0, 20.0          # rango razonable Bs por USD
BOLIVIA = timezone(timedelta(hours=-4))


def descargar(b):
    if b.get("modo") == "playwright":
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            nav = p.chromium.launch(headless=True)
            page = nav.new_page(user_agent=UA, locale="es-BO")
            page.goto(b["url"], wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(b.get("espera_ms", 4000))
            for selector in (".modal button.close", ".modal [data-dismiss='modal']",
                             ".modal [data-bs-dismiss='modal']", "button.btn-close",
                             "button[aria-label='Cerrar']", "button[aria-label='Close']",
                             ".mfp-close", ".modal-dialog .close"):
                try:
                    button = page.locator(selector).first
                    if button.is_visible(timeout=400):
                        button.click(timeout=1000)
                        page.wait_for_timeout(300)
                except Exception:
                    pass
            for label in ("Cerrar", "Close", "Aceptar", "Entendido", "×"):
                try:
                    button = page.get_by_role("button", name=label, exact=True).first
                    if button.is_visible(timeout=300):
                        button.click(timeout=1000)
                        page.wait_for_timeout(300)
                except Exception:
                    pass
            contenido = page.content()
            nav.close()
            return contenido
    reintentos = Retry(total=3, connect=3, read=2, backoff_factor=1,
                       status_forcelist=(429, 500, 502, 503, 504),
                       allowed_methods=frozenset(["GET"]))
    sesion = requests.Session()
    sesion.mount("https://", HTTPAdapter(max_retries=reintentos))
    sesion.mount("http://", HTTPAdapter(max_retries=reintentos))
    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
               "Accept-Language": "es-BO,es;q=0.9,en;q=0.8", "Cache-Control": "no-cache"}
    r = sesion.get(b["url"], timeout=30, headers=headers,
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
    s = f"{v:.5f}".rstrip("0").rstrip(".")
    if "." not in s:
        s += ".00"
    else:
        ent, dec = s.split(".")
        s = f"{ent}.{dec.ljust(2, '0')}"
    return s


def extraer(contenido, b):
    soup = BeautifulSoup(contenido, "html.parser")
    texto = soup.get_text(" ", strip=True)
    if b.get("extractor") == "bnb":
        datos = {}
        etiquetas = {"compra": "dólar compra", "venta": "dólar venta", "oficial": "dólar oficial"}
        for campo, etiqueta in etiquetas.items():
            nodo = next((el for el in soup.find_all("span")
                         if " ".join(el.get_text(" ", strip=True).lower().split()) == etiqueta), None)
            valor_nodo = nodo.find_next_sibling("span") if nodo else None
            valor = buscar(valor_nodo.get_text(" ", strip=True), NUM) if valor_nodo else None
            datos[campo] = fmt(valor) if valor is not None else ""
        if datos["compra"] and datos["venta"]:
            return datos
        raise ValueError("no se encontraron compra y venta en los rótulos del BNB")
    if b.get("extractor") == "prodem":
        datos = {}
        for campo, selector in (("compra", "#prodem-compra"), ("venta", "#prodem-venta")):
            nodo = soup.select_one(selector)
            valor = buscar(nodo.get_text(" ", strip=True), NUM) if nodo else None
            datos[campo] = fmt(valor) if valor is not None else ""
        datos["oficial"] = ""
        if datos["compra"] and datos["venta"]:
            return datos
        raise ValueError("no se encontraron los nodos #prodem-compra y #prodem-venta")
    if b.get("extractor") == "bancomunidad":
        encabezado = soup.select_one(".csc-tc__titulo")
        oficial = buscar(encabezado.get_text(" ", strip=True), NUM) if encabezado else None
        tasas = {}
        tabla = soup.select_one(".csc-tc__tabla")
        if tabla:
            for fila in tabla.select("tr"):
                etiqueta = fila.find("th")
                valor_nodo = fila.find("td")
                if not etiqueta or not valor_nodo:
                    continue
                campo = etiqueta.get_text(" ", strip=True).lower()
                if campo in ("compra", "venta"):
                    valor = buscar(valor_nodo.get_text(" ", strip=True), NUM)
                    tasas[campo] = fmt(valor) if valor is not None else ""
        datos = {"compra": tasas.get("compra", ""), "venta": tasas.get("venta", ""),
                 "oficial": fmt(oficial) if oficial is not None else ""}
        if any(datos.values()):
            return datos
        raise ValueError("no se encontraron las tasas en la tabla .csc-tc__tabla")
    patrones = {"compra": b.get("regex_compra", PATRON_COMPRA),
                "venta": b.get("regex_venta", PATRON_VENTA),
                "oficial": b.get("regex_oficial")}
    datos = {campo: buscar(contenido if b["id"] in ("bcb", "prodem", "fortaleza") else texto, patron)
             if patron else None for campo, patron in patrones.items()}
    if not any(datos.values()):
        raise ValueError("no se encontró ninguna cotización configurada en la página")
    return {campo: fmt(valor) if valor is not None else "" for campo, valor in datos.items()}


def guardar_cotizacion(banco, datos, origen):
    ahora_dt = datetime.now(BOLIVIA)
    ahora = ahora_dt.strftime("%Y-%m-%d %H:%M:%S (hora Bolivia)")
    registro = {"banco_id": banco["id"], "banco": banco["nombre"],
                "consultado": ahora_dt.isoformat(timespec="seconds"), "origen": origen,
                **{k: (v or None) for k, v in datos.items()}}
    historial = DOCS / "historial" / f"{banco['id']}.jsonl"
    historial.parent.mkdir(exist_ok=True)
    with historial.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    tasas = {k: v for k, v in datos.items() if v}
    texto = (f"banco={banco['nombre']}\n" + "".join(f"{k}={v}\n" for k, v in tasas.items())
             + f"actualizado={ahora}\norigen={origen}\n")
    (DOCS / f"{banco['id']}.txt").write_text(texto, encoding="utf-8")


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
    resumen = {}
    for b in BANCOS:
        d = leer_txt(DOCS / f"{b['id']}.txt")
        if d:
            resumen[b["id"]] = d
    bancos_json = json.dumps([{"id": b["id"], "nombre": b["nombre"]} for b in BANCOS], ensure_ascii=False)
    plantilla_path = Path("index.template.html")
    if plantilla_path.exists():
        plantilla = plantilla_path.read_text(encoding="utf-8")
        escribir_si_cambia(DOCS / "index.html", plantilla.replace("__BANKS__", bancos_json))
    escribir_si_cambia(DOCS / "todos.json",
                       json.dumps(resumen, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probar", nargs="?", const="todos", help="probar sin escribir (opcional: id de banco)")
    ap.add_argument("--manual", help="guardar una cotización manual para el ID indicado")
    ap.add_argument("--compra", default="", help="cotización de compra (Bs)")
    ap.add_argument("--venta", default="", help="cotización de venta (Bs)")
    ap.add_argument("--oficial", default="", help="cotización oficial (Bs)")
    args = ap.parse_args()
    DOCS.mkdir(exist_ok=True)

    if args.manual:
        banco = next((b for b in BANCOS if b["id"] == args.manual), None)
        if not banco:
            sys.exit(f"Banco desconocido: {args.manual}")
        datos = {}
        for campo in ("compra", "venta", "oficial"):
            entrada = getattr(args, campo).strip().replace(",", ".")
            if entrada:
                try:
                    valor = float(entrada)
                except ValueError:
                    sys.exit(f"Valor inválido para {campo}: {entrada}")
                if not MIN_OK <= valor <= MAX_OK:
                    sys.exit(f"El valor de {campo} debe estar entre {MIN_OK:g} y {MAX_OK:g} Bs")
                datos[campo] = fmt(valor)
            else:
                datos[campo] = ""
        if not any(datos.values()):
            sys.exit("Debes ingresar al menos una cotización")
        guardar_cotizacion(banco, datos, "manual")
        generar_indice()
        print(f"[OK] {banco['nombre']}: cotización manual agregada al historial")
        return

    bancos = BANCOS
    if args.probar and args.probar != "todos":
        bancos = [b for b in BANCOS if b["id"] == args.probar]
        if not bancos:
            sys.exit(f"Banco desconocido: {args.probar}")

    ok, fallos = 0, []
    for b in bancos:
        try:
            datos = extraer(descargar(b), b)
        except Exception as e:
            fallos.append(b["id"])
            print(f"[FALLO] {b['id']}: {e}")
            continue
        ok += 1
        print(f"[OK]    {b['id']}: compra={datos['compra'] or '—'} venta={datos['venta'] or '—'} oficial={datos['oficial'] or '—'}")
        if args.probar:
            continue
        guardar_cotizacion(b, datos, "automatico")

    if not args.probar:
        generar_indice()
    print(f"\nResumen: {ok} OK, {len(fallos)} con fallo {fallos if fallos else ''}")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
