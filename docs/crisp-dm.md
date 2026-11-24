# CRISP-DM — mapa del proyecto

CRISP-DM es la **metodología** (6 fases) que ordena el proyecto. No es una
herramienta de código; aquí se documenta cómo cada fase se materializa en el
repo y en la arquitectura medallón.

| Fase CRISP-DM | Qué se hace aquí | Dónde (repo / capa) |
|---|---|---|
| **1. Comprensión del negocio** | Pronosticar el precio del próximo período por combustible (Shell, Guatemala) a partir de fotos del surtidor, para decidir cuándo conviene cargar. | Este doc + `README.md` |
| **2. Comprensión de los datos** | Fotos `.HEIC` con EXIF (GPS, timestamp) + lecturas OCR (`annotations/vision_readings.json`). Se extraen a tablas crudas. | `src/extract.py` → capa **bronze** (`observaciones`, `lecturas_long`) |
| **3. Preparación de los datos** | Reconciliación (venta/galones vs. precio leído), imputación temporal de faltantes, flags de calidad/outliers; luego armado del dataset analítico con features (precio anterior, días desde anterior, variaciones). | `src/transform.py` → **silver** (`precios`, `transacciones`); `src/load.py` → **gold** (`precios_combustible`) |
| **4. Modelado** | Baseline *carry-forward* + regresión **Ridge** con split temporal; preprocesado dentro del `Pipeline` de scikit-learn (sin fuga de datos). | `src/model.py` (referencia; el pipeline de modelo lo desarrolla el compañero) |
| **5. Evaluación** | MAE sobre validación temporal; comparación baseline vs. Ridge; todo registrado en **MLflow**. | `src/model.py` + MLflow (local sqlite / Databricks) |
| **6. Despliegue** | Orquestación como **Job de Databricks** (DAG extract→transform→load→model) vía **Asset Bundle**; **CI/CD** en GitHub Actions; backend intercambiable (`local`/`uc`/`s3`). | `databricks.yml`, `databricks/`, `.github/workflows/` |

## Correspondencia medallón ↔ CRISP-DM

```
raw (imágenes)      →  Fase 2  (comprensión de datos: fuente cruda)
bronze (cusn)       →  Fase 2  (datos crudos extraídos por OCR/EXIF)
silver (ag)         →  Fase 3  (limpieza, reconciliación, imputación)
gold (au)           →  Fase 3  (dataset analítico listo)  ──▶ Fase 4 (entrada del modelo)
```

El **handoff** al pipeline del modelo ocurre en la capa **gold**
(`workspace.gold.precios_combustible`): ese es el límite entre la Fase 3 (este
repo) y la Fase 4 (modelo).
