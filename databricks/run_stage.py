# Databricks notebook source
# MAGIC %md
# MAGIC # Runner de una etapa de la medallón
# MAGIC Ejecuta UNA etapa del pipeline (`extract`, `transform`, `load`, `model`)
# MAGIC leyendo/escribiendo en el backend configurado (`uc` o `s3`). Está pensado
# MAGIC para usarse como tarea de un Job (Asset Bundle): una etapa por tarea, de
# MAGIC modo que el DAG sea extract → transform → load → model.
# MAGIC
# MAGIC La lógica vive en `src/` (el mismo código que corre en local); este
# MAGIC notebook solo elige el backend y llama a `run()`.

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


stage = _param("stage", "extract")
backend = _param("backend", "uc")
team = _param("team", "equipo3")

# El backend se comunica a src/ vía variables de entorno (ver src/config.py).
os.environ["PIPELINE_BACKEND"] = backend
os.environ["PIPELINE_TEAM"] = team

# COMMAND ----------

# Hacer importable el paquete src/ que el bundle sincroniza junto a este notebook.
_raiz = Path.cwd().resolve()
while not (_raiz / "pyproject.toml").exists() and _raiz != _raiz.parent:
    _raiz = _raiz.parent
if str(_raiz) not in sys.path:
    sys.path.insert(0, str(_raiz))

from src import extract, transform, load, model  # noqa: E402

ETAPAS = {
    "extract": extract.run,
    "transform": transform.run,
    "load": load.run,
    "model": model.run,
}

# COMMAND ----------

print(f"[run_stage] etapa={stage} | backend={backend} | team={team} | raiz={_raiz}")
if stage not in ETAPAS:
    raise ValueError(f"Etapa desconocida: {stage!r}. Válidas: {list(ETAPAS)}")

ETAPAS[stage]()
print(f"[run_stage] etapa '{stage}' completada.")
