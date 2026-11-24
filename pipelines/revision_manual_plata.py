# Databricks notebook source
# MAGIC %md
# MAGIC # Revisión manual de la extracción (capa Plata)
# MAGIC
# MAGIC El enunciado pide revisar a mano al menos 20 fotos y reportar el porcentaje de precios
# MAGIC extraídos correctamente. Este notebook:
# MAGIC
# MAGIC 1. Resume Plata: fotos procesadas, aceptadas, rechazadas y motivos de rechazo.
# MAGIC 2. Elige 20 fotos al azar de Bronce (semilla fija) y muestra cada una junto a lo que leyó
# MAGIC    el modelo de visión: venta, galones, precio efectivo y combustible asignado.
# MAGIC 3. Recibe tus correcciones (celda **Hoja de revisión**) y calcula la exactitud.
# MAGIC 4. Guarda el detalle en `silver.revision_manual` e imprime el párrafo para el informe (sección 2.3).
# MAGIC
# MAGIC **Cómo revisar:** en cada foto, lee primero el display (venta, galones y el grado iluminado) y
# MAGIC después compáralo con la ficha. Así no te dejas llevar por lo que leyó el modelo.
# MAGIC Solo anotas las fotos donde algo está mal.
# MAGIC
# MAGIC No modifica ninguna tabla del pipeline: solo lee Bronce y Plata y escribe su propia tabla.

# COMMAND ----------

# MAGIC %pip install pillow-heif

# COMMAND ----------

# pillow-heif (lectura de .HEIC) no viene en el runtime; tras instalarlo hay que reiniciar Python.
dbutils.library.restartPython()  # type: ignore[name-defined]

# COMMAND ----------

# Parámetros (widgets). Aceptan un nombre de tabla de Unity Catalog o una ruta Delta s3://...
dbutils.widgets.text("tabla_bronce", "workspace.bronze.fotos_precios")  # type: ignore[name-defined]
dbutils.widgets.text("tabla_plata", "workspace.silver.precios")  # type: ignore[name-defined]
dbutils.widgets.text("tabla_rechazos", "workspace.silver.precios_rejected")  # type: ignore[name-defined]
dbutils.widgets.text("tabla_salida", "workspace.silver.revision_manual")  # type: ignore[name-defined]
dbutils.widgets.text(  # type: ignore[name-defined]
    "ruta_salida", "s3://cc3105-ag-869227452861-us-east-2-an/equipo3/silver/revision_manual"
)
dbutils.widgets.text("n_fotos", "20")  # type: ignore[name-defined]
dbutils.widgets.text("semilla", "42")  # type: ignore[name-defined]

P = {k: dbutils.widgets.get(k) for k in [  # type: ignore[name-defined]
    "tabla_bronce", "tabla_plata", "tabla_rechazos", "tabla_salida", "ruta_salida", "n_fotos", "semilla",
]}
N_FOTOS = int(P["n_fotos"])
SEMILLA = int(P["semilla"])
print(P)

# COMMAND ----------

# Funciones de la revisión (sin Spark: se pueden probar en local con pandas).
import base64
import html
import io
import math
import random

import pandas as pd

COLS_LECTURA = ["foto_origen", "image_id", "fecha", "combustible", "precio_q_galon", "esta_venta", "galones"]
COMBUSTIBLES = {"diesel", "regular", "super", "v_power"}


def elegir_muestra(paths: list[str], n: int, semilla: int) -> list[str]:
    """Muestra aleatoria reproducible: ordena las rutas y usa una semilla fija."""
    paths = sorted(set(paths))
    return random.Random(semilla).sample(paths, min(n, len(paths)))


