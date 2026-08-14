from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from . import config as C

def _load_bronze() -> pd.DataFrame:
    df = pd.read_csv(C.BRONZE_OBS, parse_dates=["ts_local", "ts_utc"])
    return df.sort_values("ts_local").reset_index(drop=True)


def _station_id(lat: float, lon: float) -> str:
    if pd.isna(lat) or pd.isna(lon):
        return "ST_UNKNOWN"
    la = round(lat, C.STATION_GPS_DECIMALS)
    lo = round(lon, C.STATION_GPS_DECIMALS)
    return f"ST_{la:.3f}_{lo:.3f}".replace("-", "m").replace(".", "p")

def _build_long_prices(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        venta = r["esta_venta"]
        galones = r["galones"]
        precio_efectivo = venta / galones if galones else np.nan

        guess = r.get("fuel_pumped_guess")
        fuel_pumped = None
        if pd.notna(precio_efectivo):
            gv = r.get(f"price_{guess}") if guess in C.FUEL_TYPES else None
            if guess in C.FUEL_TYPES and pd.notna(gv) and abs(gv - precio_efectivo) <= C.RECON_ABS_TOL:
                fuel_pumped = guess
            else:
                best = None  
                for fuel in C.FUEL_TYPES:
                    v = r.get(f"price_{fuel}")
                    if pd.notna(v):
                        key = (abs(v - precio_efectivo), -r.get(f"price_{fuel}_conf", 0.0))
                        if best is None or key < best[0]:
                            best = (key, fuel)
                fuel_pumped = best[1] if best else guess
        else:
            fuel_pumped = guess

        for fuel in C.FUEL_TYPES:
            rows.append(
                {
                    "image_id": r["image_id"],
                    "ts_local": r["ts_local"],
                    "date": r["ts_local"].date() if pd.notna(r["ts_local"]) else None,
                    "station_id": _station_id(r["latitude"], r["longitude"]),
                    "fuel_type": fuel,
                    "raw_value": r.get(f"price_{fuel}"),
                    "confidence": r.get(f"price_{fuel}_conf", 0.0),
                    "precio_efectivo": precio_efectivo,
                    "is_pumped": fuel == fuel_pumped,
                }
            )
    long = pd.DataFrame(rows)

    long["price_final"] = np.nan
    long["status"] = "missing"
    long["is_reconciled"] = False
    long["is_imputed"] = False
    long["impute_method"] = None

    for i, row in long.iterrows():
        if row["is_pumped"] and pd.notna(row["precio_efectivo"]):
            long.at[i, "price_final"] = row["precio_efectivo"]
            long.at[i, "status"] = "reconciled"
            long.at[i, "is_reconciled"] = True
        elif pd.notna(row["raw_value"]) and row["confidence"] >= C.CONFIDENCE_MIN:
            long.at[i, "price_final"] = row["raw_value"]
            long.at[i, "status"] = "trusted"
        else:
            long.at[i, "status"] = "missing"  

    long = long.sort_values(["fuel_type", "ts_local"]).reset_index(drop=True)
    for fuel in C.FUEL_TYPES:
        sub = long[long["fuel_type"] == fuel]
        anchors = sub[sub["status"].isin(["trusted", "reconciled"])]
        ax = anchors["ts_local"].map(lambda t: t.timestamp()).to_numpy()
        ay = anchors["price_final"].to_numpy()

        for idx in sub.index[sub["status"] == "missing"]:
            t = long.at[idx, "ts_local"].timestamp()
            left = ax[ax <= t]
            right = ax[ax >= t]
            method, val = "none", np.nan
            if left.size and right.size and left.max() != right.min():
                val = float(np.interp(t, ax, ay))
                method = "interp_time"
            elif pd.notna(long.at[idx, "raw_value"]) and (
                C.PRICE_MIN <= long.at[idx, "raw_value"] <= C.PRICE_MAX
            ):
                val = float(long.at[idx, "raw_value"])
                method = "weak_fallback"
            elif ax.size:
                val = float(ay[np.argmin(np.abs(ax - t))])
                method = "carry"
            long.at[idx, "price_final"] = val
            long.at[idx, "status"] = "imputed" if method != "none" else "missing"
            long.at[idx, "is_imputed"] = method != "none"
            long.at[idx, "impute_method"] = method if method != "none" else None

    long["is_range_outlier"] = (long["price_final"] < C.PRICE_MIN) | (
        long["price_final"] > C.PRICE_MAX
    )

    long["is_iqr_outlier"] = False
    for fuel in C.FUEL_TYPES:
        m = long["fuel_type"] == fuel
        vals = long.loc[m, "price_final"].dropna()
        if len(vals) >= 4:
            q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
            iqr = q3 - q1
            lo, hi = q1 - C.IQR_K * iqr, q3 + C.IQR_K * iqr
            long.loc[m, "is_iqr_outlier"] = (long.loc[m, "price_final"] < lo) | (
                long.loc[m, "price_final"] > hi
            )

    long["is_ladder_violation"] = False
    for img, g in long.groupby("image_id"):
        vals = {f: g.loc[g["fuel_type"] == f, "price_final"].iloc[0] for f in C.FUEL_TYPES}
        viol = False
        for a, b in zip(C.GASOLINE_LADDER, C.GASOLINE_LADDER[1:]):
            if pd.notna(vals[a]) and pd.notna(vals[b]) and vals[a] > vals[b] + 1e-9:
                viol = True
        if viol:
            long.loc[long["image_id"] == img, "is_ladder_violation"] = True

    long["price_gtq_gal"] = long["price_final"].round(C.PRICE_DECIMALS)
    long["price_gtq_liter"] = (long["price_final"] / C.LITERS_PER_GALLON).round(C.PRICE_DECIMALS)
    long["currency"] = C.CURRENCY
    long["fuel_category"] = long["fuel_type"].map(C.FUEL_CATEGORY)
    long["needs_review"] = (
        long["is_range_outlier"] | long["is_iqr_outlier"] | long["is_ladder_violation"]
    )

    cols = [
        "image_id", "ts_local", "date", "station_id", "fuel_type", "fuel_category",
        "price_gtq_gal", "price_gtq_liter", "currency",
        "raw_value", "confidence", "status", "is_reconciled", "is_imputed",
        "impute_method", "is_range_outlier", "is_iqr_outlier",
        "is_ladder_violation", "needs_review",
    ]
    return long[cols].sort_values(["ts_local", "fuel_type"]).reset_index(drop=True)


def _build_fillups(df: pd.DataFrame, long: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        venta, galones = r["esta_venta"], r["galones"]
        precio_efectivo = venta / galones if galones else np.nan
        img_prices = long[long["image_id"] == r["image_id"]]
        # combustible surtido = el marcado como reconciliado
        pumped = img_prices.loc[img_prices["is_reconciled"], "fuel_type"]
        fuel_pumped = pumped.iloc[0] if len(pumped) else r.get("fuel_pumped_guess")
        price_pumped = np.nan
        if fuel_pumped is not None:
            pp = img_prices.loc[img_prices["fuel_type"] == fuel_pumped, "price_gtq_gal"]
            price_pumped = pp.iloc[0] if len(pp) else np.nan
        residual = (precio_efectivo - price_pumped) if pd.notna(price_pumped) else np.nan

        flags = []
        if not (C.SALE_MIN <= venta <= C.SALE_MAX):
            flags.append("venta_fuera_rango")
        if not (C.GALLONS_MIN <= galones <= C.GALLONS_MAX):
            flags.append("galones_fuera_rango")
        if pd.notna(residual) and abs(residual) > C.RECON_ABS_TOL:
            flags.append("reconciliacion_alta")

        rows.append(
            {
                "image_id": r["image_id"],
                "station_id": _station_id(r["latitude"], r["longitude"]),
                "ts_local": r["ts_local"],
                "ts_utc": r["ts_utc"],
                "date": r["ts_local"].date() if pd.notna(r["ts_local"]) else None,
                "total_cost": round(venta, C.PRICE_DECIMALS),
                "gallons": round(galones, C.GALLONS_DECIMALS),
                "liters": round(galones * C.LITERS_PER_GALLON, 3),
                "fuel_pumped": fuel_pumped,
                "price_effective_gtq_gal": round(precio_efectivo, 4),
                "price_pumped_gtq_gal": price_pumped,
                "recon_residual": round(residual, 4) if pd.notna(residual) else np.nan,
                "currency": C.CURRENCY,
                "quality_flag": ";".join(flags) if flags else "ok",
            }
        )
    return pd.DataFrame(rows).sort_values("ts_local").reset_index(drop=True)


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    C.ensure_dirs()
    df = _load_bronze()
    long = _build_long_prices(df)
    fillups = _build_fillups(df, long)

    long.to_csv(C.SILVER_PRICES, index=False)
    fillups.to_csv(C.SILVER_FILLUPS, index=False)

    n_imp = int(long["is_imputed"].sum())
    n_rec = int(long["is_reconciled"].sum())
    n_rev = int(long["needs_review"].sum())
    print(f"[transform] precios limpios -> {C.SILVER_PRICES.relative_to(C.ROOT)} "
          f"({len(long)} filas; {n_rec} reconciliados, {n_imp} imputados, {n_rev} a revisar)")
    print(f"[transform] transacciones  -> {C.SILVER_FILLUPS.relative_to(C.ROOT)} "
          f"({len(fillups)} filas)")
    return fillups, long


if __name__ == "__main__":
    run()
