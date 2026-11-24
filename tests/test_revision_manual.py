"""Pruebas de la lógica del notebook pipelines/revision_manual_plata.py (sin Spark)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
NOTEBOOK = RAIZ / "pipelines" / "revision_manual_plata.py"


@pytest.fixture(scope="module")
def nb() -> dict:
    """Ejecuta solo la celda de funciones del notebook (no usa Spark ni dbutils)."""
    celdas = NOTEBOOK.read_text(encoding="utf-8").split("# COMMAND ----------")
    celda = next(c for c in celdas if "def evaluar(" in c)
    ns: dict = {}
    exec(compile(celda, str(NOTEBOOK), "exec"), ns)
    return ns


def _datos():
    plata = pd.DataFrame([
        {"foto_origen": "s3://b/img/A.HEIC", "image_id": "A", "fecha": "2026-01-06", "combustible": "super",
         "precio_q_galon": 32.50, "esta_venta": 250.00, "galones": 7.692},
        {"foto_origen": "s3://b/img/B.HEIC", "image_id": "B", "fecha": "2026-01-13", "combustible": "diesel",
         "precio_q_galon": 30.00, "esta_venta": 300.00, "galones": 10.000},
    ])
    rech = pd.DataFrame([
        {"foto_origen": "s3://b/img/C.HEIC", "image_id": "C", "fecha": "2026-01-20", "combustible": None,
         "precio_q_galon": 3.0, "esta_venta": 30.0, "galones": 10.0, "motivo_rechazo": "precio_fuera_de_rango"},
    ])
    return plata, rech


def test_muestra_reproducible(nb):
    paths = [f"p{i}" for i in range(109)]
    m1 = nb["elegir_muestra"](paths, 20, 42)
    assert m1 == nb["elegir_muestra"](list(reversed(paths)), 20, 42)
    assert len(set(m1)) == 20


def test_unir_lecturas_estados(nb):
    plata, rech = _datos()
    muestra = ["s3://b/img/A.HEIC", "s3://b/img/C.HEIC", "s3://b/img/D.HEIC"]
    lect = nb["unir_lecturas"](muestra, plata, rech)
    assert list(lect["estado"]) == ["aceptada", "rechazada", "sin_fila_en_plata"]
    assert lect.loc[2, "image_id"] == "D"


def test_evaluar_sin_correcciones_todo_correcto(nb):
    plata, rech = _datos()
    lect = nb["unir_lecturas"]([*plata["foto_origen"]], plata, rech)
    s = nb["resumen"](nb["evaluar"](lect, {}), 42)
    assert (s["correctas"], s["evaluables"], s["exactitud_pct"]) == (2, 2, 100.0)


def test_evaluar_con_correcciones(nb):
    plata, rech = _datos()
    lect = nb["unir_lecturas"]([*plata["foto_origen"], *rech["foto_origen"]], plata, rech)
    corr = {
        "B": {"galones": 9.5},                       # galones mal leídos -> precio mal
        "C": {"ilegible": True},                     # no cuenta
    }
    ev = nb["evaluar"](lect, corr)
    s = nb["resumen"](ev, 42)
    assert s["evaluables"] == 2 and s["correctas"] == 1 and s["exactitud_pct"] == 50.0
    assert s["errores_por_campo"] == {"galones": 1}
    assert ev.set_index("image_id").loc["B", "precio_real"] == pytest.approx(31.58)
    assert "1 de 2" in nb["parrafo_informe"](s)


def test_combustible_equivocado_es_error(nb):
    plata, rech = _datos()
    lect = nb["unir_lecturas"]([*plata["foto_origen"]], plata, rech)
    s = nb["resumen"](nb["evaluar"](lect, {"A": {"combustible": "regular"}}), 42)
    assert s["correctas"] == 1 and s["errores_por_campo"] == {"combustible": 1}


def test_correcciones_invalidas(nb):
    plata, rech = _datos()
    lect = nb["unir_lecturas"]([*plata["foto_origen"]], plata, rech)
    with pytest.raises(ValueError):
        nb["evaluar"](lect, {"ZZZ": {"galones": 1}})
    with pytest.raises(ValueError):
        nb["evaluar"](lect, {"A": {"combustible": "premium"}})
    with pytest.raises(ValueError):
        nb["evaluar"](lect, {"A": {"galon": 7.0}})


def test_ficha_y_jpeg(nb):
    fotos = sorted((RAIZ / "Data").glob("*.HEIC"))
    if not fotos:
        pytest.skip("sin fotos locales")
    pytest.importorskip("pillow_heif")
    b64 = nb["a_jpeg_b64"](fotos[0].read_bytes(), 400)
    plata, rech = _datos()
    lect = nb["unir_lecturas"](["s3://b/img/A.HEIC"], plata, rech)
    html = nb["ficha_html"](lect.iloc[0], b64)
    assert "data:image/jpeg;base64," in html and "32.50" in html
