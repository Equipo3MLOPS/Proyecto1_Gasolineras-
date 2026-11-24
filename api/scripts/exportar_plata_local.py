"""Exporta la capa Plata y las fotos a local (para probar /fotos con GOLD_MODE=local).

Complementa a `exportar_oro_local.py`: usa el mismo SQL Warehouse vía el CLI de
Databricks (perfil `uvg-mlops`) y SOLO LEE. Deja en `api/local_gold/`:

  silver_precios.parquet            una lectura por foto (fecha, precio, GPS…)
  silver_precios_rejected.parquet   fotos rechazadas por calidad
  fotos/IMG_xxxx.HEIC               foto original (desde bronze.fotos_precios)

    python api/scripts/exportar_oro_local.py      # tablas oro
    python api/scripts/exportar_plata_local.py    # plata + fotos (~170 MB)
    python api/scripts/exportar_plata_local.py --sin-fotos
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
from pathlib import Path

import pandas as pd

WAREHOUSE_ID = "aa1fd558f80e0607"
PROFILE = "uvg-mlops"
CATALOG = "workspace"
TABLAS = ["precios", "precios_rejected"]
OUT_DIR = Path(__file__).resolve().parent.parent / "local_gold"


def consultar(sql: str, parametros: list[dict] | None = None) -> pd.DataFrame:
    payload = {"warehouse_id": WAREHOUSE_ID, "statement": sql, "wait_timeout": "50s"}
    if parametros:
        payload["parameters"] = parametros
    out = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements",
         "-p", PROFILE, "--json", json.dumps(payload)],
        capture_output=True, text=True, check=True,
    ).stdout
    d = json.loads(out)
    if d.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(f"consulta falló: {d.get('status')}")
    cols = [c["name"] for c in d["manifest"]["schema"]["columns"]]
    return pd.DataFrame(d.get("result", {}).get("data_array", []), columns=cols)


def tipar(df: pd.DataFrame) -> pd.DataFrame:
    """El warehouse devuelve todo como texto; recupera numéricos (como en exportar_oro_local)."""
    for col in df.columns:
        conv = pd.to_numeric(df[col], errors="coerce")
        if conv.notna().any() and conv.notna().sum() >= df[col].notna().sum():
            df[col] = conv
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sin-fotos", action="store_true", help="exportar solo las tablas")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    origenes: set[str] = set()
    for tabla in TABLAS:
        df = tipar(consultar(f"SELECT * FROM {CATALOG}.silver.{tabla}"))
        df.to_parquet(OUT_DIR / f"silver_{tabla}.parquet", index=False)
        origenes |= set(df["foto_origen"].dropna())
        print(f"  silver.{tabla}: {len(df)} filas -> {OUT_DIR / f'silver_{tabla}.parquet'}")

    if not args.sin_fotos:
        carpeta = OUT_DIR / "fotos"
        carpeta.mkdir(exist_ok=True)
        for i, origen in enumerate(sorted(origenes), 1):
            destino = carpeta / origen.rsplit("/", 1)[-1]
            if destino.exists() and destino.stat().st_size > 0:
                continue
            # una foto por consulta: el resultado inline de la API tiene límite de tamaño
            df = consultar(
                f"SELECT content FROM {CATALOG}.bronze.fotos_precios "
                "WHERE _source_file = :origen LIMIT 1",
                [{"name": "origen", "value": origen, "type": "STRING"}],
            )
            if df.empty or df.iloc[0]["content"] is None:
                print(f"  [{i}/{len(origenes)}] sin binario en bronce: {origen}")
                continue
            destino.write_bytes(base64.b64decode(df.iloc[0]["content"]))
            print(f"  [{i}/{len(origenes)}] {destino.name}")
    print("Listo. Corré la API con GOLD_MODE=local.")


if __name__ == "__main__":
    main()
