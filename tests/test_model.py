"""Pruebas de la etapa de modelo (backend local, sin MLflow, datos sintéticos)."""
from __future__ import annotations

import os

os.environ.setdefault("PIPELINE_BACKEND", "local")
os.environ["MODEL_MLFLOW"] = "0"

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from src import config as C, io_layer as io, load, model  # noqa: E402


@pytest.fixture
def gold_tmp(tmp_path, monkeypatch):
    """Redirige las tablas Oro a una carpeta temporal y escribe features sintéticas."""
    for ds in ("gold.features_modelo", "gold.predicciones", "gold.metricas_modelo"):
        monkeypatch.setitem(C.DATASETS[ds], "csv", tmp_path / f"{ds.split('.')[1]}.csv")
    monkeypatch.setattr(C, "MODEL_MLFLOW", False)

    rng = np.random.default_rng(0)
    semanas = pd.date_range("2025-01-07", periods=24, freq="7D")   # martes
    filas = []
    for fuel, base in (("super", 32.0), ("regular", 31.0), ("diesel", 29.0)):
        precio = base + np.cumsum(rng.choice([-0.5, 0.0, 0.5], size=len(semanas)))
        for s, p in zip(semanas, precio):
            filas.append({"semana": s.date(), "combustible": fuel, "precio_promedio": p,
                          "precio_min": p, "precio_max": p, "n_observaciones": 1})
    sem = pd.DataFrame(filas)
    feats = load._features_modelo(sem)
    feats["semana"] = feats["semana"].astype(str)
    io.write_df(feats, "gold.features_modelo")
    return feats


def test_split_temporal_no_mezcla_semanas(gold_tmp):
    df = model.preparar(gold_tmp).dropna(subset=[model.TARGET])
    train, test = model.split_temporal(df, 0.3)
    assert train["semana"].max() < test["semana"].min()      # validación temporal, no aleatoria
    assert len(train) + len(test) == len(df)


def test_baseline_repite_la_direccion_actual():
    df = pd.DataFrame({"direccion": ["sube", None, "baja"]})
    assert list(model.prediccion_baseline(df)) == ["sube", "se_mantiene", "baja"]


def test_run_escribe_predicciones_y_metricas(gold_tmp):
    pred = model.run()
    assert pred is not None

    p = io.read_df("gold.predicciones")
    for col in ["semana", "combustible", "prediccion", "probabilidad", "direccion_real", "tipo"]:
        assert col in p.columns
    assert set(p["prediccion"]).issubset({"sube", "baja", "se_mantiene"})
    assert p["probabilidad"].between(0, 1).all()

    futuras = p[p["tipo"] == "futura"]
    assert sorted(futuras["combustible"]) == ["diesel", "regular", "super"]   # una por combustible
    assert futuras["direccion_real"].isna().all()
    # la semana predicha es la siguiente a la última observada
    assert (pd.to_datetime(futuras["semana"]) - pd.to_datetime(futuras["semana_base"])
            == pd.Timedelta(days=7)).all()
    assert p.loc[p["tipo"] == "validacion", "direccion_real"].notna().all()

    m = io.read_df("gold.metricas_modelo")
    assert m["es_baseline"].sum() == 1 and m["elegido"].sum() == 1
    assert m["accuracy"].between(0, 1).all()


def test_run_es_idempotente(gold_tmp):
    model.run()
    p1 = io.read_df("gold.predicciones").drop(columns="generado_en")
    model.run()
    p2 = io.read_df("gold.predicciones").drop(columns="generado_en")
    pd.testing.assert_frame_equal(p1, p2)
