"""Lector de la capa Oro.

Lee las tablas Delta de oro desde S3 (con la librería `deltalake`, sin Spark) o,
en modo local, desde parquet. Cachea en memoria unos segundos para no golpear S3
en cada request. La API solo LEE; nunca escribe.
"""
from __future__ import annotations

import os
import time

import pandas as pd

from .config import settings

TABLAS = [
    "precio_semanal", "variacion_semanal", "features_modelo",
    "predicciones", "metricas_modelo",
]

_cache: dict[str, tuple[float, pd.DataFrame]] = {}


def _s3_uri(tabla: str) -> str:
    return f"s3://{settings.gold_bucket}/{settings.team}/gold/{tabla}"


def _storage_options() -> dict:
    """Credenciales para leer S3.

    - Si el .env trae llaves explícitas, se usan.
    - Si no, se toman las credenciales AMBIENTALES del servidor (variables de
      entorno o ~/.aws/credentials que el profe ya dejó configuradas en el
      Droplet). Así normalmente NO hace falta poner llaves en el .env.
    """
    opts = {"AWS_REGION": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        opts["AWS_ACCESS_KEY_ID"] = settings.aws_access_key_id
        opts["AWS_SECRET_ACCESS_KEY"] = settings.aws_secret_access_key
        return opts
    try:  # resolver la cadena de credenciales del sistema (env, perfil, rol)
        import boto3

        cred = boto3.Session().get_credentials()
        if cred:
            fr = cred.get_frozen_credentials()
            opts["AWS_ACCESS_KEY_ID"] = fr.access_key
            opts["AWS_SECRET_ACCESS_KEY"] = fr.secret_key
            if fr.token:
                opts["AWS_SESSION_TOKEN"] = fr.token
    except Exception:
        pass  # dejar que deltalake intente su propia cadena de credenciales
    return opts


def _leer_s3(tabla: str) -> pd.DataFrame:
    from deltalake import DeltaTable

    return DeltaTable(_s3_uri(tabla), storage_options=_storage_options()).to_pandas()


def _leer_local(tabla: str) -> pd.DataFrame:
    ruta = os.path.join(settings.local_gold_dir, f"{tabla}.parquet")
    return pd.read_parquet(ruta)


def _coerce_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """El SQL API devuelve todo como texto; recupera booleanos y numéricos."""
    for col in df.columns:
        bajo = df[col].astype(str).str.lower()
        no_nulos = bajo[~bajo.isin(["none", "nan", ""])]
        if len(no_nulos) and no_nulos.isin(["true", "false"]).all():
            df[col] = bajo.map({"true": True, "false": False})
            continue
        conv = pd.to_numeric(df[col], errors="coerce")
        if conv.notna().any() and conv.notna().sum() >= df[col].notna().sum():
            df[col] = conv
    return df


def _leer_databricks(tabla: str) -> pd.DataFrame:
    """Lee la tabla oro vía el SQL Statement Execution API de Databricks.

    Usa un token (PAT) del usuario; no toca S3 directamente (Databricks lee el
    oro por Unity Catalog). Pensado para cuando el bucket S3 no es accesible
    desde el Droplet.
    """
    import requests

    url = f"{settings.databricks_host.rstrip('/')}/api/2.0/sql/statements"
    payload = {
        "warehouse_id": settings.databricks_warehouse_id,
        "statement": f"SELECT * FROM {settings.uc_catalog}.gold.{tabla}",
        "wait_timeout": "50s",
    }
    r = requests.post(url, headers={"Authorization": f"Bearer {settings.databricks_token}"},
                      json=payload, timeout=120)
    r.raise_for_status()
    d = r.json()
    estado = d.get("status", {}).get("state")
    if estado != "SUCCEEDED":
        raise RuntimeError(f"consulta Databricks no exitosa ({estado}): "
                           f"{d.get('status', {}).get('error')}")
    cols = [c["name"] for c in d["manifest"]["schema"]["columns"]]
    data = d.get("result", {}).get("data_array", [])
    return _coerce_tipos(pd.DataFrame(data, columns=cols))


def leer_oro(tabla: str) -> pd.DataFrame:
    """Devuelve la tabla oro `tabla` como DataFrame, con caché TTL en memoria."""
    if tabla not in TABLAS:
        raise KeyError(f"Tabla oro desconocida: {tabla}")

    ahora = time.time()
    cacheado = _cache.get(tabla)
    if cacheado and (ahora - cacheado[0]) < settings.cache_ttl_seconds:
        return cacheado[1]

    if settings.gold_mode == "local":
        df = _leer_local(tabla)
    elif settings.gold_mode == "databricks":
        df = _leer_databricks(tabla)
    else:
        df = _leer_s3(tabla)
    _cache[tabla] = (ahora, df)
    return df


def limpiar_cache() -> None:
    _cache.clear()
