"""Pruebas del pipeline de datos (backend local).

Son pruebas rápidas sobre la lógica ya probada: una unitaria (identificador de
estación) y una de integración que corre extract → transform → load sobre las
fotos de ejemplo del repo y valida el contrato de la capa gold.
"""
from __future__ import annotations

import os

# Asegura el backend local antes de importar src (config lee el entorno al importar).
os.environ.setdefault("PIPELINE_BACKEND", "local")

import pandas as pd  # noqa: E402

from src import config as C  # noqa: E402
from src.transform import _station_id  # noqa: E402


def test_backend_local_por_defecto():
    assert C.BACKEND == "local"


def test_station_id_estable_y_desconocido():
    a = _station_id(14.6, -90.5)
    b = _station_id(14.6, -90.5)
    assert a == b                      # determinista
    assert a.startswith("ST_")
    assert _station_id(float("nan"), -90.5) == "ST_UNKNOWN"


def test_pipeline_local_gold_cumple_contrato():
    """extract → transform → load produce la gold esperada."""
    from src import extract, transform, load

    extract.run()
    transform.run()
    gold = load.run()

    # Contrato de la capa gold (lo que consumirá el pipeline del modelo):
    assert len(gold) == 20
    assert set(gold["tipo_combustible"]) == {"diesel", "regular", "super", "v_power"}
    assert gold["precio_galon"].notna().all()
    # columnas que el modelo necesita para armar features/target
    for col in ["precio_galon", "precio_galon_anterior", "dias_desde_anterior",
                "tipo_combustible", "fecha_hora_local"]:
        assert col in gold.columns, f"falta la columna {col} en gold"


def test_silver_tiene_reconciliados_e_imputados():
    """La capa silver debe marcar precios reconciliados e imputados."""
    from src import transform

    fillups, precios = transform.run()
    assert isinstance(precios, pd.DataFrame) and len(precios) > 0
    assert int(precios["is_reconciled"].sum()) > 0
    assert int(precios["is_imputed"].sum()) > 0
