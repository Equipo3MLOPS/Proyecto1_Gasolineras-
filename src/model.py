"""Etapa MODELO — predice la dirección del precio de la semana siguiente.

Lee `gold.features_modelo` (capa Oro) y, por combustible, clasifica si el precio
de la semana siguiente `sube`, `baja` o `se_mantiene`.

1. Validación temporal (no aleatoria): se entrena con las semanas antiguas y se
   evalúa con el último tramo de semanas (`MODEL_TEST_FRACTION`).
2. Se comparan varios clasificadores contra la línea base del PDF:
   "se repite la dirección de la semana anterior".
3. Todo queda registrado en MLflow (parámetros, métricas y modelos); el elegido
   se registra como modelo si `MLFLOW_REGISTERED_MODEL` está definido.
4. El modelo elegido se reentrena con todas las semanas y predice la semana
   siguiente a la última observada de cada combustible.

Escribe dos tablas Oro que consume la API:
  - `gold.predicciones`     -> /prediccion
  - `gold.metricas_modelo`  -> /modelo/metricas

Nota sobre los datos: las fotos no cubren todas las semanas, así que la
"semana siguiente" en el histórico es la siguiente semana CON foto (puede
estar a varias semanas). `dias_desde_anterior` le da esa información al
modelo. `dif_super_diesel` no se usa: casi nunca hay súper y diésel en la
misma semana, por lo que la columna viene vacía en casi todas las filas.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from . import config as C, io_layer as io

FEATURES_NUM = [
    "precio_promedio", "variacion_1s", "variacion_2s", "variacion_3s", "variacion_4s",
    "promedio_movil_4s", "precio_vs_promedio", "dias_desde_anterior",
]
FEATURES_CAT = ["combustible"]
FEATURES = FEATURES_NUM + FEATURES_CAT
TARGET = "direccion_siguiente"
BASELINE = "baseline_persistencia"


# --------------------------------------------------------------------- datos
def preparar(feats: pd.DataFrame) -> pd.DataFrame:
    """Agrega variables derivadas y la semana objetivo de cada fila."""
    df = feats.copy()
    df["semana"] = pd.to_datetime(df["semana"])
    df = df.sort_values(["combustible", "semana"]).reset_index(drop=True)
    g = df.groupby("combustible")
    df["dias_desde_anterior"] = g["semana"].diff().dt.days
    df["precio_vs_promedio"] = df["precio_promedio"] - df["promedio_movil_4s"]
    # semana a la que se refiere `direccion_siguiente` (la siguiente con foto)
    df["semana_objetivo"] = g["semana"].shift(-1)
    df[FEATURES_NUM] = df[FEATURES_NUM].astype(float).fillna(0.0)
    return df


def split_temporal(etiquetadas: pd.DataFrame, fraccion: float):
    """Las últimas semanas (≈ `fraccion`) son prueba; las anteriores, entrenamiento."""
    semanas = np.sort(etiquetadas["semana"].unique())
    n_test = max(1, int(round(len(semanas) * fraccion)))
    if len(semanas) - n_test < 2:
        raise ValueError(f"Muy pocas semanas ({len(semanas)}) para validar en el tiempo.")
    corte = semanas[-n_test]
    return etiquetadas[etiquetadas["semana"] < corte], etiquetadas[etiquetadas["semana"] >= corte]


# ------------------------------------------------------------------- modelos
def _preproceso() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", StandardScaler(), FEATURES_NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CAT),
    ])


def candidatos() -> dict[str, Pipeline]:
    return {
        "regresion_logistica": Pipeline([
            ("pre", _preproceso()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]),
        "arbol_decision": Pipeline([
            ("pre", _preproceso()),
            ("clf", DecisionTreeClassifier(max_depth=3, class_weight="balanced", random_state=0)),
        ]),
        "bosque_aleatorio": Pipeline([
            ("pre", _preproceso()),
            ("clf", RandomForestClassifier(n_estimators=200, max_depth=4, min_samples_leaf=2,
                                           class_weight="balanced", random_state=0)),
        ]),
    }


def prediccion_baseline(df: pd.DataFrame) -> pd.Series:
    """Línea base: la dirección siguiente es igual a la de esta semana."""
    return df["direccion"].fillna("se_mantiene")


def _metricas(y_real, y_pred, combustibles: pd.Series) -> dict:
    out = {
        "accuracy": float(accuracy_score(y_real, y_pred)),
        "f1_macro": float(f1_score(y_real, y_pred, average="macro", zero_division=0)),
    }
    real, pred = pd.Series(list(y_real)), pd.Series(list(y_pred))
    comb = combustibles.reset_index(drop=True)
    for fuel in ("super", "regular", "diesel"):
        m = comb == fuel
        out[f"accuracy_{fuel}"] = float((real[m] == pred[m]).mean()) if m.any() else None
    return out


def evaluar(train: pd.DataFrame, test: pd.DataFrame):
    """Entrena cada candidato con `train`, evalúa en `test`.

    Devuelve (resultados por modelo, modelos entrenados, predicciones de prueba).
    """
    resultados = {BASELINE: _metricas(test[TARGET], prediccion_baseline(test), test["combustible"])}
    modelos, preds = {}, {BASELINE: (prediccion_baseline(test).to_numpy(), None)}
    for nombre, pipe in candidatos().items():
        pipe.fit(train[FEATURES], train[TARGET])
        y = pipe.predict(test[FEATURES])
        proba = pipe.predict_proba(test[FEATURES]).max(axis=1)
        resultados[nombre] = _metricas(test[TARGET], y, test["combustible"])
        modelos[nombre], preds[nombre] = pipe, (y, proba)
    return resultados, modelos, preds


def elegir(resultados: dict) -> str:
    """El mejor clasificador (sin contar la línea base) por accuracy y luego F1."""
    ml = {k: v for k, v in resultados.items() if k != BASELINE}
    return max(ml, key=lambda k: (ml[k]["accuracy"], ml[k]["f1_macro"]))


# ------------------------------------------------------------------- MLflow
def _mlflow():
    if not C.MODEL_MLFLOW:
        return None
    try:
        import mlflow
    except ImportError:
        print("[modelo] aviso: MLflow no está instalado; no se registran experimentos.")
        return None
    if C.MLFLOW_TRACKING_URI:
        # p. ej. "databricks://uvg-mlops": desde la Mac, registra en el MLflow
        # del workspace de Databricks usando el perfil del CLI.
        mlflow.set_tracking_uri(C.MLFLOW_TRACKING_URI)
        if C.MLFLOW_TRACKING_URI.startswith("databricks"):
            perfil = C.MLFLOW_TRACKING_URI.partition("://")[2]
            mlflow.set_registry_uri(f"databricks-uc://{perfil}" if perfil else "databricks-uc")
    elif C.BACKEND == "local":
        mlflow.set_tracking_uri(f"sqlite:///{C.ROOT / 'mlflow.db'}")
    else:
        mlflow.set_registry_uri("databricks-uc")
    mlflow.set_experiment(C.MLFLOW_EXPERIMENT)
    return mlflow


def _log_model(mlflow, pipe, ejemplo: pd.DataFrame, registrar: str | None):
    import mlflow.sklearn

    # cloudpickle: el formato por defecto de MLflow 3 (skops) rechaza árboles y bosques.
    kwargs = {"input_example": ejemplo, "serialization_format": "cloudpickle"}
    if registrar:
        kwargs["registered_model_name"] = registrar
    try:  # MLflow 3 usa `name`; MLflow 2 usa `artifact_path`
        mlflow.sklearn.log_model(pipe, name="modelo_direccion", **kwargs)
    except TypeError:
        mlflow.sklearn.log_model(pipe, artifact_path="modelo_direccion", **kwargs)


def registrar_en_mlflow(resultados, modelos, elegido, train, test) -> dict[str, str]:
    """Una corrida por modelo (anidadas en una corrida padre). Devuelve run_ids."""
    mlflow = _mlflow()
    if mlflow is None:
        return {}
    run_ids = {}
    comunes = {
        "features": ",".join(FEATURES), "umbral_direccion_q": C.DIRECCION_UMBRAL,
        "test_fraccion": C.MODEL_TEST_FRACTION, "n_train": len(train), "n_test": len(test),
        "semanas_test_desde": str(test["semana"].min().date()),
        "semanas_test_hasta": str(test["semana"].max().date()),
    }
    with mlflow.start_run(run_name=f"direccion_{datetime.now():%Y%m%d_%H%M}") as padre:
        mlflow.log_params(comunes)
        mlflow.set_tags({"equipo": C.TEAM, "proyecto": "cc3105-gasolina-gt"})
        mlflow.log_param("modelo_elegido", elegido)
        mlflow.log_metric("accuracy_elegido", resultados[elegido]["accuracy"])
        mlflow.log_metric("accuracy_baseline", resultados[BASELINE]["accuracy"])
        run_ids["padre"] = padre.info.run_id
        for nombre, met in resultados.items():
            with mlflow.start_run(run_name=nombre, nested=True) as run:
                mlflow.set_tags({"equipo": C.TEAM, "elegido": str(nombre == elegido).lower(),
                                 "es_baseline": str(nombre == BASELINE).lower()})
                mlflow.log_params({"modelo": nombre, **comunes})
                mlflow.log_metrics({k: v for k, v in met.items() if v is not None})
                if nombre in modelos:
                    clf = modelos[nombre].named_steps["clf"]
                    mlflow.log_params({f"hp_{k}": v for k, v in clf.get_params().items()
                                       if isinstance(v, (int, float, str, bool)) or v is None})
                    registrar = C.MLFLOW_REGISTERED_MODEL if nombre == elegido else None
                    try:
                        _log_model(mlflow, modelos[nombre], train[FEATURES].head(3), registrar)
                    except Exception as exc:  # registrar no debe tumbar el Job
                        print(f"[modelo] aviso: no se pudo guardar/registrar {nombre}: {str(exc)[:200]}")
                run_ids[nombre] = run.info.run_id
    return run_ids


# --------------------------------------------------------------- tablas Oro
def tabla_predicciones(test, preds_test, final, futuras, elegido, ahora) -> pd.DataFrame:
    y_val, p_val = preds_test[elegido]
    val = pd.DataFrame({
        "semana": test["semana_objetivo"].to_numpy(),
        "semana_base": test["semana"].to_numpy(),
        "combustible": test["combustible"].to_numpy(),
        "prediccion": y_val,
        "probabilidad": np.round(p_val, 4),
        "direccion_real": test[TARGET].to_numpy(),
        "tipo": "validacion",
    })
    proba_fut = final.predict_proba(futuras[FEATURES])
    fut = pd.DataFrame({
        "semana": (futuras["semana"] + timedelta(days=7)).to_numpy(),
        "semana_base": futuras["semana"].to_numpy(),
        "combustible": futuras["combustible"].to_numpy(),
        "prediccion": final.predict(futuras[FEATURES]),
        "probabilidad": np.round(proba_fut.max(axis=1), 4),
        "direccion_real": None,
        "tipo": "futura",
    })
    out = pd.concat([val, fut], ignore_index=True)
    out["acierto"] = np.where(out["direccion_real"].isna(), None,
                              out["prediccion"] == out["direccion_real"])
    out["modelo"] = elegido
    out["generado_en"] = ahora
    for c in ("semana", "semana_base"):
        out[c] = pd.to_datetime(out[c]).dt.date.astype(str)
    return out[["semana", "semana_base", "combustible", "prediccion", "probabilidad",
                "direccion_real", "acierto", "tipo", "modelo", "generado_en"]]


def tabla_metricas(resultados, elegido, train, test, run_ids, ahora) -> pd.DataFrame:
    base = resultados[BASELINE]["accuracy"]
    filas = []
    for nombre, met in resultados.items():
        filas.append({
            "modelo": nombre,
            "es_baseline": nombre == BASELINE,
            "elegido": nombre == elegido,
            **{k: (round(v, 4) if v is not None else None) for k, v in met.items()},
            "supera_baseline": None if nombre == BASELINE else bool(met["accuracy"] > base),
            "n_train": len(train),
            "n_test": len(test),
            "semanas_test_desde": str(test["semana"].min().date()),
            "semanas_test_hasta": str(test["semana"].max().date()),
            "mlflow_run_id": run_ids.get(nombre),
            "generado_en": ahora,
        })
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------- run
def run() -> pd.DataFrame | None:
    C.ensure_dirs()
    feats = preparar(io.read_df("gold.features_modelo"))
    etiquetadas = feats.dropna(subset=[TARGET]).reset_index(drop=True)
    # última semana observada de cada combustible: lo que se predice a futuro
    futuras = feats[feats[TARGET].isna()].groupby("combustible").tail(1).reset_index(drop=True)

    try:
        train, test = split_temporal(etiquetadas, C.MODEL_TEST_FRACTION)
    except ValueError as exc:
        print(f"[modelo] {exc} Etapa omitida.")
        return None
    if train[TARGET].nunique() < 2:
        print("[modelo] el entrenamiento tiene una sola clase; etapa omitida.")
        return None

    resultados, modelos, preds_test = evaluar(train, test)
    elegido = elegir(resultados)

    # Reentrenar el elegido con TODAS las semanas etiquetadas para predecir el futuro.
    final = candidatos()[elegido].fit(etiquetadas[FEATURES], etiquetadas[TARGET])
    modelos_log = {**modelos, elegido: final}
    run_ids = registrar_en_mlflow(resultados, modelos_log, elegido, train, test)

    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pred = tabla_predicciones(test, preds_test, final, futuras, elegido, ahora)
    metr = tabla_metricas(resultados, elegido, train, test, run_ids, ahora)
    io.write_df(pred, "gold.predicciones")
    io.write_df(metr, "gold.metricas_modelo")

    for nombre, met in resultados.items():
        marca = " <- elegido" if nombre == elegido else ""
        print(f"[modelo] {nombre:22s} accuracy={met['accuracy']:.3f} f1={met['f1_macro']:.3f}{marca}")
    gana = resultados[elegido]["accuracy"] > resultados[BASELINE]["accuracy"]
    print(f"[modelo] train={len(train)} test={len(test)} filas | "
          f"{'SUPERA' if gana else 'NO supera'} a la línea base")
    print(f"[modelo] predicciones -> {io.target_name('gold.predicciones')} ({len(pred)} filas)")
    print(f"[modelo] métricas     -> {io.target_name('gold.metricas_modelo')}")
    print(pred[pred["tipo"] == "futura"][["semana", "combustible", "prediccion", "probabilidad"]]
          .to_string(index=False))
    return pred


if __name__ == "__main__":
    run()
