from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RAW_IMAGES_DIR = ROOT / "Data"
ANNOTATIONS_FILE = ROOT / "annotations" / "vision_readings.json"

BRONZE_DIR = ROOT / "artifacts" / "bronze"
SILVER_DIR = ROOT / "artifacts" / "silver"
GOLD_DIR = ROOT / "artifacts" / "gold"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DB_PATH = ROOT / "db" / "gasolineras.db"

CURRENCY = "GTQ"
VOLUME_UNIT = "gallon"
LITERS_PER_GALLON = 3.785411784
PAIS = "Guatemala"
ESTACION_MARCA = "Shell"

FUEL_TYPES = ["diesel", "regular", "super", "v_power"]
FUEL_CATALOG = set(FUEL_TYPES)

FUEL_DISPLAY_NAME = {
    "diesel": "Shell Diesel",
    "regular": "Shell FuelSave Regular",
    "super": "Shell FuelSave Super",
    "v_power": "Shell V-Power",
}

FUEL_CATEGORY = {
    "diesel": "diesel",
    "regular": "gasolina",
    "super": "gasolina",
    "v_power": "gasolina",
}

GASOLINE_LADDER = ["regular", "super", "v_power"]

LOCAL_UTC_OFFSET_HOURS = -6

CONFIDENCE_MIN = 0.70
PRICE_MIN, PRICE_MAX = 20.0, 60.0          
MODALIDAD_DEFAULT = "no_especificada"      



DIRECCION_UMBRAL = 0.10

# --- Modelo de dirección (src/model.py) -----------------------------------
# Fracción de las semanas más recientes que se reserva para la validación temporal.
MODEL_TEST_FRACTION = float(os.environ.get("MODEL_TEST_FRACTION", "0.3"))
# "0" desactiva MLflow (útil en tests).
MODEL_MLFLOW = os.environ.get("MODEL_MLFLOW", "1").strip() not in ("0", "false", "no")
MLFLOW_EXPERIMENT = os.environ.get(
    "MLFLOW_EXPERIMENT_PATH", "/Shared/equipo3_gasolina_direccion"
).strip()
# Vacío = automático (sqlite local o el MLflow del workspace dentro de Databricks).
# "databricks://<perfil>" registra en Databricks desde la Mac.
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "").strip() or None

PRICE_DECIMALS = 2
STATION_GPS_DECIMALS = 3


def semana_inicio(d: date) -> date:

    return d - timedelta(days=(d.weekday() - 1) % 7)


def ensure_dirs() -> None:
    
    
    if BACKEND != "local":
        return
    for dpath in (BRONZE_DIR, SILVER_DIR, GOLD_DIR, REPORTS_DIR, FIGURES_DIR, DB_PATH.parent):
        dpath.mkdir(parents=True, exist_ok=True)


BACKEND = os.environ.get("PIPELINE_BACKEND", "local").strip().lower()   
TEAM = os.environ.get("PIPELINE_TEAM", "equipo3").strip()
UC_CATALOG = os.environ.get("PIPELINE_UC_CATALOG", "workspace").strip()



VISION_MODE = os.environ.get("PIPELINE_VISION", "json").strip().lower()
VISION_ENDPOINT = os.environ.get("PIPELINE_VISION_ENDPOINT", "databricks-llama-4-maverick").strip()

_DEFAULT_IMAGES_DIR = (
    str(RAW_IMAGES_DIR) if BACKEND == "local" else "/Volumes/workspace/bronze/raw_images"
)


IMAGES_URI = os.environ.get("PIPELINE_IMAGES_DIR", _DEFAULT_IMAGES_DIR)
IMAGES_DIR = Path(IMAGES_URI)

_DEFAULT_ANNOTATIONS = (
    str(ANNOTATIONS_FILE)
    if BACKEND == "local"
    else "/Volumes/workspace/bronze/raw_images/vision_readings.json"
)
ANNOTATIONS_PATH = Path(os.environ.get("PIPELINE_ANNOTATIONS", _DEFAULT_ANNOTATIONS))

if BACKEND != "local":
    FIGURES_DIR = Path(os.environ.get("PIPELINE_FIGURES_DIR", "/Volumes/workspace/gold/figuras"))

S3_BUCKETS = {
    "raw":    os.environ.get("S3_BUCKET_RAW",    "cc3105-raw-869227452861-us-east-2-an"),
    "bronze": os.environ.get("S3_BUCKET_BRONZE", "cc3105-cusn-869227452861-us-east-2-an"),
    "silver": os.environ.get("S3_BUCKET_SILVER", "cc3105-ag-869227452861-us-east-2-an"),
    "gold":   os.environ.get("S3_BUCKET_GOLD",   "cc3105-au-869227452861-us-east-2-an"),
}




