"""Fotos de surtidor (capa Plata) para el mapa del dashboard.

Módulo NUEVO y aislado: no modifica `gold.py` ni los endpoints existentes (que
consume el modelo). Solo LEE:

  - `silver.precios`           una lectura limpia por foto (fecha, precio, GPS…)
  - `silver.precios_rejected`  fotos que no pasaron las reglas de calidad
  - `bronze.fotos_precios`     binario original de la foto (para la miniatura)

Respeta el mismo `GOLD_MODE` que el resto de la API:
  databricks -> SQL Warehouse con el token (PAT) del .env (no necesita S3)
  s3         -> Delta de plata en S3 + objeto original del bucket raw
  local      -> parquet en LOCAL_GOLD_DIR (silver_*.parquet) y fotos en
                LOCAL_GOLD_DIR/fotos/
"""
from __future__ import annotations

import base64
import glob
import io
import os
import re
import threading
import time

import pandas as pd

from .config import settings
from .gold import _coerce_tipos, _storage_options

TABLAS_PLATA = ["precios", "precios_rejected"]

# ubicacion = "ST_14p560_m90p463"  ->  (14.560, -90.463)   (ver src/transform.py)
_RE_UBICACION = re.compile(r"^ST_(m?\d+p\d+)_(m?\d+p\d+)$")
# image_id = "IMG_8810"; se valida antes de usarlo en rutas o consultas
_RE_IMAGE_ID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")

_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


# ------------------------------------------------------------------ lectura --

def _sql_databricks(statement: str, parameters: list[dict] | None = None) -> pd.DataFrame:
    """Ejecuta una consulta de SOLO LECTURA en el SQL Warehouse de Databricks."""
    import requests

    url = f"{settings.databricks_host.rstrip('/')}/api/2.0/sql/statements"
    payload = {
        "warehouse_id": settings.databricks_warehouse_id,
        "statement": statement,
        "wait_timeout": "50s",
    }
    if parameters:
        payload["parameters"] = parameters
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
    return pd.DataFrame(data, columns=cols)


def leer_plata(tabla: str) -> pd.DataFrame:
    """Devuelve la tabla de plata `tabla` como DataFrame, con caché TTL en memoria."""
    if tabla not in TABLAS_PLATA:
        raise KeyError(f"Tabla plata desconocida: {tabla}")

    ahora = time.time()
    cacheado = _cache.get(tabla)
    if cacheado and (ahora - cacheado[0]) < settings.cache_ttl_seconds:
        return cacheado[1]

    if settings.gold_mode == "local":
        df = pd.read_parquet(os.path.join(settings.local_gold_dir, f"silver_{tabla}.parquet"))
    elif settings.gold_mode == "databricks":
        df = _coerce_tipos(_sql_databricks(f"SELECT * FROM {settings.uc_catalog}.silver.{tabla}"))
    else:
        from deltalake import DeltaTable

        uri = f"s3://{settings.silver_bucket}/{settings.team}/silver/{tabla}"
        df = DeltaTable(uri, storage_options=_storage_options()).to_pandas()
    _cache[tabla] = (ahora, df)
    return df


# --------------------------------------------------------------- transformar --

def coordenadas(ubicacion) -> tuple[float, float] | tuple[None, None]:
    """Decodifica el id de estación (GPS redondeado a 3 decimales, ~110 m)."""
    m = _RE_UBICACION.match(str(ubicacion or ""))
    if not m:
        return None, None

    def num(s: str) -> float:
        return float(s.replace("m", "-").replace("p", "."))

    return num(m.group(1)), num(m.group(2))


def _valor(v):
    """NaN/NaT -> None para que el JSON sea válido."""
    try:
        return None if pd.isna(v) else v
    except (TypeError, ValueError):
        return v


