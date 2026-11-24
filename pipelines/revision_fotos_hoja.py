# Databricks notebook source
# MAGIC %md
# MAGIC # Hoja de revisión manual · 20 fotos
# MAGIC Elige las mismas 20 fotos que `pipelines/revision_manual_plata.py` (semilla 42), las convierte a JPEG y arma
# MAGIC una página HTML autocontenida con cada foto junto a lo que leyó el modelo. Solo lee tablas; no escribe ninguna.

# COMMAND ----------

# MAGIC %pip install pillow-heif

# COMMAND ----------

dbutils.library.restartPython()  # type: ignore[name-defined]

# COMMAND ----------

import base64
import html
import io
import json
import random

import pillow_heif
from PIL import Image, ImageOps
from pyspark.sql import functions as F

pillow_heif.register_heif_opener()
SEMILLA, N = 42, 20

bronce = spark.table("workspace.bronze.fotos_precios")  # type: ignore[name-defined]
paths = sorted({r["path"] for r in bronce.select("path").collect()})
muestra = random.Random(SEMILLA).sample(paths, N)

cols = ["foto_origen", "image_id", "fecha", "combustible", "precio_q_galon", "esta_venta", "galones"]
acept = spark.table("workspace.silver.precios").select(*cols).withColumn("motivo", F.lit(None).cast("string"))  # type: ignore[name-defined]
rech = spark.table("workspace.silver.precios_rejected").select(*cols, F.col("motivo_rechazo").alias("motivo"))  # type: ignore[name-defined]
lect = {}
for r in acept.unionByName(rech).where(F.col("foto_origen").isin(muestra)).collect():
    lect.setdefault(r["foto_origen"], []).append(r.asDict())

fotos = []
for i, p in enumerate(muestra, 1):
    content = bronce.where(F.col("path") == p).select("content").first()["content"]
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(bytes(content)))).convert("RGB")
    im.thumbnail((1100, 1100))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=74)
    filas = lect.get(p, [])
    fotos.append({
        "n": i, "foto": p.rsplit("/", 1)[-1], "img": base64.b64encode(buf.getvalue()).decode(),
        "lecturas": [{k: (None if v is None else str(v)) for k, v in f.items() if k != "foto_origen"} for f in filas],
    })
    print(i, p.rsplit("/", 1)[-1], len(filas), "lectura(s)")

# COMMAND ----------

