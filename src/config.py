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
}


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
}


def uc_table(dataset: str) -> str:
    m = DATASETS[dataset]
    return f"{UC_CATALOG}.{m['layer']}.{m['table']}"


def s3_path(dataset: str) -> str:
    m = DATASETS[dataset]
    bucket = S3_BUCKETS[m["layer"]]
    return f"s3://{bucket}/{TEAM}/{m['layer']}/{m['table']}"
