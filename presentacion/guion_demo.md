# Guion de la presentación y la demo · Equipo 3

Formato del jurado: **20 minutos** = 10 de exposición + 5 de demo en vivo + 5 de preguntas. Hablan todos los
integrantes y el jurado puede preguntarle a cualquiera. El resumen de una página
(`presentacion/resumen_jurado.pdf`) se entrega **48 horas antes**.

## Reparto sugerido (ajústenlo entre ustedes)

P1 = Jose Santiago (Databricks), P2 = API, P3 = despliegue y repositorio, P4 = Hugo (informe y presentación). El
quinto integrante toma la diapositiva 10 y puede apoyar en la demo.

| Min | Diapositiva | Quién | Idea central |
|---|---|---|---|
| 0:00 | 1 · Portada | P4 | Presentar al equipo y la pregunta |
| 0:40 | 2 · Cada martes hay un precio nuevo | P4 | Para quién importa predecir el precio |
| 1:40 | 3 · De la foto a la respuesta | P3 | Bronce → Plata → Oro → API, sin jerga (se puede tocar cada caja) |
| 2:50 | 4 · De la foto al dato | P2 | Modelo de visión, precio efectivo y revisión manual |
| 3:50 | 5 · Tres reglas (interactiva) | P2 | Mostrar «Galones mal leídos» y volver a «Foto real» |
| 4:30 | 6 · La súper de Q28 a Q45 | P1 | Capa Oro: un precio por semana y combustible |
| 5:10 | 7 · La etiqueta (interactiva) | P1 | Mover el control: ±Q0.10 cuenta como «se mantiene» |
| 5:50 | 8 · Semanas que nunca vio | P1 | Validación temporal: 71 para entrenar, 28 para probar |
| 6:30 | 9 · Un acierto más | P1 | Resultado honesto; «siempre sube» gana; matriz si preguntan |
| 7:40 | 10 · Los datos ponen el techo | Quinto integrante | Limitaciones |
| 8:40 | 11 · Corre solo cada martes | P1 | Job, programación, alerta, serverless, MLflow |
| 9:40 | 12 · Demo en vivo | P2 y P3 | Ver la sección «Demo» |
| 14:40 | 13 · Lo que aprendimos | P4 | Lecciones y qué haríamos con más tiempo |
| 15:00 | 14 · Preguntas | Todos | El anexo (diapositiva 15) tiene el diagrama técnico completo |

## Antes de entrar (checklist del día)

- [ ] El Job de producción existe y está compartido con el catedrático (`databricks bundle deploy -t prod`).
- [ ] Las fotos de la semana nueva ya están en `s3://cc3105-raw-…/img/`.
- [x] La API responde desde fuera: `curl http://165.22.137.8:8003/health` devuelve `"status": "ok"` (verificado el 24 de noviembre).
- [ ] El QR de la diapositiva 12 abre la página de la API (precios, predicciones e histórico) en un teléfono con datos móviles (no con el Wi-Fi de la UVG).
- [ ] Pestañas abiertas: Job en Databricks, `workspace.gold.predicciones` en Catalog y `http://165.22.137.8:8003/docs`.
- [ ] El video y las capturas del plan B están en la laptop, no solo en la nube.

## Demo en vivo (5 minutos)

1. **Ejecutar el Job (1:30).** En Databricks → Jobs & Pipelines → «Medallón Gasolineras — equipo3» → **Run now**.
   Mostrar que las tareas bronce → plata → oro se encadenan. Mientras corre, explicar en una frase qué hace cada
   una. Si tarda más de lo previsto, seguir con el paso 2 sobre la corrida anterior y volver al final.
2. **Ver la capa Oro (1:00).** Catalog → `workspace.gold.predicciones` → Sample Data: filas `tipo = futura`, una
   por combustible, con la semana, la dirección y la probabilidad. Mostrar la pestaña **Lineage** de la tabla
   (bronce → plata → oro).
3. **Consultar la API (2:00).** Pedirle al jurado que escanee el QR. En la laptop:

   ```bash
   BASE_URL=http://165.22.137.8:8003 api/tests/consultas_api.sh
   ```

   Destacar `/prediccion?combustible=super` (semana, dirección y probabilidad) y `/modelo/metricas` (modelo
   contra línea base). Abrir `/docs` para enseñar la documentación automática.
4. **Cerrar (0:30).** «Cada martes esto corre solo; si algo falla, nos llega un correo».

## Plan B (si falla la conexión o el Job)

Ya están listos: `presentacion/planb_respuestas.txt` (respuestas reales de todos los endpoints, 24 de noviembre),
`presentacion/capturas/api_docs.jpg` y `presentacion/qr_prediccion.png`. El día anterior, repetir con datos frescos:

```bash
# respuestas reales de la API, para mostrarlas sin conexión
BASE_URL=http://165.22.137.8:8003 api/tests/consultas_api.sh | tee presentacion/planb_respuestas.txt
```

- Capturas: historial de corridas del Job con la duración de cada tarea (sirven también para el informe),
  `gold.predicciones` en Catalog y `/docs` de la API.
- Video corto (1 a 2 minutos) de la demo completa grabado con la herramienta de grabación de pantalla del sistema.
- Si cae la API durante la demo, mostrar el video; si cae el Job, mostrar la corrida exitosa más reciente.

## La presentación y el QR

La presentación es una página web: `presentacion/presentacion_jurado.html` (se abre con doble clic, sin internet).
Teclas: ← → para avanzar, **F** pantalla completa, **O** índice, **N** notas del orador con el tiempo y quién habla.
Las diapositivas 5, 6, 7, 9 y 11 son interactivas. `presentacion_jurado.pdf` es la misma presentación sin animaciones
(plan B si falla la laptop).

La versión actual ya trae el QR al servidor 165.22.137.8 y el 45.0 % de la revisión. Si cambia la IP, se regenera así:

```bash
cd presentacion/web
npm install
VITE_API_URL=http://165.22.137.8:8003 npm run build
cp dist/index.html ../presentacion_jurado.html
```

Para el resumen de una página, el QR como imagen:

```bash
pip install qrcode
python -c "import qrcode; qrcode.make('http://165.22.137.8:8003/').save('presentacion/qr_prediccion.png')"
```

## Preguntas probables del jurado

- **¿Por qué no supera a «siempre sube»?** En las 28 semanas de prueba el precio subió 16 veces; con tan pocos
  datos, la regla trivial es difícil de vencer. Lo decimos abiertamente y explicamos qué datos faltan.
- **¿Qué tan confiable es la lectura de las fotos?** 95.4 % pasa las reglas. En la revisión a mano de 20 fotos,
  9 no tenían ningún error (45 %): los montos se leen bien (18 de 20), pero en 10 fotos de súper el combustible quedó
  mal asignado. El precio es correcto, solo cae en la serie de otro combustible; es la primera mejora pendiente.
- **¿Cuánto cuesta operarlo?** Serverless solo cobra mientras corre el Job (minutos por semana) y la API usa un
  SQL Warehouse 2X-Small que se apaga solo.
- **¿Qué harían con más tiempo?** Los cuatro precios de cada foto, el precio del petróleo y una serie por semanas
  calendario.
