from __future__ import annotations

import os
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

BRONZE_OBS = BRONZE_DIR / "observations_raw.csv"       
BRONZE_LONG = BRONZE_DIR / "readings_long.csv"         
SILVER_FILLUPS = SILVER_DIR / "fill_ups_clean.csv"     
SILVER_PRICES = SILVER_DIR / "fuel_prices_clean.csv"   
GOLD_DATASET = GOLD_DIR / "dataset_precios.csv"        

CURRENCY = "GTQ"                 
VOLUME_UNIT = "gallon"
LITERS_PER_GALLON = 3.785411784  
PAIS = "Guatemala"               
ESTACION_MARCA = "Shell"         

CALIDAD_PRECIO = {
    "trusted": "leido",          
    "reconciled": "reconciliado",  
    "imputed": "imputado",       
    "missing": "faltante",       
}

FUEL_TYPES = ["diesel", "regular", "super", "v_power"]

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
GALLONS_MIN, GALLONS_MAX = 0.5, 60.0
SALE_MIN, SALE_MAX = 20.0, 5000.0

RECON_ABS_TOL = 0.15   

IQR_K = 1.5

PRICE_DECIMALS = 2
GALLONS_DECIMALS = 3

STATION_GPS_DECIMALS = 3

def ensure_dirs() -> None:
    # Las carpetas locales solo tienen sentido en el backend local; en
    # Databricks los destinos son tablas/volúmenes, no carpetas del disco.
    if BACKEND != "local":
        return
    for d in (BRONZE_DIR, SILVER_DIR, GOLD_DIR, REPORTS_DIR, FIGURES_DIR, DB_PATH.parent):
        d.mkdir(parents=True, exist_ok=True)


BACKEND = os.environ.get("PIPELINE_BACKEND", "local").strip().lower()   
TEAM = os.environ.get("PIPELINE_TEAM", "equipo3").strip()
UC_CATALOG = os.environ.get("PIPELINE_UC_CATALOG", "workspace").strip()

_DEFAULT_IMAGES_DIR = (
    str(RAW_IMAGES_DIR) if BACKEND == "local" else "/Volumes/workspace/bronze/raw_images"
)
IMAGES_DIR = Path(os.environ.get("PIPELINE_IMAGES_DIR", _DEFAULT_IMAGES_DIR))

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
    "bronze.observaciones":     {"layer": "bronze", "table": "observaciones",       "csv": BRONZE_OBS},
    "bronze.lecturas_long":     {"layer": "bronze", "table": "lecturas_long",       "csv": BRONZE_LONG},
    "silver.precios":           {"layer": "silver", "table": "precios",             "csv": SILVER_PRICES},
    "silver.transacciones":     {"layer": "silver", "table": "transacciones",       "csv": SILVER_FILLUPS},
    "gold.precios_combustible": {"layer": "gold",   "table": "precios_combustible", "csv": GOLD_DATASET},
}


def uc_table(dataset: str) -> str:
    m = DATASETS[dataset]
    return f"{UC_CATALOG}.{m['layer']}.{m['table']}"


def s3_path(dataset: str) -> str:
    m = DATASETS[dataset]
    bucket = S3_BUCKETS[m["layer"]]
    return f"s3a://{bucket}/{TEAM}/{m['layer']}/{m['table']}"