def unir_lecturas(muestra: list[str], plata: pd.DataFrame, rechazos: pd.DataFrame) -> pd.DataFrame:
    """Una fila por foto de la muestra con lo que leyó el modelo y su estado en Plata."""
    a = plata.reindex(columns=COLS_LECTURA).assign(estado="aceptada", motivo_rechazo=None)
    r = rechazos.reindex(columns=COLS_LECTURA + ["motivo_rechazo"]).assign(estado="rechazada")
    lect = pd.concat([a, r], ignore_index=True).drop_duplicates("foto_origen", keep="first")
    base = pd.DataFrame({"foto_origen": muestra, "n": range(1, len(muestra) + 1)})
    out = base.merge(lect, on="foto_origen", how="left")
    out["image_id"] = out["image_id"].fillna(
        out["foto_origen"].map(lambda p: p.rsplit("/", 1)[-1].rsplit(".", 1)[0])
    )
    out["estado"] = out["estado"].fillna("sin_fila_en_plata")
    return out.sort_values("n").reset_index(drop=True)


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def a_jpeg_b64(contenido: bytes, lado_max: int = 1100) -> str:
    """HEIC (o JPEG/PNG) a JPEG en base64, con la orientación del EXIF corregida."""
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    from PIL import Image, ImageOps

    im = ImageOps.exif_transpose(Image.open(io.BytesIO(contenido))).convert("RGB")
    im.thumbnail((lado_max, lado_max))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=78)
    return base64.b64encode(buf.getvalue()).decode()


def ficha_html(fila: pd.Series, jpeg_b64: str | None) -> str:
    venta, gal, precio = _num(fila.get("esta_venta")), _num(fila.get("galones")), _num(fila.get("precio_q_galon"))
    f = lambda v, d: "—" if v is None else f"{v:,.{d}f}"  # noqa: E731
    estado = fila["estado"]
    color = {"aceptada": "#1e7d32", "rechazada": "#b71c1c"}.get(estado, "#6b6b6b")
    motivo = f" &middot; {html.escape(str(fila['motivo_rechazo']))}" if isinstance(fila.get("motivo_rechazo"), str) else ""
    img = (f'<img src="data:image/jpeg;base64,{jpeg_b64}" style="width:100%;border-radius:6px">'
           if jpeg_b64 else '<div style="padding:40px;color:#999">sin imagen</div>')
    filas = [
        ("Esta venta (Q)", f(venta, 2)),
        ("Galones", f(gal, 3)),
        ("Precio efectivo (Q/gal)", f(precio, 2)),
        ("Combustible asignado", html.escape(str(fila.get("combustible") or "—"))),
        ("Fecha (EXIF)", html.escape(str(fila.get("fecha") or "—"))),
    ]
    tabla = "".join(
        f'<tr><td style="padding:3px 10px 3px 0;color:#555">{k}</td><td style="font-weight:600">{v}</td></tr>'
        for k, v in filas
    )
    return (
        '<div style="display:flex;gap:16px;align-items:flex-start;border:1px solid #ddd;'
        'border-radius:8px;padding:12px;margin:10px 0;font-family:sans-serif">'
        f'<div style="flex:0 0 62%">{img}</div>'
        f'<div style="flex:1"><div style="font-size:18px;font-weight:700">#{int(fila["n"])} &middot; '
        f'{html.escape(str(fila["image_id"]))}</div>'
        f'<div style="color:{color};margin:4px 0 10px">{estado}{motivo}</div>'
        f'<table style="font-size:15px">{tabla}</table>'
        f'<div style="color:#999;font-size:11px;margin-top:10px;word-break:break-all">'
        f'{html.escape(str(fila["foto_origen"]))}</div></div></div>'
    )


def plantilla_correcciones(lect: pd.DataFrame) -> str:
    """Texto listo para pegar en la hoja de revisión, con una línea comentada por foto."""
    lineas = ["CORRECCIONES = {"]
    for _, r in lect.iterrows():
        venta, gal = _num(r.get("esta_venta")), _num(r.get("galones"))
        lineas.append(
            f'    # "{r["image_id"]}": {{}},  # #{int(r["n"])} leyó: venta {venta} · galones {gal} · '
            f'{r.get("combustible")}'
        )
    lineas.append("}")
    return "\n".join(lineas)