DATASETS = {
    "bronze.fotos_precios": {
        "layer": "bronze", "table": "fotos_precios", "csv": BRONZE_DIR / "fotos_precios.csv",
        "comment": "Bronce: una fila por foto con contenido binario y columnas de auditoria (path, modificationTime, length, _source_file, _ingestion_timestamp).",
    },
    "silver.precios": {
        "layer": "silver", "table": "precios", "csv": SILVER_DIR / "precios.csv",
        "comment": "Plata: un precio limpio por fecha, ubicacion, combustible y modalidad (extraido de las fotos y validado).",
    },
    "silver.precios_rejected": {
        "layer": "silver", "table": "precios_rejected", "csv": SILVER_DIR / "precios_rejected.csv",
        "comment": "Plata: filas que no pasaron las reglas de calidad, con el motivo del rechazo.",
    },
    "gold.precio_semanal": {
        "layer": "gold", "table": "precio_semanal", "csv": GOLD_DIR / "precio_semanal.csv",
        "comment": "Oro: precio promedio, minimo y maximo por semana (martes a lunes) y combustible.",
    },
    "gold.variacion_semanal": {
        "layer": "gold", "table": "variacion_semanal", "csv": GOLD_DIR / "variacion_semanal.csv",
        "comment": "Oro: variacion en quetzales y % contra la semana anterior, con etiqueta de direccion (sube/baja/se_mantiene).",
    },
    "gold.features_modelo": {
        "layer": "gold", "table": "features_modelo", "csv": GOLD_DIR / "features_modelo.csv",
        "comment": "Oro: variables por semana y combustible para predecir la direccion de la semana siguiente (entrada del modelo).",
    },
    "gold.predicciones": {
        "layer": "gold", "table": "predicciones", "csv": GOLD_DIR / "predicciones.csv",
        "comment": "Oro: prediccion de la direccion (sube/baja/se_mantiene) por combustible y semana, con su probabilidad y la direccion real cuando se conoce.",
    },
    "gold.metricas_modelo": {
        "layer": "gold", "table": "metricas_modelo", "csv": GOLD_DIR / "metricas_modelo.csv",
        "comment": "Oro: exactitud de cada modelo candidato y de la linea base en las semanas de validacion temporal.",
    },
}

# Modelo registrado en MLflow (Unity Catalog). Vacío = no se registra.
MLFLOW_REGISTERED_MODEL = os.environ.get(
    "MLFLOW_REGISTERED_MODEL",
    "" if BACKEND == "local" else f"{UC_CATALOG}.gold.modelo_direccion",
).strip() or None


COMENTARIOS_COLUMNAS = {
    "gold.precio_semanal": {
        "semana": "Martes que abre la semana (martes a lunes, igual que el MEM).",
        "anio": "Anio de la semana.",
        "semana_iso": "Numero de semana ISO.",
        "combustible": "Tipo de combustible: diesel/regular/super/v_power.",
        "precio_promedio": "Precio promedio Q/galon de la semana.",
        "precio_min": "Precio minimo Q/galon de la semana.",
        "precio_max": "Precio maximo Q/galon de la semana.",
        "n_observaciones": "Cantidad de fotos que aportaron a la semana.",
    },
    "gold.variacion_semanal": {
        "semana": "Martes que abre la semana.",
        "combustible": "Tipo de combustible.",
        "precio_promedio": "Precio promedio Q/galon de la semana.",
        "precio_promedio_anterior": "Precio promedio de la semana anterior.",
        "variacion_abs": "Diferencia en quetzales contra la semana anterior.",
        "variacion_pct": "Diferencia porcentual contra la semana anterior.",
        "direccion": "Etiqueta: sube / baja / se_mantiene (umbral +/-Q0.10).",
    },
    "gold.features_modelo": {
        "semana": "Martes que abre la semana.",
        "combustible": "Tipo de combustible.",
        "precio_promedio": "Precio promedio Q/galon de la semana (nivel actual).",
        "variacion_1s": "Variacion Q de esta semana vs la anterior.",
        "variacion_2s": "Variacion Q de hace 1 semana.",
        "variacion_3s": "Variacion Q de hace 2 semanas.",
        "variacion_4s": "Variacion Q de hace 3 semanas.",
        "promedio_movil_4s": "Promedio movil del precio en 4 semanas.",
        "dif_super_diesel": "Diferencia Q entre super y diesel esa semana (senal de mercado).",
        "direccion": "Direccion de ESTA semana (sube/baja/se_mantiene).",
        "direccion_siguiente": "OBJETIVO del modelo: direccion de la semana SIGUIENTE.",
    },
    "gold.predicciones": {
        "semana": "Semana que se predice (martes que la abre).",
        "semana_base": "Ultima semana con datos usada para predecir.",
        "combustible": "Tipo de combustible.",
        "prediccion": "Direccion predicha: sube / baja / se_mantiene.",
        "probabilidad": "Probabilidad que el modelo asigna a la direccion predicha (0-1).",
        "direccion_real": "Direccion observada; vacia si la semana aun no ocurre.",
        "acierto": "True si la prediccion coincide con la direccion real.",
        "tipo": "validacion (semanas de prueba) o futura (semana siguiente a la ultima observada).",
        "modelo": "Nombre del modelo elegido.",
        "generado_en": "Fecha y hora UTC en que se genero la prediccion.",
    },
    "gold.metricas_modelo": {
        "modelo": "Nombre del modelo o de la linea base.",
        "es_baseline": "True para la linea base (se repite la direccion de la semana anterior).",
        "elegido": "True para el modelo que se usa en las predicciones.",
        "accuracy": "Exactitud en las semanas de validacion temporal (0-1).",
        "f1_macro": "F1 promedio de las tres clases en validacion.",
        "accuracy_super": "Exactitud solo para gasolina super.",
        "accuracy_regular": "Exactitud solo para gasolina regular.",
        "accuracy_diesel": "Exactitud solo para diesel.",
        "supera_baseline": "True si la exactitud del modelo es mayor que la de la linea base.",
        "n_train": "Filas usadas para entrenar.",
        "n_test": "Filas usadas para validar.",
        "semanas_test_desde": "Primera semana de validacion.",
        "semanas_test_hasta": "Ultima semana de validacion.",
        "mlflow_run_id": "Corrida de MLflow donde quedo registrado.",
        "generado_en": "Fecha y hora UTC del entrenamiento.",
    },
}


def uc_table(dataset: str) -> str:
    m = DATASETS[dataset]
    return f"{UC_CATALOG}.{m['layer']}.{m['table']}"


def s3_path(dataset: str) -> str:
    m = DATASETS[dataset]
    bucket = S3_BUCKETS[m["layer"]]
    return f"s3://{bucket}/{TEAM}/{m['layer']}/{m['table']}"
