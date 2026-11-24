"""API de precios y predicción de gasolina (Guatemala) — equipo3.

Lee SOLO la capa Oro (S3) y la sirve por HTTP. No corre el modelo: el modelo vive
en Databricks y deja sus resultados en `gold.predicciones` / `gold.metricas_modelo`.

Endpoints (documento, Fase 5):
  GET /health                      estado del servicio
  GET /precios/actual              último precio por combustible
  GET /precios?combustible&desde&hasta&limit   histórico semanal con filtros
  GET /prediccion?combustible      predicción de la semana siguiente
  GET /modelo/metricas             exactitud del modelo y de la línea base
  GET /docs                        documentación Swagger (automática)
"""
from __future__ import annotations

import os
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from .config import settings
from .gold import leer_oro

_STATIC = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title=settings.api_title, version=settings.api_version,
              description="Precios y predicción de combustibles Shell (Guatemala). "
                          "Datos de la capa Oro del pipeline medallón.")

FUELS = ["diesel", "regular", "super", "v_power"]


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> lista de dicts con NaN convertido a None (JSON válido)."""
    return df.astype(object).where(pd.notna(df), None).to_dict("records")


def _oro(tabla: str) -> pd.DataFrame:
    try:
        return leer_oro(tabla)
    except Exception as exc:  # S3 inaccesible, credenciales, etc.
        raise HTTPException(status_code=503,
                            detail=f"No se pudo leer la capa oro ({tabla}): {exc}") from exc


@app.get("/", include_in_schema=False)
def raiz():
    """Dashboard web que consume la propia API (mismo origen, sin CORS)."""
    return FileResponse(os.path.join(_STATIC, "index.html"))


@app.get("/health", tags=["servicio"])
def health():
    """Estado del servicio y si puede leer la capa oro."""
    try:
        n = len(leer_oro("predicciones"))
        return {"status": "ok", "gold_mode": settings.gold_mode, "predicciones": n}
    except Exception as exc:
        return {"status": "degraded", "gold_mode": settings.gold_mode, "error": str(exc)[:200]}


@app.get("/precios/actual", tags=["precios"])
def precios_actual():
    """Último precio promedio semanal conocido, por combustible."""
    df = _oro("precio_semanal")
    if df.empty:
        return {"precios": []}
    idx = df.sort_values("semana").groupby("combustible").tail(1)
    cols = ["combustible", "semana", "precio_promedio", "precio_min", "precio_max"]
    return {"precios": _records(idx[cols].sort_values("combustible"))}


@app.get("/precios", tags=["precios"])
def precios(
    combustible: Optional[str] = Query(None, description="diesel | regular | super | v_power"),
    desde: Optional[str] = Query(None, description="fecha inicial YYYY-MM-DD (inclusive)"),
    hasta: Optional[str] = Query(None, description="fecha final YYYY-MM-DD (inclusive)"),
    limit: int = Query(100, ge=1, le=1000, description="máximo de filas"),
):
    """Histórico de precios semanales (martes a lunes) con filtros."""
    if combustible and combustible not in FUELS:
        raise HTTPException(422, f"combustible inválido; use uno de {FUELS}")
    df = _oro("precio_semanal")
    if combustible:
        df = df[df["combustible"] == combustible]
    if desde:
        df = df[df["semana"] >= desde]
    if hasta:
        df = df[df["semana"] <= hasta]
    df = df.sort_values(["semana", "combustible"])
    total = len(df)
    df = df.head(limit)
    return {"total": total, "mostrados": len(df), "limit": limit,
            "precios": _records(df)}


@app.get("/prediccion", tags=["predicción"])
def prediccion(
    combustible: Optional[str] = Query(None, description="diesel | regular | super | v_power"),
):
    """Predicción de la dirección del precio para la semana siguiente."""
    if combustible and combustible not in FUELS:
        raise HTTPException(422, f"combustible inválido; use uno de {FUELS}")
    df = _oro("predicciones")
    df = df[df["tipo"] == "futura"]
    cols = ["combustible", "semana", "prediccion", "probabilidad", "modelo"]
    if combustible:
        fila = df[df["combustible"] == combustible]
        if fila.empty:
            raise HTTPException(404, f"sin predicción para {combustible}")
        return _records(fila[cols])[0]
    return {"predicciones": _records(df[cols].sort_values("combustible"))}


@app.get("/modelo/metricas", tags=["modelo"])
def modelo_metricas():
    """Exactitud del modelo elegido y de la línea base (validación temporal)."""
    df = _oro("metricas_modelo")
    if df.empty:
        raise HTTPException(503, "sin métricas de modelo todavía")
    elegido = df[df["elegido"] == True]  # noqa: E712
    base = df[df["es_baseline"] == True]  # noqa: E712
    resumen = {}
    if not elegido.empty and not base.empty:
        e, b = elegido.iloc[0], base.iloc[0]
        resumen = {
            "modelo_elegido": e["modelo"],
            "accuracy_elegido": round(float(e["accuracy"]), 4),
            "accuracy_baseline": round(float(b["accuracy"]), 4),
            "supera_baseline": bool(e["accuracy"] > b["accuracy"]),
            "n_test": int(e["n_test"]),
        }
    return {"resumen": resumen, "modelos": _records(df)}


# ---------------------------------------------------------------------------
# Fotos de surtidor (capa Plata) — endpoints NUEVOS para el mapa del dashboard.
# No modifican ninguno de los endpoints de arriba.
# ---------------------------------------------------------------------------
from fastapi.responses import Response  # noqa: E402

from . import fotos as fotos_plata  # noqa: E402


@app.get("/fotos", tags=["fotos"])
def fotos(
    combustible: Optional[str] = Query(None, description="diesel | regular | super | v_power"),
    desde: Optional[str] = Query(None, description="fecha inicial YYYY-MM-DD (inclusive)"),
    hasta: Optional[str] = Query(None, description="fecha final YYYY-MM-DD (inclusive)"),
    ubicacion: Optional[str] = Query(None, description="id de estación, p. ej. ST_14p560_m90p463"),
    incluir_rechazadas: bool = Query(False, description="incluir fotos que no pasaron calidad"),
    limit: int = Query(1000, ge=1, le=5000, description="máximo de filas"),
):
    """Una lectura por foto: fecha, precio Q/galón, total, galones y ubicación GPS.

    La ubicación sale del id de estación (GPS redondeado a 3 decimales, ~110 m).
    `imagen_url` apunta a la miniatura de la foto.
    """
    if combustible and combustible not in FUELS:
        raise HTTPException(422, f"combustible inválido; use uno de {FUELS}")
    try:
        filas = fotos_plata.observaciones(incluir_rechazadas)
    except Exception as exc:
        raise HTTPException(status_code=503,
                            detail=f"No se pudo leer la capa plata: {exc}") from exc
    if combustible:
        filas = [f for f in filas if f["combustible"] == combustible]
    if desde:
        filas = [f for f in filas if (f["fecha"] or "") >= desde]
    if hasta:
        filas = [f for f in filas if (f["fecha"] or "") <= hasta]
    if ubicacion:
        filas = [f for f in filas if f["ubicacion"] == ubicacion]
    return {"total": len(filas), "mostrados": min(len(filas), limit), "limit": limit,
            "fotos": filas[:limit]}


@app.get("/fotos/{image_id}/imagen", tags=["fotos"],
         responses={200: {"content": {"image/jpeg": {}}}})
def foto_imagen(image_id: str):
    """Miniatura JPEG de la foto (sin metadatos EXIF), cacheada en el servidor."""
    try:
        jpg = fotos_plata.miniatura(image_id)
    except Exception as exc:
        raise HTTPException(status_code=503,
                            detail=f"No se pudo obtener la foto {image_id}: {exc}") from exc
    if jpg is None:
        raise HTTPException(404, f"foto no encontrada: {image_id}")
    return Response(content=jpg, media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"})


# ---------------------------------------------------------------------------
# Presentación del jurado — ruta NUEVA, servida igual que el dashboard (/).
# `static/presentacion.html` es una copia de presentacion/presentacion_jurado.html
# (la imagen Docker solo incluye api/app/; ver presentacion/web/README.md).
# ---------------------------------------------------------------------------
@app.get("/presentacion", include_in_schema=False)
def presentacion():
    """Presentación web del proyecto (HTML autocontenido, funciona sin internet)."""
    ruta = os.path.join(_STATIC, "presentacion.html")
    if not os.path.isfile(ruta):
        raise HTTPException(404, "presentación no disponible")
    return FileResponse(ruta)
