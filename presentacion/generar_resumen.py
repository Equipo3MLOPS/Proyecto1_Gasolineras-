"""Genera presentacion/resumen_jurado.html (una página carta) para imprimir a PDF.

uso: API_URL=http://<ip>:8003 REVISION="85 %" python generar_resumen.py resumen_jurado.html
"""
import base64
import io
import os
import sys

API_URL = os.environ.get("API_URL", "").rstrip("/")
REVISION = os.environ.get("REVISION", "45.0 %")


def qr_data_uri(texto: str) -> str:
    import qrcode
    img = qrcode.make(texto, border=1, box_size=8)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


base = API_URL or "http://[IP del Droplet]:8003"
pend = "" if API_URL else ' class="pend"'
qr = (f'<img class="qr" src="{qr_data_uri(API_URL + "/")}" alt="QR a la página de la API">'
      if API_URL else '<div class="qr qrpend">QR pendiente<br>(IP del Droplet)</div>')
rev = ("de 20 fotos revisadas a mano sin ningún error; los montos, bien en 18" if REVISION
       else '<span class="pend">revisión manual de 20 fotos: pendiente</span>')

html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>Resumen para el jurado · Equipo 3</title>
<style>
@page {{ size: letter; margin: 0.55in 0.6in; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Calibri, Carlito, Arial, sans-serif; color: #1B1F2A; font-size: 10.8pt; line-height: 1.38; margin: 0; }}
h1 {{ font-family: Arial, sans-serif; color: #0E2A47; font-size: 21pt; margin: 0 0 2px; }}
.sub {{ color: #5A6473; font-size: 10pt; margin-bottom: 12px; }}
h2 {{ font-family: Arial, sans-serif; color: #0E2A47; font-size: 12.5pt; margin: 13px 0 4px; }}
p {{ margin: 0 0 6px; }}
.flujo {{ display: flex; gap: 6px; margin: 6px 0 6px; }}
.paso {{ flex: 1; border-radius: 7px; padding: 6px 8px; font-size: 9.4pt; line-height: 1.28; border: 1px solid #C5CCD6; }}
.paso b {{ display: block; font-size: 10.5pt; color: #0E2A47; }}
.f {{ background: #fff; }} .b {{ background: #EBCFB2; }} .s {{ background: #E3E6EA; }} .o {{ background: #F8E7A6; }} .a {{ background: #E3EEFB; }}
.stats {{ display: flex; gap: 8px; margin: 6px 0 4px; }}
.stat {{ flex: 1; background: #EEF2F7; border-radius: 7px; padding: 7px 9px; font-size: 9.4pt; line-height: 1.25; }}
.stat .n {{ font-family: Arial, sans-serif; font-size: 18pt; font-weight: bold; color: #0E2A47; display: block; }}
.stat .n.ok {{ color: #2E8B57; }} .stat .n.am {{ color: #B9801F; }}
table {{ border-collapse: collapse; width: 100%; font-size: 9.6pt; margin: 4px 0 6px; }}
th, td {{ border: 1px solid #C9D1DB; padding: 3px 7px; text-align: left; }}
th {{ background: #D9E2F3; }} td.num {{ text-align: center; }}
tr.sel td {{ background: #E2EFDA; font-weight: bold; }} tr.ref td {{ background: #F2F2F2; font-style: italic; }}
.prueba {{ display: flex; gap: 14px; align-items: center; background: #0E2A47; color: #fff; border-radius: 8px; padding: 10px 14px; margin-top: 10px; }}
.prueba code {{ font-family: "Courier New", monospace; font-size: 9.6pt; color: #FFE2A8; }}
.prueba h2 {{ color: #E8A33D; margin: 0 0 4px; }}
.qr {{ width: 1.15in; height: 1.15in; background: #fff; border-radius: 6px; padding: 4px; flex: none; }}
.qrpend {{ color: #C0392B; font-size: 9pt; display: flex; align-items: center; justify-content: center; text-align: center; border: 1.5px dashed #C0392B; }}
.pend {{ color: #C0392B; font-weight: bold; }}
ul {{ margin: 2px 0 6px 18px; padding: 0; }} li {{ margin-bottom: 2px; }}
.pie {{ margin-top: 10px; font-size: 9pt; color: #5A6473; border-top: 1px solid #DDE3EA; padding-top: 5px; }}
</style></head><body>
<h1>¿Sube o baja la gasolina la próxima semana?</h1>
<div class="sub">Resumen para el jurado · Equipo 3 · CC3105 Proyecto final · Universidad del Valle de Guatemala · noviembre de 2026</div>

<h2>El problema</h2>
<p>El Ministerio de Energía y Minas publica cada martes los precios de referencia de la gasolina súper, la regular y
el diésel, vigentes de martes a lunes. Para transportistas, flotillas y pequeñas empresas que compran cientos de
galones, saber con una semana de anticipación si el precio va a subir o a bajar ayuda a decidir cuándo comprar.
Nuestra pregunta: <b>para cada combustible, ¿el precio de la semana siguiente sube, baja o se mantiene?</b></p>

<h2>La solución</h2>
<div class="flujo">
  <div class="paso f"><b>Fotos</b>Fotos de surtidores en la nube (AWS S3).</div>
  <div class="paso b"><b>Bronce</b>Guarda cada foto tal como llegó, sin repetir.</div>
  <div class="paso s"><b>Plata</b>Un modelo de visión lee venta y galones; tres reglas validan el precio.</div>
  <div class="paso o"><b>Oro</b>Precio semanal, tendencia y la predicción del modelo.</div>
  <div class="paso a"><b>API</b>Responde por internet con el precio y la predicción.</div>
</div>
<p>Databricks ejecuta Bronce, Plata y Oro cada martes a las 6:00 sin intervención y avisa por correo si algo falla;
cada entrenamiento del modelo queda registrado en MLflow. La API vive en un contenedor Docker en un servidor de
DigitalOcean y solo lee la capa Oro.</p>

<h2>Resultados</h2>
<div class="stats">
  <div class="stat"><span class="n">109</span>fotos procesadas</div>
  <div class="stat"><span class="n ok">95.4 %</span>pasan los controles de calidad; las 5 restantes quedan en cuarentena con su motivo</div>
  <div class="stat"><span class="n am">{REVISION or "—"}</span>{rev}</div>
</div>
<table>
<tr><th>Exactitud en las 28 semanas de prueba (que el modelo nunca vio)</th><th>Exactitud</th></tr>
<tr class="sel"><td>Bosque aleatorio (modelo elegido)</td><td class="num">42.9 %</td></tr>
<tr><td>Línea base: repetir la dirección de la semana anterior</td><td class="num">39.3 %</td></tr>
<tr class="ref"><td>Referencia: decir siempre «sube»</td><td class="num">57.1 %</td></tr>
</table>
<p>El modelo supera a la línea base por un acierto en 28 semanas, una diferencia que no está demostrada, y ninguna
regla le gana a «siempre sube» porque en ese periodo el precio subió 16 de 28 semanas. Las limitaciones vienen de los
datos: las fotos no son semanales (33 días entre fotos de súper en promedio), hay 99 semanas etiquetadas en cuatro
años, la revisión a mano encontró el combustible mal asignado en 10 de 20 fotos y no usamos el precio del petróleo. Con más tiempo, corregiríamos la asignación del combustible, guardaríamos los cuatro precios de
cada foto y agregaríamos el petróleo como variable.</p>

<div class="prueba">
  {qr}
  <div>
    <h2>Pruébelo desde su teléfono</h2>
    <div>Página con precios y predicciones: <code{pend}>{base}/</code></div>
    <div>Predicción de la súper: <code{pend}>{base}/prediccion?combustible=super</code></div>
    <div>Precio actual: <code{pend}>{base}/precios/actual</code></div>
    <div>Documentación interactiva: <code{pend}>{base}/docs</code></div>
  </div>
</div>

<div class="pie">Jose Santiago Pereira · Nancy Mazariegos · Hugo Rivas · Giovanni Santos · Alexis Mesias · Brandon Reyes ·
Código: github.com/Equipo3MLOPS/Proyecto1_Gasolineras-</div>
</body></html>"""
open(sys.argv[1], "w", encoding="utf-8").write(html)
print("ok", sys.argv[1])
