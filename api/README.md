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
| GET | `/docs` | Documentación Swagger (automática) |

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
