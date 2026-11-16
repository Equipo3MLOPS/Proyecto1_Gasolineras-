
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
        except ImportError as exc:  
            raise RuntimeError(
                f"El backend '{C.BACKEND}' necesita pyspark/Databricks, pero no "
                "está disponible en este entorno. "
            ) from exc
        _SPARK = SparkSession.builder.getOrCreate()
    return _SPARK


def read_df(dataset: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
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
    else:  
        writer.format("delta").save(C.s3_path(dataset))


def target_name(dataset: str) -> str:
    if C.BACKEND == "local":
        return str(C.DATASETS[dataset]["csv"])
    return C.uc_table(dataset) if C.BACKEND == "uc" else C.s3_path(dataset)