def observaciones(incluir_rechazadas: bool = False) -> list[dict]:
    """Una fila por lectura de foto, lista para el mapa (más reciente primero)."""
    marcos = [leer_plata("precios").assign(estado="aceptada", motivo_rechazo=None)]
    if incluir_rechazadas:
        marcos.append(leer_plata("precios_rejected").assign(estado="rechazada"))
    df = pd.concat(marcos, ignore_index=True)

    filas = []
    for r in df.to_dict("records"):
        lat, lon = coordenadas(r.get("ubicacion"))
        ts = _valor(r.get("ts_local"))
        image_id = _valor(r.get("image_id"))
        filas.append({
            "image_id": image_id,
            "fecha": _valor(r.get("fecha")),
            "hora": str(ts)[11:16] if ts and len(str(ts)) >= 16 else None,
            "ts_local": ts,
            "combustible": _valor(r.get("combustible")),
            "precio_q_galon": _valor(r.get("precio_q_galon")),
            "esta_venta": _valor(r.get("esta_venta")),
            "galones": _valor(r.get("galones")),
            "modalidad": _valor(r.get("modalidad")),
            "ubicacion": _valor(r.get("ubicacion")),
            "lat": lat,
            "lon": lon,
            "estado": r["estado"],
            "motivo_rechazo": _valor(r.get("motivo_rechazo")),
            "imagen_url": f"/fotos/{image_id}/imagen" if image_id else None,
        })
    filas.sort(key=lambda f: str(f["ts_local"] or f["fecha"] or ""), reverse=True)
    return filas


# --------------------------------------------------------------- miniaturas --

def _foto_origen(image_id: str) -> str | None:
    """Ruta original (s3://…/IMG_x.HEIC) de la foto, buscada en plata."""
    for tabla in TABLAS_PLATA:
        df = leer_plata(tabla)
        fila = df[df["image_id"] == image_id]
        if not fila.empty and pd.notna(fila.iloc[0]["foto_origen"]):
            return str(fila.iloc[0]["foto_origen"])
    return None


def _bytes_originales(image_id: str, origen: str) -> bytes | None:
    if settings.gold_mode == "local":
        carpeta = os.path.join(settings.local_gold_dir, "fotos")
        candidatos = [os.path.join(carpeta, os.path.basename(origen))]
        candidatos += sorted(glob.glob(os.path.join(carpeta, f"{image_id}.*")))
        for ruta in candidatos:
            if os.path.isfile(ruta):
                with open(ruta, "rb") as f:
                    return f.read()
        return None

    if settings.gold_mode == "databricks":
        df = _sql_databricks(
            f"SELECT content FROM {settings.uc_catalog}.bronze.fotos_precios "
            "WHERE _source_file = :origen LIMIT 1",
            parameters=[{"name": "origen", "value": origen, "type": "STRING"}],
        )
        if df.empty or df.iloc[0]["content"] is None:
            return None
        return base64.b64decode(df.iloc[0]["content"])

    import boto3  # gold_mode == "s3": objeto original del bucket raw

    opts = _storage_options()
    s3 = boto3.client(
        "s3", region_name=opts.get("AWS_REGION"),
        aws_access_key_id=opts.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=opts.get("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=opts.get("AWS_SESSION_TOKEN"),
    )
    bucket, _, key = origen.removeprefix("s3://").partition("/")
    return s3.get_object(Bucket=bucket, Key=key)["Body"].read()


def _a_jpeg(original: bytes, lado_max: int) -> bytes:
    from PIL import Image, ImageOps
    from pillow_heif import register_heif_opener

    register_heif_opener()
    with Image.open(io.BytesIO(original)) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((lado_max, lado_max))
        salida = io.BytesIO()
        # sin `exif=` -> la miniatura NO lleva metadatos (ni el GPS exacto)
        im.save(salida, "JPEG", quality=80, optimize=True)
        return salida.getvalue()


def _lock(clave: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(clave, threading.Lock())


def miniatura(image_id: str) -> bytes | None:
    """JPEG reducido de la foto; se cachea en disco para no repetir la descarga.

    Devuelve None si el id no existe en plata o la foto original no se encuentra.
    """
    if not _RE_IMAGE_ID.match(image_id or ""):
        return None
    lado = settings.miniatura_px
    ruta_cache = os.path.join(settings.fotos_cache_dir, f"{image_id}_{lado}.jpg")
    if os.path.isfile(ruta_cache):
        with open(ruta_cache, "rb") as f:
            return f.read()

    with _lock(image_id):  # evita bajar la misma foto dos veces en paralelo
        if os.path.isfile(ruta_cache):
            with open(ruta_cache, "rb") as f:
                return f.read()
        origen = _foto_origen(image_id)
        if not origen:
            return None
        original = _bytes_originales(image_id, origen)
        if not original:
            return None
        jpg = _a_jpeg(original, lado)
        try:
            os.makedirs(settings.fotos_cache_dir, exist_ok=True)
            tmp = f"{ruta_cache}.{os.getpid()}.tmp"
            with open(tmp, "wb") as f:
                f.write(jpg)
            os.replace(tmp, ruta_cache)
        except OSError:
            pass  # sin caché en disco: igual se devuelve la imagen
        return jpg
