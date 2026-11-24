from __future__ import annotations

import pandas as pd

from . import config as C, io_layer as io


def _direccion(var_abs) -> object:
    if pd.isna(var_abs):
        return None
    if var_abs > C.DIRECCION_UMBRAL:
        return "sube"
    if var_abs < -C.DIRECCION_UMBRAL:
        return "baja"
    return "se_mantiene"


def _precio_semanal(silver: pd.DataFrame) -> pd.DataFrame:
    g = silver.groupby(["semana", "combustible"])["precio_q_galon"]
    sem = g.agg(
        precio_promedio="mean", precio_min="min", precio_max="max",
        n_observaciones="count",
    ).reset_index()
    for c in ("precio_promedio", "precio_min", "precio_max"):
        sem[c] = sem[c].round(C.PRICE_DECIMALS)
    sem["anio"] = sem["semana"].map(lambda d: pd.Timestamp(d).year)
    sem["semana_iso"] = sem["semana"].map(lambda d: pd.Timestamp(d).isocalendar().week)
    return sem[["semana", "anio", "semana_iso", "combustible",
                "precio_promedio", "precio_min", "precio_max", "n_observaciones"]]


def _variacion_semanal(sem: pd.DataFrame) -> pd.DataFrame:
    v = sem[["semana", "combustible", "precio_promedio"]].sort_values(
        ["combustible", "semana"]
    ).reset_index(drop=True)
    v["precio_promedio_anterior"] = v.groupby("combustible")["precio_promedio"].shift(1)
    v["variacion_abs"] = (v["precio_promedio"] - v["precio_promedio_anterior"]).round(C.PRICE_DECIMALS)
    v["variacion_pct"] = (v["variacion_abs"] / v["precio_promedio_anterior"] * 100).round(2)
    v["direccion"] = v["variacion_abs"].map(_direccion)
    
    return v.dropna(subset=["precio_promedio_anterior"]).reset_index(drop=True)


def _features_modelo(sem: pd.DataFrame) -> pd.DataFrame:
    f = sem[["semana", "combustible", "precio_promedio"]].sort_values(
        ["combustible", "semana"]
    ).reset_index(drop=True)
    gb = f.groupby("combustible")
    f["variacion_1s"] = gb["precio_promedio"].diff().round(C.PRICE_DECIMALS)
    f["variacion_2s"] = f.groupby("combustible")["variacion_1s"].shift(1)
    f["variacion_3s"] = f.groupby("combustible")["variacion_1s"].shift(2)
    f["variacion_4s"] = f.groupby("combustible")["variacion_1s"].shift(3)
    f["promedio_movil_4s"] = (
        gb["precio_promedio"].transform(lambda s: s.rolling(4, min_periods=1).mean())
    ).round(C.PRICE_DECIMALS)

    
    piv = sem.pivot_table(index="semana", columns="combustible", values="precio_promedio")
    dif = (piv.get("super") - piv.get("diesel")).rename("dif_super_diesel").reset_index()
    f = f.merge(dif, on="semana", how="left")
    f["dif_super_diesel"] = f["dif_super_diesel"].round(C.PRICE_DECIMALS)

    f["direccion"] = f["variacion_1s"].map(_direccion)
    
    f["direccion_siguiente"] = f.groupby("combustible")["direccion"].shift(-1)
    return f[["semana", "combustible", "precio_promedio",
              "variacion_1s", "variacion_2s", "variacion_3s", "variacion_4s",
              "promedio_movil_4s", "dif_super_diesel",
              "direccion", "direccion_siguiente"]]


def run() -> pd.DataFrame:
    C.ensure_dirs()
    silver = io.read_df("silver.precios", parse_dates=["fecha"])
    silver["semana"] = pd.to_datetime(silver["fecha"]).dt.date.map(C.semana_inicio)

    sem = _precio_semanal(silver)
    var = _variacion_semanal(sem)
    feats = _features_modelo(sem)

    
    for frame in (sem, var, feats):
        frame["semana"] = frame["semana"].astype(str)

    io.write_df(sem, "gold.precio_semanal")
    io.write_df(var, "gold.variacion_semanal")
    io.write_df(feats, "gold.features_modelo")

    print(f"[oro] precio_semanal     -> {io.target_name('gold.precio_semanal')} ({len(sem)} filas)")
    print(f"[oro] variacion_semanal  -> {io.target_name('gold.variacion_semanal')} ({len(var)} filas)")
    print(f"[oro] features_modelo    -> {io.target_name('gold.features_modelo')} ({len(feats)} filas; "
          f"{feats['direccion_siguiente'].notna().sum()} con objetivo para entrenar)")
    return feats


if __name__ == "__main__":
    run()
