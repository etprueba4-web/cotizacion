"""
Lista de bancos de Bolivia.

Campos:
  id            -> nombre del archivo de salida (docs/<id>.txt)
  nombre        -> nombre para mostrar
  url           -> página donde el banco publica su tipo de cambio
Opcionales:
  regex_compra, regex_venta, regex_oficial -> regex propia (un grupo) sobre texto visible
  modo          -> "playwright" si la página carga los datos con JavaScript
  ssl_verify    -> False si el certificado del banco da error
  
Si no pones regex, se usa una búsqueda genérica ("compra ... 6.96", "venta ... 6.86").
Ajusta las URLs/regex de los bancos que fallen (ver README, paso 7).
"""

BANCOS = [
    {"id": "bcb", "nombre": "Banco Central de Bolivia", "url": "https://www.bcb.gob.bo/",
     "regex_oficial": r"bcb-tco-num[^>]*>\s*([\d.,]+)"},
    {"id": "bcp", "nombre": "Banco de Crédito (BCP)", "url": "https://www.bcp.com.bo/", "modo": "playwright",
     "regex_compra": r"Dólar\s+Compra:\s*([\d.,]+)", "regex_venta": r"Dólar\s+Venta:\s*([\d.,]+)"},
    {"id": "bnb", "nombre": "Banco Nacional de Bolivia", "url": "https://www.bnb.com.bo/PortalBNB/Principal/BancaPersonas", "modo": "playwright", "extractor": "bnb"},
    {"id": "union", "nombre": "Banco Unión", "url": "https://www.bancounion.com.bo/",
     "regex_oficial": r"Dólar Oficial\s+([\d.,]+)", "regex_compra": r"Compra BOB:\s*([\d.,]+)", "regex_venta": r"Venta\s+([\d.,]+)"},
    {"id": "bmsc", "nombre": "Banco Mercantil Santa Cruz", "url": "https://www.bmsc.com.bo/", "modo": "playwright",
     "regex_compra": r"Compra:\s*([\d.,]+)", "regex_venta": r"Venta:\s*([\d.,]+)", "regex_oficial": r"Oficial:\s*([\d.,]+)"},
    {"id": "bisa", "nombre": "Banco BISA", "url": "https://www.bisa.com/",
     "regex_compra": r"Dólar Compra\s*([\d.,]+)", "regex_venta": r"Dólar Venta\s*([\d.,]+)"},
    {"id": "ganadero", "nombre": "Banco Ganadero", "url": "https://www.bg.com.bo/",
     "regex_venta": r"Valor Ref\. Venta USD\s*([\d.,]+)"},
    {"id": "economico", "nombre": "Banco Económico", "url": "https://baneco.com.bo/", "modo": "playwright",
     "regex_oficial": r"Tipo de Cambio oficial del BCB:\s*Bs\.\s*([\d.,]+)",
     "regex_compra": r"Compra:\s*([\d.,]+)", "regex_venta": r"Venta:\s*([\d.,]+)"},
    {"id": "bancosol", "nombre": "BancoSol", "url": "https://www.bancosol.com.bo/",
     "regex_oficial": r"Tipo de cambio oficial Boliviano por Dólar estadounidense\s*:\s*([\d.,]+)",
     "regex_compra": r"Tipo de cambio compra\s*:\s*([\d.,]+)", "regex_venta": r"Tipo de cambio venta\s*:\s*([\d.,]+)"},
    {"id": "prodem", "nombre": "Banco Prodem", "url": "https://prodem.bo/Inicio", "modo": "playwright",
     "extractor": "prodem", "cerrar_modal": True, "espera_selector": "#prodem-compra"},
    {"id": "fortaleza", "nombre": "Banco Fortaleza", "url": "https://www.bancofortaleza.com.bo/", "modo": "playwright",
     "regex_oficial": r"data-exchange=\"officialExchange\"[^>]*>\s*([\d.,]+)",
     "regex_compra": r"data-exchange=\"buyExchange\"[^>]*>\s*([\d.,]+)", "regex_venta": r"data-exchange=\"saleExchange\"[^>]*>\s*([\d.,]+)"},
    {"id": "ecofuturo", "nombre": "Banco Ecofuturo", "url": "https://www.bancoecofuturo.com.bo/",
     "regex_oficial": r"Oficial\s+Bs\s*([\d.,]+)", "regex_compra": r"Compra\s+Bs\s*([\d.,]+)", "regex_venta": r"Venta\s+Bs\s*([\d.,]+)"},
    {"id": "fie", "nombre": "Banco FIE", "url": "https://www.bancofie.com.bo/", "modo": "playwright",
     "regex_oficial": r"Dólar Oficial:\s*([\d.,]+)", "regex_compra": r"Dólar Compra:\s*([\d.,]+)", "regex_venta": r"Dólar Venta:\s*([\d.,]+)"},
    {"id": "bancomunidad", "nombre": "Bancomunidad", "url": "https://www.bco.com.bo/", "extractor": "bancomunidad"},
]
