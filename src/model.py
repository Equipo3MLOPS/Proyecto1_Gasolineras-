"""Etapa 5 (opcional) — Modelado con seguimiento de MLflow.

Toma el dataset gold (`artifacts/gold/dataset_precios.csv`) y entrena un modelo
simple para pronosticar el precio del *próximo* período por combustible. Cada
corrida queda registrada en MLflow (Experiments + Models), de modo que se pueden
comparar modelos y versionarlos sin planillas sueltas.

Integración deliberadamente mínima de MLflow:
  - Tracking local en `./mlruns` (sin servidor).
  - Se loguean parámetros, métrica (MAE) y el dataset de entrada (linaje).
  - El Pipeline de scikit-learn se empaqueta con `mlflow.sklearn.log_model`.

El preprocesado (StandardScaler) va DENTRO del Pipeline y se ajusta solo con el
train: cumple la nota de diseño de `transform.py` (la normalización pertenece al
modelado, no al ETL, para no filtrar el test -> data leakage).

Si MLflow no está instalado, la etapa se omite con un aviso en vez de romper el
pipeline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import config as C

EXPERIMENT = "precio_gasolineras"
FEATURES_NUM = ["precio_galon", "precio_galon_anterior", "dias_desde_anterior"]
FEATURES_CAT = ["tipo_combustible"]
FEATURES = FEATURES_NUM + FEATURES_CAT
TARGET = "precio_siguiente"  # precio del próximo período (lo que queremos predecir)


def _prepare() -> pd.DataFrame:
    """Carga el gold y arma el objetivo: el precio de la próxima visita por combustible."""
    df = pd.read_csv(C.GOLD_DATASET, parse_dates=["fecha_hora_local"])
    df = df.sort_values(["tipo_combustible", "fecha_hora_local"])
    df[TARGET] = df.groupby("tipo_combustible")["precio_galon"].shift(-1)
    # filas usables: con objetivo conocido y con el precio anterior ya calculado
    return df.dropna(subset=[TARGET, "precio_galon_anterior"]).reset_index(drop=True)


def _temporal_split(df: pd.DataFrame):
    """Split por tiempo (no aleatorio): la última fecha es validación."""
    corte = df["fecha_hora_local"].max()
    train = df[df["fecha_hora_local"] < corte]
    valid = df[df["fecha_hora_local"] == corte]
    return train, valid


def _build_pipeline() -> Pipeline:
    pre = ColumnTransformer(
        [
            ("num", StandardScaler(), FEATURES_NUM),
            ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CAT),
        ]
    )
    return Pipeline([("pre", pre), ("model", Ridge(alpha=1.0))])


def run() -> None:
    C.ensure_dirs()

    try:
        import mlflow
        import mlflow.sklearn
    except ImportError:
        print("[model] MLflow no está instalado; etapa omitida. "
              "Instalalo con `pip install mlflow` para registrar experimentos.")
        return

    data = _prepare()
    if len(data) < 4:
        print(f"[model] solo {len(data)} filas usables; muy pocas para modelar. Etapa omitida.")
        return

    train, valid = _temporal_split(data)
    Xtr, ytr = train[FEATURES], train[TARGET]
    Xva, yva = valid[FEATURES], valid[TARGET]

    # backend SQLite (MLflow 3.x desaconseja el backend de archivos); los
    # artefactos (modelos) van a ./mlartifacts. Ambos están en .gitignore.
    mlflow.set_tracking_uri(f"sqlite:///{C.ROOT / 'mlflow.db'}")
    mlflow.set_experiment(EXPERIMENT)
    dataset = mlflow.data.from_pandas(data, name="dataset_precios", targets=TARGET)

    # --- Corrida 1: baseline ingenuo (precio próximo = precio actual) ---
    with mlflow.start_run(run_name="baseline_carry_forward"):
        mlflow.log_param("tipo", "baseline_carry_forward")
        mlflow.log_input(dataset, context="training")
        mae_base = mean_absolute_error(yva, valid["precio_galon"])
        mlflow.log_metric("mae", mae_base)

    # --- Corrida 2: modelo Ridge (preprocesado dentro del Pipeline) ---
    with mlflow.start_run(run_name="ridge"):
        mlflow.log_param("tipo", "ridge")
        mlflow.log_param("alpha", 1.0)
        mlflow.log_param("features", ",".join(FEATURES))
        mlflow.log_input(dataset, context="training")

        pipe = _build_pipeline()
        pipe.fit(Xtr, ytr)
        mae_ridge = mean_absolute_error(yva, pipe.predict(Xva))
        mlflow.log_metric("mae", mae_ridge)

        mlflow.sklearn.log_model(
            pipe,
            name="modelo_precio",
            input_example=Xtr.head(2),
            registered_model_name="precio_combustible",
            serialization_format="cloudpickle",
        )

    print(f"[model] experimento '{EXPERIMENT}' registrado en {C.ROOT / 'mlflow.db'}")
    print(f"[model] MAE baseline={mae_base:.4f} | MAE ridge={mae_ridge:.4f} "
          f"(n_train={len(train)}, n_valid={len(valid)})")
    print(f"[model] abrí la interfaz con:  mlflow ui --backend-store-uri "
          f"sqlite:///{C.ROOT / 'mlflow.db'}")


if __name__ == "__main__":
    run()
