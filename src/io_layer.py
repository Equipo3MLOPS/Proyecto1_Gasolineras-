"""Capa de I/O intercambiable para la arquitectura medallón.

Cada etapa del pipeline lee y escribe *datasets lógicos* (p.ej.
``"bronze.observaciones"``) a través de estas funciones, sin saber en qué
backend corre. El backend se elige con la variable de entorno
``PIPELINE_BACKEND`` (ver ``config.py``):

    local -> CSV en ``artifacts/`` (y SQLite en la etapa load). Comportamiento
             original del repo; corre en cualquier laptop sin Spark.
    uc    -> tablas Delta gobernadas por Unity Catalog
             (``spark...saveAsTable("workspace.bronze.observaciones")``).
    s3    -> tablas Delta escritas por ruta directa al bucket del equipo
             (``spark...save("s3a://cc3105-cusn-.../equipo3/bronze/...")``).

De esta forma, migrar de local a Databricks —o de UC a S3 directo— NO toca la
lógica de transformación: solo cambia una variable de entorno. Esto es
justamente lo que mantiene el código "de producción" y a la vez probable en
local.
"""
from __future__ import annotations

import pandas as pd

from . import config as C

_SPARK = None


def _spark():
    """Devuelve (y cachea) la SparkSession. Solo se usa en backends uc/s3."""
    global _SPARK
    if _SPARK is None:
        try:
            from pyspark.sql import SparkSession
        except ImportError as exc:  # pragma: no cover - solo fuera de Databricks
            raise RuntimeError(
                f"El backend '{C.BACKEND}' necesita pyspark/Databricks, pero no "
                "está disponible en este entorno. Usá PIPELINE_BACKEND=local para "
                "correr con CSV/SQLite."
            ) from exc
        _SPARK = SparkSession.builder.getOrCreate()
    return _SPARK


def read_df(dataset: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    """Lee un dataset lógico como ``pandas.DataFrame``, sea cual sea el backend."""
    if C.BACKEND == "local":
        return pd.read_csv(C.DATASETS[dataset]["csv"], parse_dates=parse_dates)

    if C.BACKEND == "uc":
        sdf = _spark().table(C.uc_table(dataset))
    else:  # s3
        sdf = _spark().read.format("delta").load(C.s3_path(dataset))

    pdf = sdf.toPandas()
    for col in parse_dates or []:
        if col in pdf.columns:
            pdf[col] = pd.to_datetime(pdf[col])
    return pdf


def write_df(df: pd.DataFrame, dataset: str) -> None:
    """Escribe un ``pandas.DataFrame`` al destino del dataset según el backend.

    En Spark replica el patrón ya probado en el notebook del workspace:
    ``mode("overwrite").option("overwriteSchema", "true")``.
    """
    if C.BACKEND == "local":
        path = C.DATASETS[dataset]["csv"]
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        return

    writer = (
        _spark()
        .createDataFrame(df)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
    )
    if C.BACKEND == "uc":
        writer.saveAsTable(C.uc_table(dataset))
    else:  # s3 directo: tabla Delta por ruta
        writer.format("delta").save(C.s3_path(dataset))


def target_name(dataset: str) -> str:
    """Destino legible del dataset, para imprimir en los logs del pipeline."""
    if C.BACKEND == "local":
        return str(C.DATASETS[dataset]["csv"])
    return C.uc_table(dataset) if C.BACKEND == "uc" else C.s3_path(dataset)
