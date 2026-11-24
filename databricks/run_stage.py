# Databricks notebook source
# MAGIC %md
# MAGIC # Runner de una etapa de la medallón
# MAGIC Ejecuta UNA etapa del pipeline (`bronce`, `plata`, `oro`, `modelo`)
# MAGIC leyendo/escribiendo en el backend configurado (`uc` o `s3`). Está pensado
# MAGIC para usarse como tarea de un Job (Asset Bundle): una etapa por tarea, de
# MAGIC modo que el DAG sea bronce → plata → oro (oro incluye el modelo y la predicción).
# MAGIC
# MAGIC La lógica vive en `src/` (el mismo código que corre en local); este
# MAGIC notebook solo elige el backend y llama a `run()`.

# COMMAND ----------

# MAGIC %pip install pillow-heif

# COMMAND ----------

# pillow-heif (lectura de .HEIC) no viene en el runtime serverless; tras
# instalarlo hay que reiniciar el intérprete de Python del notebook.
dbutils.library.restartPython()  # type: ignore[name-defined]

# COMMAND ----------

import os
import sys
from pathlib import Path


def _param(nombre: str, default: str) -> str:
    """Lee un parámetro del Job (widget) con un valor por defecto para correr a mano."""
    try:
        dbutils.widgets.text(nombre, default)   # type: ignore[name-defined]
        return dbutils.widgets.get(nombre)       # type: ignore[name-defined]
    except Exception:
        return default


stage = _param("stage", "bronce")
backend = _param("backend", "uc")
team = _param("team", "equipo3")
# Fracción de semanas recientes para la validación temporal del modelo.
test_fraccion = _param("test_fraccion", "0.3")
vision = _param("vision", "json")          # json | endpoint (lectura de precios en plata)
images_dir = _param("images_dir", "")      # ruta de las fotos para bronce (S3 o Volume)

# El backend se comunica a src/ vía variables de entorno (ver src/config.py).
os.environ["PIPELINE_BACKEND"] = backend
os.environ["PIPELINE_TEAM"] = team
os.environ["MODEL_TEST_FRACTION"] = test_fraccion
os.environ["PIPELINE_VISION"] = vision
if images_dir:
    os.environ["PIPELINE_IMAGES_DIR"] = images_dir

# Para llamar al endpoint de visión de Databricks desde src/vision.py:
if vision == "endpoint":
    try:
        _ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()  # type: ignore[name-defined]
        os.environ["DATABRICKS_TOKEN"] = _ctx.apiToken().get()
        os.environ["DATABRICKS_HOST"] = _ctx.apiUrl().get()
    except Exception as _e:
        print(f"[run_stage] no pude obtener token/host del contexto: {_e}")

# COMMAND ----------

# Hacer importable el paquete src/ que el bundle sincroniza junto a este notebook.
_raiz = Path.cwd().resolve()
while not (_raiz / "pyproject.toml").exists() and _raiz != _raiz.parent:
    _raiz = _raiz.parent
if str(_raiz) not in sys.path:
    sys.path.insert(0, str(_raiz))

from src import extract, transform, load, model  # noqa: E402


def _oro_y_prediccion():
    # Según el PDF, la tarea Oro recalcula las variables y genera la predicción
    # de la semana siguiente: primero las tablas Oro, luego el modelo.
    load.run()
    model.run()


ETAPAS = {
    "bronce": extract.run,
    "plata": transform.run,
    "oro": _oro_y_prediccion,
    "modelo": model.run,     # solo el modelo (sin recalcular Oro)
}

# COMMAND ----------

print(f"[run_stage] etapa={stage} | backend={backend} | team={team} | raiz={_raiz}")
if stage not in ETAPAS:
    raise ValueError(f"Etapa desconocida: {stage!r}. Válidas: {list(ETAPAS)}")

ETAPAS[stage]()
print(f"[run_stage] etapa '{stage}' completada.")
