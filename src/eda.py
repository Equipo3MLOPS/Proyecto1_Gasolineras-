from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import seaborn as sns

    sns.set_theme(style="whitegrid")
    _SNS = True
except Exception:  
    _SNS = False

from . import config as C

PRICE_COLS = [f"price_{f}" for f in C.FUEL_TYPES]
CONF_COLS = [f"price_{f}_conf" for f in C.FUEL_TYPES]


def _load_bronze() -> pd.DataFrame:
    df = pd.read_csv(C.BRONZE_OBS, parse_dates=["ts_local", "ts_utc"])
    return df.sort_values("ts_local").reset_index(drop=True)

def _fig_confidence_heatmap(df: pd.DataFrame) -> Path:
    conf = df.set_index("image_id")[CONF_COLS]
    conf.columns = C.FUEL_TYPES
    fig, ax = plt.subplots(figsize=(7, 3.6))
    if _SNS:
        sns.heatmap(
            conf, annot=True, fmt=".2f", cmap="RdYlGn", vmin=0, vmax=1,
            linewidths=0.5, cbar_kws={"label": "confianza"}, ax=ax,
        )
    else:
        im = ax.imshow(conf.values, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(conf.columns)));  ax.set_xticklabels(conf.columns)
        ax.set_yticks(range(len(conf.index)));     ax.set_yticklabels(conf.index)
        fig.colorbar(im, ax=ax, label="confianza")
    ax.axhline(0, color="none")
    ax.set_title(f"Confianza de lectura por precio\n(umbral = {C.CONFIDENCE_MIN}: rojo = se trata como nulo)")
    ax.set_xlabel("combustible"); ax.set_ylabel("imagen")
    out = C.FIGURES_DIR / "01_confidence_heatmap.png"
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)
    return out


def _fig_reconciliation(df: pd.DataFrame) -> Path:
    d = df.copy()
    d["precio_efectivo"] = d["esta_venta"] / d["galones"]
    d["residual_super"] = d["precio_efectivo"] - d["price_super"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    ax1.plot(d["ts_local"], d["precio_efectivo"], "o-", label="precio efectivo = venta/galones")
    ax1.plot(d["ts_local"], d["price_super"], "s--", label="precio Super leido")
    ax1.set_title("Reconciliacion: precio efectivo vs Super leido")
    ax1.set_ylabel(f"{C.CURRENCY} / galon"); ax1.legend(); ax1.tick_params(axis="x", rotation=30)

    ax2.bar(d["image_id"], d["residual_super"], color="#4C72B0")
    ax2.axhline(C.RECON_ABS_TOL, ls=":", color="red")
    ax2.axhline(-C.RECON_ABS_TOL, ls=":", color="red", label=f"tolerancia +/-{C.RECON_ABS_TOL}")
    ax2.set_title("Residual de reconciliacion (efectivo - Super)")
    ax2.set_ylabel(f"{C.CURRENCY}/galon"); ax2.legend(); ax2.tick_params(axis="x", rotation=30)
    out = C.FIGURES_DIR / "02_reconciliation.png"
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)
    return out


def _fig_price_trends(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for fuel in C.FUEL_TYPES:
        col = f"price_{fuel}"
        conf = df[f"price_{fuel}_conf"]
        ax.plot(df["ts_local"], df[col], "-", alpha=0.4, color="gray", zorder=1)
        hi = conf >= C.CONFIDENCE_MIN
        ax.scatter(df["ts_local"][hi], df[col][hi], label=f"{fuel} (confiable)", zorder=3)
        ax.scatter(df["ts_local"][~hi], df[col][~hi], facecolors="none",
                   edgecolors="red", zorder=3)
    ax.set_title("Evolucion de precios por combustible\n(circulo rojo hueco = lectura de baja confianza)")
    ax.set_ylabel(f"{C.CURRENCY} / galon"); ax.set_xlabel("fecha")
    ax.legend(fontsize=8, ncol=2); ax.tick_params(axis="x", rotation=30)
    out = C.FIGURES_DIR / "03_price_trends.png"
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)
    return out


