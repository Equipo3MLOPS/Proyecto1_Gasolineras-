# API de precios y predicción — equipo3

API REST (FastAPI) que sirve la **capa Oro** por HTTP. No corre el modelo: el
modelo vive en Databricks y deja sus resultados en `gold.predicciones` /
`gold.metricas_modelo`; esta API solo los lee.

## De dónde lee los datos (`GOLD_MODE`)
| Modo | Lee de | Credencial | Uso |
|---|---|---|---|
| **`databricks`** | SQL Warehouse de Databricks (Unity Catalog) | **token (PAT) del usuario** | **el que usamos en el Droplet** |
| `s3` | Delta del bucket oro directo (`deltalake`) | credenciales S3 de solo lectura | si el bucket es accesible desde el server |
| `local` | parquet en `local_gold/` | ninguna | desarrollo/pruebas |

> Se usa el modo **databricks** porque el usuario del Droplet no tiene permiso de
> lectura sobre el bucket S3 de oro; Databricks sí lo lee (vía Unity Catalog), así
> que la API le pide los datos a Databricks con un token propio del equipo.

## Arquitectura
```
Databricks (modelo) ─► S3 oro (gold.*)           la API NO toca S3:
        ▲                                         le pide el oro a Databricks
        └──── SQL Warehouse ◄── API (Droplet, Docker) ──HTTP──► cliente
                 (token PAT)
```

## Endpoints
| Método | Ruta | Qué devuelve |
|---|---|---|
| GET | `/health` | Estado del servicio y si puede leer la capa oro |
| GET | `/precios/actual` | Último precio promedio por combustible |
| GET | `/precios?combustible=&desde=&hasta=&limit=` | Histórico semanal con filtros |
| GET | `/prediccion?combustible=` | Predicción de la semana siguiente |
| GET | `/modelo/metricas` | Exactitud del modelo elegido vs. línea base |
| GET | `/fotos?combustible=&desde=&hasta=&ubicacion=&incluir_rechazadas=&limit=` | Una lectura por foto (capa **plata**): fecha, precio, total, galones y GPS de la gasolinera |
| GET | `/fotos/{image_id}/imagen` | Miniatura JPEG de la foto (sin EXIF), cacheada en disco |
| GET | `/presentacion` | Presentación del jurado (copia de `presentacion/presentacion_jurado.html` en `app/static/presentacion.html`; al regenerarla hay que copiarla a ambos lados) |
| GET | `/docs` | Documentación Swagger (automática) |

### Mapa de fotos (endpoints `/fotos`)
El dashboard (`/`) incluye un mapa con la gasolinera donde se tomó cada foto.
Estos endpoints son **nuevos y aislados** (`app/fotos.py`): no cambian los
endpoints de arriba, que usa el modelo.
- Leen `silver.precios` y `silver.precios_rejected` con el mismo `GOLD_MODE`.
- El GPS sale del id de estación (`ST_14p560_m90p463` → 14.560, -90.463),
  redondeado a 3 decimales (~110 m): ubica la gasolinera, no la foto exacta.
- La miniatura se arma desde el binario de `bronze.fotos_precios` (modo
  `databricks`, con el mismo token; no necesita S3), se convierte de HEIC a
  JPEG **sin metadatos** y se guarda en `FOTOS_CACHE_DIR` (por defecto
  `/tmp/fotos_cache`). La primera vez tarda ~4 s por foto; luego es inmediata.

## Lo único que hay que conseguir: un token de Databricks
El modo `databricks` necesita un **Personal Access Token (PAT)** del usuario:
Databricks → **Settings → Developer → Access tokens → Generate new token**.
Es un secreto: va solo en el `.env` del server, nunca en el repo. No depende del
profe (lo genera el equipo).

## Despliegue en el Droplet (lo hace quien tiene la llave SSH)
```bash
git clone <url-del-repo>        # o: cd <repo> && git pull
cd <repo>/api
cp .env.example .env            # editar: GOLD_MODE=databricks y pegar DATABRICKS_TOKEN=<tu PAT>
docker compose up -d --build    # queda corriendo aunque se cierre el SSH
curl http://localhost:8003/health   # debe responder "status":"ok"
```
La API escucha en `API_PORT` (equipo3 → 8003). Desde fuera: `curl http://<ip>:8003/health`.

## Entorno aislado: por qué Docker
El Droplet es compartido entre equipos; **Docker** aísla dependencias y versiones
sin tocar el sistema, y deja el servicio igual en local y en el server. Dentro de
la imagen se usa **uv** para instalar rápido y de forma reproducible.

## Desarrollo / prueba local (sin token ni credenciales)
Con `GOLD_MODE=local` la API lee parquet de `local_gold/`. Para generarlos:
```bash
python scripts/exportar_oro_local.py     # baja las tablas oro desde Databricks
python scripts/exportar_plata_local.py   # plata + fotos para /fotos (--sin-fotos: solo tablas)
cd api && uv venv && source .venv/bin/activate && uv pip install -r requirements.txt
GOLD_MODE=local uvicorn app.main:app --port 8003
./tests/consultas_api.sh
```

## Cliente de prueba
`tests/consultas_api.sh` consume todos los endpoints (local o contra el Droplet):
```bash
BASE_URL=http://<ip>:8003 ./tests/consultas_api.sh
```

## Seguridad
- El `DATABRICKS_TOKEN` (y cualquier credencial) va **solo** en el `.env` del
  server, **nunca** en el repo (`.env` está en `.gitignore`).
