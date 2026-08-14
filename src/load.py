from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from . import config as C
from .transform import _station_id

SCHEMA = """
DROP VIEW  IF EXISTS v_precios_ancho;
DROP TABLE IF EXISTS precios_combustible;

CREATE TABLE precios_combustible (
    id                     INTEGER PRIMARY KEY,   -- sin AUTOINCREMENT (evita sqlite_sequence)
    fecha                  TEXT NOT NULL,         -- YYYY-MM-DD (eje temporal)
    fecha_hora_local       TEXT,                  -- timestamp local de la foto
    anio                   INTEGER,
    semana_iso             INTEGER,               -- semana del anio (los precios cambian por semana)
    id_estacion            TEXT,
    estacion               TEXT,
    pais                   TEXT,
    latitud                REAL,
    longitud               REAL,
    altitud_m              REAL,
    tipo_combustible       TEXT NOT NULL,         -- diesel / regular / super / v_power
    categoria              TEXT,                  -- gasolina / diesel
    precio_galon           REAL,                  -- Q/galon (objetivo del pronostico)
    precio_litro           REAL,                  -- Q/litro (misma info estandarizada)
    moneda                 TEXT,
    calidad_precio         TEXT,                  -- leido / reconciliado / imputado
    precio_galon_anterior  REAL,                  -- precio previo del mismo combustible
    variacion_abs          REAL,                  -- precio - precio_anterior
    variacion_pct          REAL,                  -- variacion porcentual
    dias_desde_anterior    INTEGER                -- dias entre observaciones
);

CREATE INDEX idx_precio_combustible_fecha ON precios_combustible(tipo_combustible, fecha);

-- Vista ancha: una columna por combustible (comoda para graficar y correlacionar)
CREATE VIEW v_precios_ancho AS
SELECT
    fecha_hora_local,
    MIN(fecha)       AS fecha,
    MIN(id_estacion) AS id_estacion,
    MAX(CASE WHEN tipo_combustible='diesel'  THEN precio_galon END) AS diesel,
    MAX(CASE WHEN tipo_combustible='regular' THEN precio_galon END) AS regular,
    MAX(CASE WHEN tipo_combustible='super'   THEN precio_galon END) AS super,
    MAX(CASE WHEN tipo_combustible='v_power' THEN precio_galon END) AS v_power
FROM precios_combustible
GROUP BY fecha_hora_local;
"""


def _build_dataset() -> pd.DataFrame:
    prices = pd.read_csv(C.SILVER_PRICES, parse_dates=["ts_local"])
    bronze = pd.read_csv(C.BRONZE_OBS)[["image_id", "latitude", "longitude", "altitude_m"]]

    df = prices.merge(bronze, on="image_id", how="left")

    out = pd.DataFrame()
    out["fecha_hora_local"] = df["ts_local"]
    out["fecha"] = df["ts_local"].dt.date.astype(str)
    out["anio"] = df["ts_local"].dt.year
    out["semana_iso"] = df["ts_local"].dt.isocalendar().week.astype(int)
    out["id_estacion"] = [
        _station_id(la, lo) for la, lo in zip(df["latitude"], df["longitude"])
    ]
    out["estacion"] = C.ESTACION_MARCA
    out["pais"] = C.PAIS
    out["latitud"] = df["latitude"].round(6)
    out["longitud"] = df["longitude"].round(6)
    out["altitud_m"] = df["altitude_m"].round(1)
    out["tipo_combustible"] = df["fuel_type"]
    out["categoria"] = df["fuel_category"]
    out["precio_galon"] = df["price_gtq_gal"]
    out["precio_litro"] = df["price_gtq_liter"]
    out["moneda"] = C.CURRENCY
    out["calidad_precio"] = df["status"].map(C.CALIDAD_PRECIO).fillna(df["status"])

    out = out.sort_values(["tipo_combustible", "fecha_hora_local"]).reset_index(drop=True)
    g = out.groupby("tipo_combustible", group_keys=False)
    out["precio_galon_anterior"] = g["precio_galon"].shift(1)
    out["variacion_abs"] = (out["precio_galon"] - out["precio_galon_anterior"]).round(C.PRICE_DECIMALS)
    out["variacion_pct"] = (
        (out["variacion_abs"] / out["precio_galon_anterior"] * 100).round(2)
    )
    dias = g["fecha_hora_local"].diff().dt.total_seconds() / 86400.0
    out["dias_desde_anterior"] = dias.round().astype("Int64")

    out = out.sort_values(["fecha_hora_local", "tipo_combustible"]).reset_index(drop=True)
    out.insert(0, "id", range(1, len(out) + 1))

    out["fecha_hora_local"] = out["fecha_hora_local"].astype(str)
    return out


def run() -> pd.DataFrame:
    C.ensure_dirs()
    dataset = _build_dataset()

    dataset.to_csv(C.GOLD_DATASET, index=False)

    with sqlite3.connect(C.DB_PATH) as conn:
        conn.executescript(SCHEMA)
        dataset.to_sql("precios_combustible", conn, if_exists="append", index=False)
        conn.commit()
        n = conn.execute("SELECT COUNT(*) FROM precios_combustible").fetchone()[0]
        nfuel = conn.execute(
            "SELECT COUNT(DISTINCT tipo_combustible) FROM precios_combustible"
        ).fetchone()[0]

    
    return dataset


if __name__ == "__main__":
    run()