PAGINA = r"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Revisión manual · 20 fotos</title><style>
body{margin:0;font:16px/1.5 Helvetica,Arial,sans-serif;color:#16191d;background:#f3f5f7}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #d9dee4;padding:12px 24px;display:flex;gap:24px;align-items:center;flex-wrap:wrap;z-index:2}
h1{font-size:22px;margin:0}.res{font-size:18px}.res b{font-size:26px}
main{max-width:1180px;margin:0 auto;padding:20px}
.card{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:22px;background:#fff;border-radius:14px;padding:18px;margin-bottom:18px;border:2px solid transparent}
.card.ok{border-color:#2e8540}.card.ko{border-color:#d24a2c}.card.il{border-color:#8a929b}
.card img{width:100%;border-radius:10px;cursor:zoom-in}.card img.zoom{position:fixed;inset:0;width:auto;height:100vh;margin:auto;z-index:9;cursor:zoom-out;background:#000;object-fit:contain;max-width:100vw}
h2{font-size:20px;margin:0 0 8px}table{border-collapse:collapse;width:100%;margin-bottom:10px}td{padding:5px 8px;border-bottom:1px solid #e4e8ec}td:first-child{color:#59616c;width:46%}
.btns{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}button{font:inherit;padding:10px 14px;border-radius:9px;border:2px solid #d9dee4;background:#fff;cursor:pointer}
button[aria-pressed=true]{background:#16191d;color:#fff;border-color:#16191d}
.fix{display:none;gap:8px;flex-direction:column}.card.ko .fix{display:flex}label{display:flex;justify-content:space-between;gap:10px;align-items:center}
input,select{font:inherit;padding:6px 8px;border:1px solid #c9d1db;border-radius:7px;width:150px}
.warn{background:#fff4e5;border-radius:8px;padding:6px 10px;font-size:14px;margin-bottom:8px}
textarea{width:100%;height:150px;font:13px/1.4 monospace}
@media(max-width:760px){.card{grid-template-columns:1fr}}
</style></head><body>
<header><h1>Revisión manual · 20 fotos (semilla 42)</h1><div class="res" id="res"></div></header>
<main><p>Para cada foto, lea primero el display (Esta venta, Galones y el combustible iluminado o surtido) y después compárelo con la lectura. Una foto es <b>correcta</b> si la venta y los galones coinciden y el combustible asignado es el surtido. Si ni a mano se puede leer, márquela como <b>ilegible</b>: no cuenta para el porcentaje. Toque la foto para ampliarla. Las marcas se guardan en este navegador.</p>
<div id="lista"></div>
<h2>Resultado para el informe y el notebook</h2><textarea id="salida" readonly></textarea></main>
<script>
const FOTOS = __DATOS__;
const KEY = "revision20";
let st = {}; try { st = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} };
const esc = (s) => String(s == null ? "—" : s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const COMB = ["diesel", "regular", "super", "v_power"];
function render() {
  document.getElementById("lista").innerHTML = FOTOS.map((f) => {
    const s = st[f.foto] || {}; const L = f.lecturas;
    const tabla = L.length ? L.map((l) => `<table>
      <tr><td>Estado en Plata</td><td>${l.motivo ? "rechazada: " + esc(l.motivo) : "aceptada"}</td></tr>
      <tr><td>Esta venta (Q)</td><td><b>${esc(l.esta_venta)}</b></td></tr><tr><td>Galones</td><td><b>${esc(l.galones)}</b></td></tr>
      <tr><td>Precio efectivo (Q/gal)</td><td>${esc(l.precio_q_galon)}</td></tr><tr><td>Combustible asignado</td><td><b>${esc(l.combustible)}</b></td></tr>
      <tr><td>Fecha (EXIF)</td><td>${esc(l.fecha)}</td></tr></table>`).join("") : "<p>Sin lectura en Plata.</p>";
    const dup = L.length > 1 ? `<div class="warn">Esta foto tiene ${L.length} filas en Plata con combustibles distintos: revise cuál es el correcto.</div>` : "";
    return `<section class="card ${s.v || ""}" data-f="${f.foto}">
      <img src="data:image/jpeg;base64,${f.img}" alt="Foto ${f.n}: ${f.foto}">
      <div><h2>${f.n}. ${f.foto}</h2>${dup}${tabla}
      <div class="btns">${[["ok","Correcta"],["ko","Tiene un error"],["il","Ilegible"]].map(([k,t]) => `<button data-k="${k}" aria-pressed="${s.v===k}">${t}</button>`).join("")}</div>
      <div class="fix"><label>Venta real (Q)<input data-c="esta_venta" type="number" step="0.01" value="${s.esta_venta ?? ""}"></label>
      <label>Galones reales<input data-c="galones" type="number" step="0.001" value="${s.galones ?? ""}"></label>
      <label>Combustible real<select data-c="combustible"><option value="">(igual)</option>${COMB.map((c) => `<option ${s.combustible===c?"selected":""}>${c}</option>`).join("")}</select></label>
      <label>Nota<input data-c="nota" value="${esc(s.nota ?? "").replace(/^—$/, "")}" style="width:220px"></label></div></div></section>`;
  }).join("");
  resumen();
}
function resumen() {
  const marcadas = FOTOS.filter((f) => st[f.foto] && st[f.foto].v);
  const ok = marcadas.filter((f) => st[f.foto].v === "ok").length;
  const il = marcadas.filter((f) => st[f.foto].v === "il").length;
  const ev = marcadas.length - il;
  const pct = ev ? (100 * ok / ev).toFixed(1) : "—";
  document.getElementById("res").innerHTML = `Revisadas <b>${marcadas.length}</b>/20 · correctas <b>${ok}</b> de ${ev} evaluables · exactitud <b>${pct}${ev ? " %" : ""}</b>`;
  const corr = {};
  for (const f of FOTOS) { const s = st[f.foto]; if (!s || s.v === "ok" || !s.v) continue;
    const id = f.foto.replace(/\.[^.]+$/, ""); if (s.v === "il") { corr[id] = { ilegible: true }; continue; }
    const c = {}; for (const k of ["esta_venta", "galones"]) if (s[k] !== undefined && s[k] !== "") c[k] = Number(s[k]);
    if (s.combustible) c.combustible = s.combustible; if (s.nota) c.nota = s.nota; corr[id] = c; }
  const errores = FOTOS.filter((f) => st[f.foto] && st[f.foto].v === "ko").map((f) => f.foto + (st[f.foto].nota ? " (" + st[f.foto].nota + ")" : ""));
  document.getElementById("salida").value = `Revisadas: ${marcadas.length} de 20\nCorrectas: ${ok} de ${ev} evaluables (${il} ilegibles)\nExactitud: ${pct}${ev ? " %" : ""}\nCon error: ${errores.join(", ") || "ninguna"}\n\nCORRECCIONES = ${JSON.stringify(corr, null, 2)}`;
}
document.addEventListener("click", (e) => {
  const img = e.target.closest("img"); if (img) { img.classList.toggle("zoom"); return; }
  const b = e.target.closest("button[data-k]"); if (!b) return;
  const f = b.closest(".card").dataset.f; st[f] = Object.assign(st[f] || {}, { v: b.dataset.k }); save(); render();
});
document.addEventListener("change", (e) => {
  const el = e.target.closest("[data-c]"); if (!el) return;
  const f = el.closest(".card").dataset.f; st[f] = st[f] || {}; st[f][el.dataset.c] = el.value; save(); resumen();
});
render();
</script></body></html>"""

pagina = PAGINA.replace("__DATOS__", json.dumps(fotos))
usuario = spark.sql("SELECT current_user()").first()[0]  # type: ignore[name-defined]
ruta = f"/Workspace/Users/{usuario}/hoja_revision_20_fotos.html"
with open(ruta, "w", encoding="utf-8") as fh:
    fh.write(pagina)
print(f"Hoja guardada en {ruta} ({len(pagina) / 1e6:.1f} MB)")
displayHTML(pagina)  # type: ignore[name-defined]