def evaluar(lect: pd.DataFrame, correcciones: dict) -> pd.DataFrame:
    """Compara lo leído con lo real (lo leído + tus correcciones) foto por foto.

    Una foto es correcta si el precio efectivo coincide al centavo y el combustible es el surtido.
    Las fotos marcadas {"ilegible": True} o sin fila en Plata no cuentan para el porcentaje.
    """
    desconocidas = set(correcciones) - set(lect["image_id"])
    if desconocidas:
        raise ValueError(f"Estas fotos no están en la muestra: {sorted(desconocidas)}")
    filas = []
    for _, r in lect.iterrows():
        c = correcciones.get(r["image_id"], {}) or {}
        extra = set(c) - {"esta_venta", "galones", "combustible", "ilegible", "nota"}
        if extra:
            raise ValueError(f"{r['image_id']}: campos no reconocidos {sorted(extra)}")
        if c.get("combustible") is not None and c["combustible"] not in COMBUSTIBLES:
            raise ValueError(f"{r['image_id']}: combustible debe ser uno de {sorted(COMBUSTIBLES)}")
        v_leida, g_leido, p_leido = _num(r.get("esta_venta")), _num(r.get("galones")), _num(r.get("precio_q_galon"))
        comb_leido = r.get("combustible") if isinstance(r.get("combustible"), str) else None
        v_real = _num(c.get("esta_venta", v_leida))
        g_real = _num(c.get("galones", g_leido))
        comb_real = c.get("combustible", comb_leido)
        ilegible = bool(c.get("ilegible"))
        evaluable = not ilegible and r["estado"] != "sin_fila_en_plata"

        p_real = round(v_real / g_real, 2) if (v_real is not None and g_real) else None
        venta_ok = v_leida is not None and v_real is not None and abs(v_leida - v_real) < 0.005
        galones_ok = g_leido is not None and g_real is not None and abs(g_leido - g_real) < 0.0005
        comb_ok = comb_leido is not None and comb_leido == comb_real
        precio_ok = p_leido is not None and p_real is not None and abs(p_leido - p_real) <= 0.01
        errores = [n for n, ok in (("venta", venta_ok), ("galones", galones_ok), ("combustible", comb_ok)) if not ok]
        filas.append({
            "n": int(r["n"]), "image_id": r["image_id"], "foto_origen": r["foto_origen"], "estado": r["estado"],
            "esta_venta_leida": v_leida, "esta_venta_real": v_real,
            "galones_leidos": g_leido, "galones_reales": g_real,
            "precio_leido": p_leido, "precio_real": p_real,
            "combustible_leido": comb_leido, "combustible_real": comb_real,
            "evaluable": evaluable, "ilegible": ilegible,
            "precio_ok": precio_ok if evaluable else None,
            "combustible_ok": comb_ok if evaluable else None,
            "correcta": (precio_ok and comb_ok) if evaluable else None,
            "errores": ";".join(errores) if evaluable else None,
            "nota": c.get("nota"),
        })
    return pd.DataFrame(filas)


def resumen(ev: pd.DataFrame, semilla: int) -> dict:
    e = ev[ev["evaluable"]]
    n_ok = int(e["correcta"].sum())
    errores = e["errores"].dropna().str.split(";").explode()
    errores = errores[errores != ""].value_counts().to_dict()
    rech = e[e["estado"] == "rechazada"]
    return {
        "muestra": len(ev), "evaluables": len(e), "correctas": n_ok,
        "exactitud_pct": round(100 * n_ok / len(e), 1) if len(e) else None,
        "precio_ok_pct": round(100 * e["precio_ok"].mean(), 1) if len(e) else None,
        "combustible_ok_pct": round(100 * e["combustible_ok"].mean(), 1) if len(e) else None,
        "errores_por_campo": errores,
        "ilegibles": int(ev["ilegible"].sum()),
        "sin_fila": int((ev["estado"] == "sin_fila_en_plata").sum()),
        "rechazadas_en_muestra": len(rech),
        "rechazadas_bien_leidas": int(rech["correcta"].sum()) if len(rech) else 0,
        "semilla": semilla,
    }


