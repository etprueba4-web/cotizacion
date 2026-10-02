"""
Lista de bancos de Bolivia.

Campos:
  id            -> nombre del archivo de salida (docs/<id>.txt)
  nombre        -> nombre para mostrar
  url           -> página donde el banco publica su tipo de cambio
Opcionales:
  regex_compra  -> regex propia (con 1 grupo) aplicada al TEXTO visible de la página
  regex_venta   -> idem para venta
  modo          -> "playwright" si la página carga los datos con JavaScript
  ssl_verify    -> False si el certificado del banco da error
  
Si no pones regex, se usa una búsqueda genérica ("compra ... 6.96", "venta ... 6.86").
Ajusta las URLs/regex de los bancos que fallen (ver README, paso 7).
"""

BANCOS = [
    {"id": "bcb",         "nombre": "Banco Central de Bolivia",     "url": "https://www.bcb.gob.bo/"},  
    {"id": "bcp",         "nombre": "Banco de Crédito (BCP)",       "url": "https://www.bcp.com.bo/"},
    {"id": "bnb",         "nombre": "Banco Nacional de Bolivia",    "url": "https://www.bnb.com.bo/"},
    {"id": "union",       "nombre": "Banco Unión",                  "url": "https://www.bancounion.com.bo/"},
    {"id": "bmsc",        "nombre": "Banco Mercantil Santa Cruz",   "url": "https://www.bmsc.com.bo/"},
    {"id": "bisa",        "nombre": "Banco BISA",                   "url": "https://www.bisa.com/"},
    {"id": "ganadero",    "nombre": "Banco Ganadero",               "url": "https://www.bg.com.bo/"},
    {"id": "economico",   "nombre": "Banco Económico",              "url": "https://www.baneco.com.bo/"},
    {"id": "fassil",      "nombre": "Banco Fassil",                 "url": "https://www.bancofassil.com.bo/"},
    {"id": "bancosol",    "nombre": "BancoSol",                     "url": "https://www.bancosol.com.bo/"},
    {"id": "prodem",      "nombre": "Banco Prodem",                 "url": "https://www.prodem.com.bo/"},
    {"id": "fortaleza",   "nombre": "Banco Fortaleza",              "url": "https://www.bancofortaleza.com.bo/"},
    {"id": "ecofuturo",   "nombre": "Banco Ecofuturo",              "url": "https://www.bancoecofuturo.com.bo/"},
    {"id": "fie",         "nombre": "Banco FIE",                    "url": "https://www.bancofie.com.bo/"},
    {"id": "bancomunidad","nombre": "Bancomunidad",                 "url": "https://www.bancomunidad.com.bo/"},
]
