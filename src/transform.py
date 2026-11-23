
from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from . import config as C, io_layer as io, vision

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:
    pass

from PIL import Image
from PIL.ExifTags import IFD, TAGS, GPSTAGS


def _dms_to_deg(dms, ref: str) -> Optional[float]:
    if not dms:
        return None
    d, m, s = (float(x) for x in dms)
    val = d + m / 60.0 + s / 3600.0
    if ref in ("S", "W"):
        val = -val
    return val


def _read_exif(src) -> dict:
    out = {"ts_local": None, "latitude": None, "longitude": None}
    try:
        with Image.open(src) as im:
            exif = im.getexif()
            exif_ifd = {TAGS.get(k, k): v for k, v in exif.get_ifd(IFD.Exif).items()}
            base = {TAGS.get(k, k): v for k, v in exif.items()}
            dt_str = exif_ifd.get("DateTimeOriginal") or base.get("DateTime")
            if dt_str:
                try:
                    out["ts_local"] = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    pass
            gps = exif.get_ifd(IFD.GPSInfo)
            if gps:
                g = {GPSTAGS.get(k, k): v for k, v in gps.items()}
                out["latitude"] = _dms_to_deg(g.get("GPSLatitude"), g.get("GPSLatitudeRef", "N"))
                out["longitude"] = _dms_to_deg(g.get("GPSLongitude"), g.get("GPSLongitudeRef", "E"))
    except Exception as exc:
        print(f"[plata] aviso: no se pudo leer EXIF: {str(exc)[:120]}")
    return out


def _station_id(lat, lon) -> str:
    if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
        return "ST_DESCONOCIDA"
    la, lo = round(lat, C.STATION_GPS_DECIMALS), round(lon, C.STATION_GPS_DECIMALS)
    return f"ST_{la:.3f}_{lo:.3f}".replace("-", "m").replace(".", "p")


def _motivos_rechazo(fecha, combustible, precio) -> list[str]:
    hoy = datetime.now().date()
    motivos = []
    if precio is None or pd.isna(precio):
        motivos.append("venta_galones_ilegible")
    elif not (C.PRICE_MIN <= precio <= C.PRICE_MAX):
        motivos.append("precio_fuera_de_rango")
    if combustible not in C.FUEL_CATALOG:
        motivos.append("combustible_no_identificado")
    if fecha is None or (isinstance(fecha, float) and pd.isna(fecha)):
        motivos.append("fecha_nula")
    elif fecha > hoy:
        motivos.append("fecha_futura")
    return motivos


def _build_silver() -> tuple[pd.DataFrame, pd.DataFrame]:
    bronze = io.read_df("bronze.fotos_precios")
    reader = vision.make_reader()

    filas = []
    for _, row in bronze.iterrows():
        image_id = str(row["_source_file"]).rsplit("/", 1)[-1].rsplit(".", 1)[0]
        exif = _read_exif(io.open_photo(row))
        ts = exif["ts_local"]
        fecha = ts.date() if ts is not None else None
        ubicacion = _station_id(exif["latitude"], exif["longitude"])

        img_bytes = io.photo_bytes(row) if C.VISION_MODE == "endpoint" else None
        reading = reader.read(image_id, img_bytes)
        venta, galones = reading.get("esta_venta"), reading.get("galones")
        efectivo = (
            round(venta / galones, C.PRICE_DECIMALS)
            if (venta and galones and galones > 0) else None
        )
        combustible = vision.asignar_combustible(
            efectivo, reading.get("prices") or {}, reading.get("fuel_pumped_guess")
        )

        filas.append({
            "fecha": fecha,
            "combustible": combustible,
            "precio_q_galon": efectivo,
            "modalidad": C.MODALIDAD_DEFAULT,
            "ubicacion": ubicacion,
            "foto_origen": row["_source_file"],
            "esta_venta": venta,
            "galones": galones,
            "image_id": image_id,
            "ts_local": ts,
        })

    df = pd.DataFrame(filas)
    df["_motivos"] = df.apply(
        lambda r: _motivos_rechazo(r["fecha"], r["combustible"], r["precio_q_galon"]), axis=1
    )
    ok = df["_motivos"].map(len) == 0

    cols = ["fecha", "combustible", "precio_q_galon", "modalidad", "ubicacion",
            "foto_origen", "esta_venta", "galones", "image_id", "ts_local"]
    aceptados = df.loc[ok, cols].reset_index(drop=True)
    rechazados = df.loc[~ok, cols].copy()
    rechazados["motivo_rechazo"] = df.loc[~ok, "_motivos"].map(lambda ms: ";".join(ms))
    rechazados = rechazados.reset_index(drop=True)

    for frame in (aceptados, rechazados):
        frame["fecha"] = frame["fecha"].astype(str)
        frame["ts_local"] = frame["ts_local"].astype(str)
        for c in ("precio_q_galon", "esta_venta", "galones"):
            frame[c] = pd.to_numeric(frame[c], errors="coerce")
    return aceptados, rechazados


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    C.ensure_dirs()
    aceptados, rechazados = _build_silver()

    io.merge_df(aceptados, "silver.precios",
                keys=["fecha", "ubicacion", "combustible", "modalidad"])
    io.merge_df(rechazados, "silver.precios_rejected",
                keys=["foto_origen"])

    print(f"[plata] {len(aceptados)} precios -> {io.target_name('silver.precios')} "
          f"| {len(rechazados)} rechazados -> {io.target_name('silver.precios_rejected')}")
    if not rechazados.empty:
        print("[plata] motivos:", rechazados["motivo_rechazo"].value_counts().to_dict())
    return aceptados, rechazados


if __name__ == "__main__":
    run()