def parrafo_informe(s: dict) -> str:
    nombres = {"venta": "la venta", "galones": "los galones", "combustible": "el combustible"}
    t = (f"De las {s['muestra']} fotos revisadas (muestra al azar con semilla {s['semilla']}), "
         f"{s['correctas']} de {s['evaluables']} tienen el precio efectivo y el combustible correctos: "
         f"una exactitud de {s['exactitud_pct']:.1f} %. ")
    if s["errores_por_campo"]:
        partes = [f"{k} {'error' if k == 1 else 'errores'} en {nombres.get(c, c)}"
                  for c, k in s["errores_por_campo"].items()]
        t += "Hubo " + (", ".join(partes[:-1]) + " y " if len(partes) > 1 else "") + partes[-1] + ". "
    if s["ilegibles"]:
        k = s["ilegibles"]
        t += ("1 foto no se pudo leer ni a mano y no cuenta para el porcentaje. " if k == 1 else
              f"{k} fotos no se pudieron leer ni a mano y no cuentan para el porcentaje. ")
    if s["rechazadas_en_muestra"]:
        k, b = s["rechazadas_en_muestra"], s["rechazadas_bien_leidas"]
        t += (f"La muestra incluyó {k} {'foto rechazada' if k == 1 else 'fotos rechazadas'} por las reglas "
              "de calidad; " + ("ninguna estaba bien leída. " if b == 0 else
                                f"{b} {'estaba bien leída' if b == 1 else 'estaban bien leídas'}. "))
    return t.strip()

# COMMAND ----------

# Lectura de las tablas (nombre de UC o ruta Delta).
from pyspark.sql import functions as F


def leer(nombre: str):
    if nombre.startswith("s3://") or nombre.startswith("/"):
        return spark.read.format("delta").load(nombre)  # type: ignore[name-defined]
    return spark.table(nombre)  # type: ignore[name-defined]


bronce = leer(P["tabla_bronce"])
plata_sdf = leer(P["tabla_plata"])
rech_sdf = leer(P["tabla_rechazos"])

# COMMAND ----------

# MAGIC %md ## 1. Resumen de Plata: procesadas, rechazadas y motivos

# COMMAND ----------

n_bronce = bronce.select("path").distinct().count()
n_plata = plata_sdf.count()
n_rech = rech_sdf.count()
print(f"Fotos en Bronce: {n_bronce}")
print(f"Aceptadas en silver.precios: {n_plata} ({100 * n_plata / n_bronce:.1f} %)")
print(f"Rechazadas en silver.precios_rejected: {n_rech} ({100 * n_rech / n_bronce:.1f} %)")
if n_plata + n_rech != n_bronce:
    print(f"Ojo: {n_bronce - n_plata - n_rech} foto(s) no aparecen en Plata "
          "(pueden haberse fusionado por la llave fecha + ubicación + combustible + modalidad).")

display(  # type: ignore[name-defined]
    rech_sdf.withColumn("motivo", F.explode(F.split("motivo_rechazo", ";")))
    .groupBy("motivo").count().orderBy(F.desc("count"))
)

# COMMAND ----------

# MAGIC %md ## 2. Muestra de fotos

# COMMAND ----------

paths = [r["path"] for r in bronce.select("path").distinct().collect()]
muestra = elegir_muestra(paths, N_FOTOS, SEMILLA)

