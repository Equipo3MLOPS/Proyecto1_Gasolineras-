
from __future__ import annotations

import base64
import io
import json
import os

from . import config as C

_PROMPT = (
    "Lees el display LCD de un surtidor Shell en Guatemala. Devuelve SOLO un JSON, "
    "sin texto extra: "
    '{"esta_venta": num, "galones": num, '
    '"fuel_pumped_guess": "diesel|regular|super|v_power", '
    '"prices": {"diesel": num_o_null, "regular": num_o_null, "super": num_o_null, '
    '"v_power": num_o_null}}. '
    "'esta_venta' es el monto grande en Quetzales; 'galones' es el otro monto grande; "
    "'fuel_pumped_guess' es el grado resaltado/seleccionado (el que se surtio). "
    "Los 4 'prices' son los LCD chicos de precio por galon (Q20-60); si uno esta "
    "borroso o cortado, usa null. No adivines."
)


def make_reader():
    if C.VISION_MODE == "endpoint":
        return EndpointReader()
    return JsonReader()


class JsonReader:
    def __init__(self, annotations_file=C.ANNOTATIONS_PATH):
        with open(annotations_file, "r", encoding="utf-8") as f:
            doc = json.load(f)
        self._by_id = {r["image_id"]: r for r in doc["readings"]}

    def read(self, image_id: str, img_bytes: bytes | None = None) -> dict:
        r = self._by_id.get(image_id)
        if r is None:
            return {}
        return {
            "esta_venta": r["esta_venta"]["value"],
            "galones": r["galones"]["value"],
            "fuel_pumped_guess": r.get("fuel_pumped_guess"),
            "prices": {f: (r["prices"].get(f) or {}).get("value") for f in C.FUEL_TYPES},
        }


class EndpointReader:
    def __init__(self):
        self.host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
        self.token = os.environ.get("DATABRICKS_TOKEN", "")
        self.endpoint = C.VISION_ENDPOINT

    def _b64_jpeg(self, img_bytes: bytes) -> str:
        import pillow_heif

        pillow_heif.register_heif_opener()
        from PIL import Image

        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        im.thumbnail((1600, 1600))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90)
        return base64.b64encode(buf.getvalue()).decode()

    def read(self, image_id: str, img_bytes: bytes | None = None) -> dict:
        import requests

        if not img_bytes:
            return {}
        payload = {
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": _PROMPT},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{self._b64_jpeg(img_bytes)}"}},
            ]}],
            "temperature": 0,
            "max_tokens": 400,
        }
        try:
            r = requests.post(
                f"{self.host}/serving-endpoints/{self.endpoint}/invocations",
                headers={"Authorization": f"Bearer {self.token}"},
                json=payload, timeout=120,
            )
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]
            data = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        except Exception as exc:
            print(f"[vision] fallo leyendo {image_id}: {str(exc)[:160]}")
            return {}
        prices = data.get("prices") or {}
        return {
            "esta_venta": data.get("esta_venta"),
            "galones": data.get("galones"),
            "fuel_pumped_guess": data.get("fuel_pumped_guess"),
            "prices": {f: prices.get(f) for f in C.FUEL_TYPES},
        }


def asignar_combustible(efectivo, prices: dict, guess) -> str | None:

    if efectivo is not None and prices:
        cand = [(abs(v - efectivo), f) for f, v in prices.items() if v is not None]
        if cand:
            return min(cand)[1]
    return guess if guess in C.FUEL_CATALOG else None