def _fig_variacion_semanal(df: pd.DataFrame) -> Path:
    d = df.sort_values("ts_local")
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    x = np.arange(1, len(d))
    width = 0.2
    for i, fuel in enumerate(C.FUEL_TYPES):
        diffs = d[f"price_{fuel}"].diff().iloc[1:].to_numpy()
        ax.bar(x + (i - 1.5) * width, diffs, width, label=fuel)
    labels = [f"{a:%m-%d}\n->{b:%m-%d}" for a, b in zip(d["ts_local"][:-1], d["ts_local"][1:])]
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Variacion de precio entre visitas consecutivas\n(sube y luego se estabiliza -> senal de cuando conviene comprar)")
    ax.set_ylabel(f"cambio ({C.CURRENCY}/galon)"); ax.legend(fontsize=8, ncol=4)
    out = C.FIGURES_DIR / "04_variacion_semanal.png"
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)
    return out


def _fig_correlacion(df: pd.DataFrame) -> Path:
    corr = df[PRICE_COLS].copy()
    corr.columns = C.FUEL_TYPES
    corr = corr.corr()
    fig, ax = plt.subplots(figsize=(5.5, 4.6))
    if _SNS:
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1,
                    linewidths=0.5, square=True, cbar_kws={"label": "correlacion"}, ax=ax)
    else:
        im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr))); ax.set_xticklabels(corr.columns, rotation=45)
        ax.set_yticks(range(len(corr))); ax.set_yticklabels(corr.columns)
        fig.colorbar(im, ax=ax, label="correlacion")
    ax.set_title("Correlacion entre precios de combustibles")
    out = C.FIGURES_DIR / "05_correlacion.png"
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)
    return out

def _diagnostics(df: pd.DataFrame) -> dict:
    d = df.copy()
    d["precio_efectivo"] = d["esta_venta"] / d["galones"]
    d["residual_super"] = d["precio_efectivo"] - d["price_super"]

    low_conf = {}
    for fuel in C.FUEL_TYPES:
        mask = df[f"price_{fuel}_conf"] < C.CONFIDENCE_MIN
        low_conf[fuel] = df.loc[mask, "image_id"].tolist()

    ladder_viol = []
    for _, r in df.iterrows():
        seq = [r[f"price_{f}"] for f in C.GASOLINE_LADDER]
        if any(pd.notna(seq[i]) and pd.notna(seq[i + 1]) and seq[i] > seq[i + 1]
               for i in range(len(seq) - 1)):
            ladder_viol.append(r["image_id"])

    range_out = {}
    for fuel in C.FUEL_TYPES:
        col = f"price_{fuel}"
        mask = (df[col] < C.PRICE_MIN) | (df[col] > C.PRICE_MAX)
        if mask.any():
            range_out[fuel] = df.loc[mask, "image_id"].tolist()

    recon_bad = d.loc[d["residual_super"].abs() > C.RECON_ABS_TOL, "image_id"].tolist()

    corr = df[PRICE_COLS].rename(columns=dict(zip(PRICE_COLS, C.FUEL_TYPES))).corr().round(3)
    total_change = {}
    dd = df.sort_values("ts_local")
    for fuel in C.FUEL_TYPES:
        s = dd[f"price_{fuel}"].dropna()
        if len(s) >= 2:
            total_change[fuel] = round(s.iloc[-1] - s.iloc[0], 2)

    return {
        "n_images": len(df),
        "date_min": df["ts_local"].min(),
        "date_max": df["ts_local"].max(),
        "n_stations": df[["latitude", "longitude"]].round(C.STATION_GPS_DECIMALS).drop_duplicates().shape[0],
        "low_conf": low_conf,
        "ladder_viol": ladder_viol,
        "range_out": range_out,
        "recon_bad": recon_bad,
        "recon_table": d[["image_id", "esta_venta", "galones", "precio_efectivo",
                          "price_super", "residual_super"]],
        "price_summary": df[PRICE_COLS].describe().round(2),
        "corr": corr,
        "total_change": total_change,
    }

def run() -> Path:
    C.ensure_dirs()
    df = _load_bronze()
    figs = [
        _fig_confidence_heatmap(df),
        _fig_reconciliation(df),
        _fig_price_trends(df),
        _fig_variacion_semanal(df),
        _fig_correlacion(df),
    ]
    _diagnostics(df)

if __name__ == "__main__":
    run()
