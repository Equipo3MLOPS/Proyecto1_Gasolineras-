"""Exporta las tablas Oro de Databricks a parquet local (para GOLD_MODE=local).

Usa el SQL Warehouse vía el CLI de Databricks (perfil `uvg-mlops`), así que no
necesita credenciales S3. Solo para desarrollo/pruebas de la API.

    python api/scripts/exportar_oro_local.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd

WAREHOUSE_ID = "aa1fd558f80e0607"
PROFILE = "uvg-mlops"
CATALOG_SCHEMA = "workspace.gold"
TABLAS = ["precio_semanal", "variacion_semanal", "features_modelo",
          "predicciones", "metricas_modelo"]
OUT_DIR = Path(__file__).resolve().parent.parent / "local_gold"


def consultar(sql: str) -> pd.DataFrame:
    payload = {"warehouse_id": WAREHOUSE_ID, "statement": sql, "wait_timeout": "50s"}
    out = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements",
         "-p", PROFILE, "--json", json.dumps(payload)],
        capture_output=True, text=True, check=True,
    ).stdout
    d = json.loads(out)
    if d.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(f"consulta falló: {d.get('status')}")
    cols = [c["name"] for c in d["manifest"]["schema"]["columns"]]
    data = d.get("result", {}).get("data_array", [])
    return pd.DataFrame(data, columns=cols)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for tabla in TABLAS:
        df = consultar(f"SELECT * FROM {CATALOG_SCHEMA}.{tabla}")
        # el warehouse devuelve todo como texto; recuperar tipos como en S3/Delta.
        for col in df.columns:
            bajo = df[col].astype(str).str.lower()
            no_nulos = bajo[~bajo.isin(["none", "nan", ""])]
            if len(no_nulos) and no_nulos.isin(["true", "false"]).all():
                df[col] = bajo.map({"true": True, "false": False})  # booleano
                continue
            conv = pd.to_numeric(df[col], errors="coerce")
            if conv.notna().any() and conv.notna().sum() >= df[col].notna().sum():
                df[col] = conv
        df.to_parquet(OUT_DIR / f"{tabla}.parquet", index=False)
        print(f"  {tabla}: {len(df)} filas -> {OUT_DIR / f'{tabla}.parquet'}")
    print("Listo. Corré la API con GOLD_MODE=local.")


if __name__ == "__main__":
    main()
