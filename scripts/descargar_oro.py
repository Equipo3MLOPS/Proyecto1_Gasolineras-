"""Descarga las tablas de la capa Oro (S3 del equipo) a artifacts/gold/*.csv.

Sirve para correr el modelo en local con los datos reales:
    python scripts/descargar_oro.py
    PIPELINE_BACKEND=local python -m src.pipeline modelo

Lee por el SQL warehouse de Databricks con el perfil del CLI
(`databricks auth login ... --profile uvg-mlops`). Solo hace lecturas.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
from databricks.sdk import WorkspaceClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("PIPELINE_BACKEND", "local")
from src import config as C  # noqa: E402

TABLAS = ["precio_semanal", "variacion_semanal", "features_modelo"]
NUMERICOS = {"DOUBLE", "FLOAT", "DECIMAL", "INT", "LONG", "BIGINT", "SHORT", "BYTE"}


def consultar(w: WorkspaceClient, warehouse: str, sql: str) -> pd.DataFrame:
    r = w.statement_execution.execute_statement(warehouse_id=warehouse, statement=sql, wait_timeout="30s")
    while r.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(3)  # el warehouse serverless puede estar arrancando
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state.value != "SUCCEEDED":
        raise RuntimeError(f"Falló la consulta: {r.status.error.message if r.status.error else r.status.state}")
    cols = r.manifest.schema.columns
    df = pd.DataFrame(r.result.data_array or [], columns=[c.name for c in cols])
    for c in cols:
        if c.type_name.value in NUMERICOS:
            df[c.name] = pd.to_numeric(df[c.name])
    return df


def main() -> None:
    w = WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "uvg-mlops"))
    warehouse = os.environ.get("DATABRICKS_WAREHOUSE_ID") or next(iter(w.warehouses.list())).id
    base = f"s3://{C.S3_BUCKETS['gold']}/{C.TEAM}/gold"
    C.GOLD_DIR.mkdir(parents=True, exist_ok=True)
    for t in TABLAS:
        df = consultar(w, warehouse, f"SELECT * FROM delta.`{base}/{t}`")
        destino = C.DATASETS[f"gold.{t}"]["csv"]
        df.to_csv(destino, index=False)
        print(f"[oro] {t}: {len(df)} filas -> {destino}")


if __name__ == "__main__":
    main()
