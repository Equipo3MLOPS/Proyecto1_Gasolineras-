from __future__ import annotations

import os

os.environ.setdefault("PIPELINE_BACKEND", "local")
os.environ.setdefault("PIPELINE_VISION", "json")

from src import config as C  
from src import extract, transform, load, io_layer as io  
from src.transform import _station_id  


def _limpiar_artefactos():
    for meta in C.DATASETS.values():
        if meta["csv"].exists():
            meta["csv"].unlink()


def test_backend_local_por_defecto():
    assert C.BACKEND == "local"


def test_station_id_estable_y_desconocido():
    a = _station_id(14.6, -90.5)
    assert a == _station_id(14.6, -90.5)
    assert a.startswith("ST_")
    assert _station_id(float("nan"), -90.5) == "ST_DESCONOCIDA"


def test_pipeline_capas_cumplen_contrato():
    _limpiar_artefactos()
    extract.run()
    aceptados, rechazados = transform.run()
    feats = load.run()

    sp = io.read_df("silver.precios")
    assert len(sp) == 5                                   
    for col in ["fecha", "combustible", "precio_q_galon", "modalidad",
                "ubicacion", "foto_origen"]:
        assert col in sp.columns, f"falta {col} en silver.precios"
    assert sp["precio_q_galon"].notna().all()
    assert set(sp["combustible"]).issubset(set(C.FUEL_TYPES))
    assert len(rechazados) == 0                            

    ps = io.read_df("gold.precio_semanal")
    assert (ps["precio_min"] <= ps["precio_promedio"]).all()
    assert (ps["precio_promedio"] <= ps["precio_max"]).all()

    vs = io.read_df("gold.variacion_semanal")
    assert set(vs["direccion"]).issubset({"sube", "baja", "se_mantiene"})

    assert "direccion_siguiente" in feats.columns
    assert set(feats["direccion"].dropna()).issubset({"sube", "baja", "se_mantiene"})


def test_plata_es_idempotente():
    _limpiar_artefactos()
    extract.run()
    transform.run()
    n1 = len(io.read_df("silver.precios"))
    transform.run()
    n2 = len(io.read_df("silver.precios"))
    assert n1 == n2 == 5
