# Tipo de cambio de los bancos de Bolivia (GitHub Actions + GitHub Pages)

Cada 30 minutos, GitHub Actions consulta la web de cada banco, extrae compra/venta
del dólar y guarda un archivo de texto por banco en `docs/`. GitHub Pages publica esa carpeta.

    docs/bcp.txt        docs/bnb.txt   ...   docs/todos.json   docs/index.html

Formato de cada .txt:

    banco=Banco de Crédito (BCP)
    compra=6.96
    venta=6.86
    actualizado=2026-09-28 11:00 (hora Bolivia)

`actualizado` indica el último momento en que CAMBIARON los valores (si no cambian,
no se toca el archivo ni se hace commit).

## Instrucciones

1. Crea un repositorio PÚBLICO en GitHub (ej. `tipo-cambio-bolivia`), vacío (sin README).
2. Descomprime este ZIP y, dentro de la carpeta, ejecuta:

       git init -b main
       git add .
       git commit -m "Primer commit"
       git remote add origin https://github.com/TU_USUARIO/tipo-cambio-bolivia.git
       git push -u origin main

   (No uses "arrastrar y soltar" en la web: suele omitir la carpeta oculta `.github`.)
3. En GitHub: Settings > Actions > General > Workflow permissions >
   marca "Read and write permissions" > Save.
4. Settings > Pages > Source: "Deploy from a branch" > Branch: `main`, carpeta `/docs` > Save.
5. Pestaña Actions > "Actualizar tipo de cambio" > Run workflow (primera ejecución manual).
6. Tus URLs (tras 1-2 minutos):

       https://TU_USUARIO.github.io/tipo-cambio-bolivia/            (tabla resumen)
       https://TU_USUARIO.github.io/tipo-cambio-bolivia/bcp.txt     (un banco)
       https://TU_USUARIO.github.io/tipo-cambio-bolivia/todos.json  (todos juntos)

7. Ajustar bancos que fallen (esperable en algunos):

       pip install -r requirements.txt
       python actualizar.py --probar          # prueba todos, sin escribir
       python actualizar.py --probar bnb      # prueba uno

   Si un banco falla, abre `bancos.py` y:
   - corrige `url` a la página exacta donde muestra el tipo de cambio;
   - o agrega `regex_compra` / `regex_venta` (un grupo de captura con el número,
     aplicado al texto visible de la página);
   - si la cifra se carga con JavaScript, agrega `"modo": "playwright"` y descomenta
     el paso "Instalar Playwright" en `.github/workflows/actualizar.yml`
     (localmente: `pip install playwright && playwright install chromium`);
   - si da error de certificado: `"ssl_verify": False`.
   Los bancos que fallan no rompen a los demás: conservan su último valor.
   Si quieres quitar un banco, borra su línea en `bancos.py`.

## Notas
- GitHub puede retrasar los cron varios minutos; 5 min es el mínimo posible.
- Los archivos de GitHub Pages permiten CORS, así que puedes leer los .txt con `fetch()` desde otra web.
- Si Pages no se actualiza, revisa Actions > "pages-build-deployment".
- Respeta los términos de uso de cada sitio; 30 min entre consultas es un ritmo prudente.
