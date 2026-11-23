"""Etapa de MODELO — REFERENCIA para el compañero (no es parte del Job de datos).

Lee `gold.features_modelo` y entrena un clasificador que predice la DIRECCION
de la semana siguiente (sube / baja / se_mantiene) por combustible, lo compara
contra una línea base de persistencia ("se repite la dirección de la semana
anterior") con validación temporal, y registra todo en MLflow.

Es un punto de partida intencionalmente simple: el pipeline del modelo
(incluida la tabla `gold.predicciones`) lo desarrolla e integra el compañero.
"""
from __future__ import annotations

import os

import pandas as pd

from . import config as C, io_layer as io

FEATURES = ["variacion_1s", "variacion_2s", "variacion_3s", "variacion_4s",
            "promedio_movil_4s", "dif_super_diesel"]
TARGET = "direccion_siguiente"


def _prepare() -> pd.DataFrame:
    df = io.read_df("gold.features_modelo")
    df = df.dropna(subset=[TARGET]).reset_index(drop=True)
    df[FEATURES] = df[FEATURES].fillna(0.0)
    return df.sort_values("semana").reset_index(drop=True)


def run() -> None:
    C.ensure_dirs()
    try:
        import mlflow
        import mlflow.sklearn
        from sklearn.tree import DecisionTreeClassifier
        from sklearn.metrics import accuracy_score
    except ImportError:
        print("[modelo] falta mlflow/sklearn; etapa de referencia omitida.")
        return

    data = _prepare()
    if data["semana"].nunique() < 2 or len(data) < 4:
        print(f"[modelo] datos insuficientes ({len(data)} filas, "
              f"{data['semana'].nunique()} semanas). Se necesitan más fotos/semanas.")
        return

    corte = data["semana"].max()           # validación temporal: última semana
    train = data[data["semana"] < corte]
    valid = data[data["semana"] == corte]
    if train.empty or valid.empty:
        print("[modelo] no hay suficientes semanas para un split temporal.")
        return

    if C.BACKEND == "local":
        mlflow.set_tracking_uri(f"sqlite:///{C.ROOT / 'mlflow.db'}")
        mlflow.set_experiment("precio_gasolineras_direccion")
    else:
        mlflow.set_registry_uri("databricks-uc")
        mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_PATH",
                                             "/Shared/precio_gasolineras_direccion"))

    # --- línea base: persistencia (la dirección siguiente = la actual) ---
    with mlflow.start_run(run_name="baseline_persistencia"):
        mlflow.log_param("tipo", "baseline_persistencia")
        acc_base = accuracy_score(valid[TARGET], valid["direccion"].fillna("se_mantiene"))
        mlflow.log_metric("accuracy", acc_base)

    # --- modelo: árbol de decisión ---
    with mlflow.start_run(run_name="arbol_decision"):
        mlflow.log_param("tipo", "decision_tree")
        mlflow.log_param("features", ",".join(FEATURES))
        clf = DecisionTreeClassifier(max_depth=3, random_state=0)
        clf.fit(train[FEATURES], train[TARGET])
        acc_model = accuracy_score(valid[TARGET], clf.predict(valid[FEATURES]))
        mlflow.log_metric("accuracy", acc_model)
        mlflow.sklearn.log_model(clf, name="modelo_direccion", input_example=train[FEATURES].head(2))

    print(f"[modelo] accuracy baseline={acc_base:.3f} | arbol={acc_model:.3f} "
          f"(n_train={len(train)}, n_valid={len(valid)})")


if __name__ == "__main__":
    run()
