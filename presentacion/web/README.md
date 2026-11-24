# Presentación del jurado (página web)

Código de `presentacion/presentacion_jurado.html`: React + GSAP, empaquetado por Vite en un solo archivo HTML.
Diseño: el rótulo de precios de una gasolinera de noche (paleta y reglas al inicio de `src/styles.css`)
(fuentes, imágenes y datos incluidos, funciona sin internet).

```bash
npm install
npm run dev                      # vista previa con recarga en http://localhost:5173
VITE_API_URL=http://165.22.137.8:8003 VITE_REVISION=<porcentaje> npm run build
cp dist/index.html ../presentacion_jurado.html
cp dist/index.html ../../api/app/static/presentacion.html   # la sirve la API en /presentacion
```

- `VITE_API_URL` dibuja el QR a `/prediccion?combustible=super` en las diapositivas 12 y 14 y la URL de `/docs`.
- `VITE_REVISION` cambia el % de la revisión manual (por defecto 45.0, diapositiva 4; el detalle está en `REV` de `src/data.js`).
- Datos: `src/data.js` (métricas, matriz de confusión, predicción) y `src/serie.json` (`gold.precio_semanal`).
- Diapositivas: `src/slides/a.jsx` (1–5), `b.jsx` (6–10), `c.jsx` (11–15); notas del orador en `src/slides/notas.js`, archivo local que no se sube al repositorio (sin él, la presentación sale sin notas; `VITE_SIN_NOTAS=1` también las quita).
- PDF sin animaciones: abrir la página con `#imprimir` al final de la URL e imprimir a PDF (tamaño 1600 × 900 px).
