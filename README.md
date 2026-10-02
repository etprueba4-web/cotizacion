# Tipo de cambio de los bancos de Bolivia (GitHub Actions + GitHub Pages)

Cada 30 minutos, GitHub Actions consulta la web de cada banco y guarda la cotización actual
en `docs/`. Cada consulta exitosa también se agrega al historial JSONL del banco.

    docs/bcp.txt        docs/bnb.txt   ...   docs/historial/bcp.jsonl
    docs/todos.json     docs/index.html

Formato de cada archivo actual `.txt`:

    banco=Banco de Crédito (BCP)
    compra=11.40
    venta=12.20
    oficial=11.90
    actualizado=2026-09-28 11:00 (hora Bolivia)

Los campos que la página no publica se dejan vacíos en el archivo actual y como `null`
en el historial. El historial agrega una línea JSON por consulta, con fecha ISO 8601
y zona horaria de Bolivia; no se reemplazan entradas anteriores.

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
       playwright install chromium
       python actualizar.py --probar          # prueba todos, sin escribir
       python actualizar.py --probar bnb      # prueba uno

   Si un banco falla, abre `bancos.py` y:
   - corrige `url` a la página exacta donde muestra el tipo de cambio;
   - o agrega `regex_compra` / `regex_venta` (un grupo de captura con el número,
     aplicado al texto visible de la página);
   - si la cifra se carga con JavaScript, agrega `"modo": "playwright"`.
   - si da error de certificado: `"ssl_verify": False`.
   Los bancos que fallan no rompen a los demás: conservan su último valor.
   Si quieres quitar un banco, borra su línea en `bancos.py`.

## Actualización manual desde el índice

En `index.html`, el formulario “Actualizar manualmente” envía los valores al workflow
`.github/workflows/actualizacion-manual.yml`. Ingresa el usuario/organización, el nombre
del repositorio y un token fine-grained de GitHub limitado a ese repositorio con permiso
`Actions: Read and write`. El token solo permanece en memoria durante el envío y se borra
del campo después de enviarlo. El workflow agrega un registro al historial y actualiza
el resumen publicado. La página de GitHub Pages puede tardar un poco en reflejar el cambio.

## Notas
- GitHub puede retrasar los cron varios minutos; 5 min es el mínimo posible.
- Los archivos de GitHub Pages permiten CORS, así que puedes leer los .txt con `fetch()` desde otra web.
- El historial se publica en `historial/<id>.jsonl`; cada línea contiene banco, fecha de consulta,
  compra, venta y oficial cuando la página los publica.
- Si Pages no se actualiza, revisa Actions > "pages-build-deployment".
- Respeta los términos de uso de cada sitio; 30 min entre consultas es un ritmo prudente.