lect = unir_lecturas(
    muestra,
    plata_sdf.select(*[c for c in COLS_LECTURA if c in plata_sdf.columns]).toPandas(),
    rech_sdf.select(*[c for c in COLS_LECTURA + ["motivo_rechazo"] if c in rech_sdf.columns]).toPandas(),
)
contenido = {
    r["path"]: bytes(r["content"])
    for r in bronce.where(F.col("path").isin(muestra)).select("path", "content").collect()
}
jpegs = {}
for p in muestra:
    try:
        jpegs[p] = a_jpeg_b64(contenido[p])
    except Exception as exc:  # una foto dañada no detiene la revisión
        print(f"No se pudo convertir {p}: {exc}")
        jpegs[p] = None

print(lect["estado"].value_counts().to_dict())
print("\nCopia esto en la hoja de revisión y descomenta solo las fotos con errores:\n")
print(plantilla_correcciones(lect))


def mostrar(desde: int, hasta: int) -> None:
    cards = [ficha_html(r, jpegs.get(r["foto_origen"])) for _, r in lect.iterrows() if desde <= r["n"] <= hasta]
    displayHTML("".join(cards))  # type: ignore[name-defined]

# COMMAND ----------

mostrar(1, 10)

# COMMAND ----------

mostrar(11, N_FOTOS)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Hoja de revisión
# MAGIC
# MAGIC Pega aquí la plantilla que imprimió la celda de la muestra y descomenta **solo** las fotos
# MAGIC con algún error, con el valor que se ve en la foto. Las que dejes comentadas cuentan como bien leídas.
# MAGIC
# MAGIC ```python
# MAGIC "IMG_8304": {"esta_venta": 300.00},                  # la venta real es Q300.00
# MAGIC "IMG_8322": {"galones": 7.812, "combustible": "super"},
# MAGIC "IMG_8271": {"ilegible": True, "nota": "foto movida"},  # ni a mano se lee: no cuenta
# MAGIC ```
# MAGIC Combustibles válidos: `diesel`, `regular`, `super`, `v_power`.

# COMMAND ----------

CORRECCIONES = {
}

# COMMAND ----------

# MAGIC %md ## 4. Exactitud

# COMMAND ----------

ev = evaluar(lect, CORRECCIONES)
s = resumen(ev, SEMILLA)
for k, v in s.items():
    print(f"{k}: {v}")
display(ev)  # type: ignore[name-defined]

print("\nPárrafo para el informe (sección 2.3):\n")
print(parrafo_informe(s))

# COMMAND ----------

# Guarda el detalle como tabla Delta externa en el bucket de Plata del equipo.
from pyspark.sql.types import BooleanType, DoubleType, LongType, StringType, StructField, StructType

_TIPOS = {"n": LongType(), "evaluable": BooleanType(), "ilegible": BooleanType(), "precio_ok": BooleanType(),
          "combustible_ok": BooleanType(), "correcta": BooleanType()}
for _c in ["esta_venta_leida", "esta_venta_real", "galones_leidos", "galones_reales", "precio_leido", "precio_real"]:
    _TIPOS[_c] = DoubleType()
esquema = StructType([StructField(c, _TIPOS.get(c, StringType()), True) for c in ev.columns])
filas = [
    {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in rec.items()}
    for rec in ev.to_dict("records")
]
try:
    (spark.createDataFrame(filas, esquema)  # type: ignore[name-defined]
     .write.mode("overwrite").option("overwriteSchema", "true").format("delta")
     .option("path", P["ruta_salida"]).saveAsTable(P["tabla_salida"]))
    spark.sql(  # type: ignore[name-defined]
        f"COMMENT ON TABLE {P['tabla_salida']} IS 'Plata: revision manual de {s['muestra']} fotos "
        f"(semilla {SEMILLA}); exactitud {s['exactitud_pct']} %.'"
    )
    print(f"Guardado en {P['tabla_salida']} ({P['ruta_salida']})")
except Exception as exc:
    print(f"No se pudo guardar la tabla ({str(exc)[:200]}). Descarga el resultado como CSV desde la tabla de arriba.")
