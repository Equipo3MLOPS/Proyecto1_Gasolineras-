from __future__ import annotations

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
    for d in (BRONZE_DIR, SILVER_DIR, GOLD_DIR, REPORTS_DIR, FIGURES_DIR, DB_PATH.parent):
        d.mkdir(parents=True, exist_ok=True)
