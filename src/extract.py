
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config as C

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    _HEIF_OK = True
except Exception:  
    _HEIF_OK = False

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


@dataclass
class ExifData:
    image_id: str
    file_name: str
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    pixel_w: Optional[int] = None
    pixel_h: Optional[int] = None
    ts_local: Optional[datetime] = None   
    ts_utc: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None
    gps_direction: Optional[float] = None


def read_exif(path: Path) -> ExifData:
    if not _HEIF_OK:
        raise RuntimeError(
            "Error de pillow"
        )
    image_id = path.stem
    ex_data = ExifData(image_id=image_id, file_name=path.name)

    with Image.open(path) as im:
        ex_data.pixel_w, ex_data.pixel_h = im.size
        exif = im.getexif()
        base = {TAGS.get(k, k): v for k, v in exif.items()}
        ex_data.camera_make = base.get("Make")
        ex_data.camera_model = base.get("Model")

        exif_ifd = exif.get_ifd(IFD.Exif)
        exif_ifd = {TAGS.get(k, k): v for k, v in exif_ifd.items()}
        dt_str = exif_ifd.get("DateTimeOriginal") or base.get("DateTime")
        if dt_str:
            try:
                ts_local = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                ex_data.ts_local = ts_local
                ex_data.ts_utc = ts_local - timedelta(hours=C.LOCAL_UTC_OFFSET_HOURS)
            except ValueError:
                pass

        # GPS
        gps_ifd = exif.get_ifd(IFD.GPSInfo)
        if gps_ifd:
            g = {GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}
            ex_data.latitude = _dms_to_deg(g.get("GPSLatitude"), g.get("GPSLatitudeRef", "N"))
            ex_data.longitude = _dms_to_deg(g.get("GPSLongitude"), g.get("GPSLongitudeRef", "E"))
            if g.get("GPSAltitude") is not None:
                alt = float(g["GPSAltitude"])
                if g.get("GPSAltitudeRef") in (1, b"\x01"): 
                    alt = -alt
                ex_data.altitude_m = alt
            if g.get("GPSImgDirection") is not None:
                ex_data.gps_direction = float(g["GPSImgDirection"])

    return ex_data


@dataclass
class DisplayReading:
    image_id: str
    esta_venta: Optional[float] = None
    esta_venta_conf: float = 0.0
    galones: Optional[float] = None
    galones_conf: float = 0.0
    fuel_pumped_guess: Optional[str] = None
    prices: dict = field(default_factory=dict)        
    prices_conf: dict = field(default_factory=dict)   


class DisplayReader:

    def read(self, image_id: str, path: Optional[Path] = None) -> DisplayReading:
        raise NotImplementedError


class VisionAnnotationReader(DisplayReader):
    def __init__(self, annotations_file: Path = C.ANNOTATIONS_FILE):
        with open(annotations_file, "r", encoding="utf-8") as f:
            self._doc = json.load(f)
        self._by_id = {r["image_id"]: r for r in self._doc["readings"]}

    def read(self, image_id: str, path: Optional[Path] = None) -> DisplayReading:
        r = self._by_id.get(image_id)
        if r is None:
            return DisplayReading(image_id=image_id)
        out = DisplayReading(
            image_id=image_id,
            esta_venta=r["esta_venta"]["value"],
            esta_venta_conf=r["esta_venta"]["confidence"],
            galones=r["galones"]["value"],
            galones_conf=r["galones"]["confidence"],
            fuel_pumped_guess=r.get("fuel_pumped_guess"),
        )
        for fuel in C.FUEL_TYPES:
            p = r["prices"].get(fuel)
            if p is not None:
                out.prices[fuel] = p["value"]
                out.prices_conf[fuel] = p["confidence"]
        return out



def run(reader: Optional[DisplayReader] = None) -> pd.DataFrame:
    C.ensure_dirs()
    reader = reader or VisionAnnotationReader()

    images = sorted(C.RAW_IMAGES_DIR.glob("*.HEIC")) + sorted(
        C.RAW_IMAGES_DIR.glob("*.heic")
    )
    if not images:
        raise FileNotFoundError(f"No se encontraron .HEIC en {C.RAW_IMAGES_DIR}")

    wide_rows = []
    long_rows = []

    for path in images:
        ex = read_exif(path)
        rd = reader.read(ex.image_id, path)

        row = {
            "image_id": ex.image_id,
            "file_name": ex.file_name,
            "camera_make": ex.camera_make,
            "camera_model": ex.camera_model,
            "pixel_w": ex.pixel_w,
            "pixel_h": ex.pixel_h,
            "ts_local": ex.ts_local,
            "ts_utc": ex.ts_utc,
            "latitude": ex.latitude,
            "longitude": ex.longitude,
            "altitude_m": ex.altitude_m,
            "gps_direction": ex.gps_direction,
            "esta_venta": rd.esta_venta,
            "esta_venta_conf": rd.esta_venta_conf,
            "galones": rd.galones,
            "galones_conf": rd.galones_conf,
            "fuel_pumped_guess": rd.fuel_pumped_guess,
        }
        for fuel in C.FUEL_TYPES:
            row[f"price_{fuel}"] = rd.prices.get(fuel)
            row[f"price_{fuel}_conf"] = rd.prices_conf.get(fuel, 0.0)
        wide_rows.append(row)

        def add_long(field_name, fuel, value, conf):
            long_rows.append(
                {
                    "image_id": ex.image_id,
                    "ts_local": ex.ts_local,
                    "field": field_name,
                    "fuel_type": fuel,
                    "value": value,
                    "confidence": conf,
                    "source": "vision",
                }
            )

        add_long("esta_venta", None, rd.esta_venta, rd.esta_venta_conf)
        add_long("galones", None, rd.galones, rd.galones_conf)
        for fuel in C.FUEL_TYPES:
            add_long("price", fuel, rd.prices.get(fuel), rd.prices_conf.get(fuel, 0.0))

    wide = pd.DataFrame(wide_rows).sort_values("ts_local").reset_index(drop=True)
    long = pd.DataFrame(long_rows)

    wide.to_csv(C.BRONZE_OBS, index=False)
    long.to_csv(C.BRONZE_LONG, index=False)
    print(f"[extract] {len(wide)} imagenes -> {C.BRONZE_OBS.relative_to(C.ROOT)}")
    print(f"[extract] {len(long)} lecturas  -> {C.BRONZE_LONG.relative_to(C.ROOT)}")
    return wide


if __name__ == "__main__":
    run()
