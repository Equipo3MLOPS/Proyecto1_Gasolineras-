# Pipeline de datos de gasolineras (fotos de surtidor → SQLite)

Pipeline **batch + ETL** que convierte fotos crudas de un surtidor de gasolina en
un dataset limpio de **series de tiempo de precios**, listo para alimentar un
modelo de ML/DL.

**Objetivo:** pronosticar el precio de cada combustible en el tiempo para responder
la problemática de las gasolineras: **cuánto y cuándo comprar** combustible para su
inventario. Todo el diseño de la base apunta a eso.

Fuente: 5 fotos `.HEIC` de un surtidor **Shell** (Gilbarco Veeder-Root) tomadas con
un iPhone 14 en **Guatemala** (deducido por GPS; moneda **Quetzal, GTQ**, combustible
vendido por **galón**), entre el 9 y el 30 de julio de 2026.

De cada foto se extrae:

- **Metadatos EXIF** (100% automático): fecha/hora, GPS (lat/lon/altitud), rumbo, cámara.
- **Displays del surtidor** (visión con puntaje de confianza):
  - `Esta Venta` — dinero surtido (Q)
  - `Galones` — volumen surtido
  - 4 precios `Precio por galón`: **Diesel, Regular, Super, V-Power**

---

## ¿Por qué batch + ETL? (y no streaming)

| Criterio | Este caso | Conclusión |
|---|---|---|
| Volumen / frecuencia | Pocas fotos, llegada periódica (semanal) | **Batch**: no hay flujo continuo que justifique streaming |
| Latencia requerida | Ninguna; el análisis es posterior | **Batch**: procesar en lotes idempotentes |
| Transformación | Pesada (imagen→texto→validación→normalización) | **ETL** en etapas re-ejecutables |
| Salida | Pequeña y estructurada | **SQLite**: cero servidor, un archivo, ideal para ML/DL |

**Matiz importante:** como la fuente son imágenes, la extracción es en realidad
**imagen→texto (OCR/visión)**, así que el flujo es *ELT en la capa cruda + ETL después*.
Por eso se organiza en capas estilo **medallion**, que hace todo auditable y
re-ejecutable **sin volver a fotografiar**:

```
  Data/ (HEIC)  ──►  BRONZE  ──►  SILVER  ──►  GOLD (SQLite)
   crudo          extraído,      limpio,       normalizado,
                  con confianza  validado      listo para modelar
```

---

## Estructura del proyecto

```
Proyecto1_Gasolineras-/
├─ Data/                              # fotos .HEIC crudas (fuente, no se toca)
├─ annotations/
│  └─ vision_readings.json           # salida del pase de visión (lecturas + confianza)
├─ src/
│  ├─ __init__.py                    # hace de src/ un paquete instalable
│  ├─ config.py                      # rutas, dominio y umbrales de calidad
│  ├─ extract.py     # 01  EXIF + displays          -> artifacts/bronze/
│  ├─ eda.py         # 02  análisis exploratorio     -> reports/
│  ├─ transform.py   # 03  limpieza + validación      -> artifacts/silver/
│  ├─ load.py        # 04  dataset para el modelo      -> db/gasolineras.db + gold/
│  └─ pipeline.py    #     orquestador de las 4 etapas
├─ notebooks/
│  └─ calibracion_hiperparametros.ipynb  # 05  Modeling + Evaluation (CRISP-DM)
├─ artifacts/
│  ├─ bronze/  observations_raw.csv, readings_long.csv   # crudo extraído
│  ├─ silver/  fuel_prices_clean.csv, fill_ups_clean.csv # limpio + control de calidad
│  └─ gold/    dataset_precios.csv                        # tabla plana lista para ML
├─ reports/   eda_report.md + figures/*.png (incluye pipeline_diagram.html)
├─ db/        gasolineras.db          # BASE DE DATOS FINAL (SQLite, 1 tabla)
├─ pyproject.toml                     # empaquetado (pip install -e .)
├─ requirements.txt
└─ README.md
```

---

## Cómo ejecutarlo

### Opción rápida (sin instalar el paquete)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m src.pipeline
```

Etapas individuales o combinaciones:

```bash
python -m src.extract            # solo extracción
python -m src.pipeline --no-eda  # todo menos el EDA
python -m src.pipeline transform load
```

Todo es **idempotente**: se puede re-ejecutar cuantas veces se quiera; las tablas
se recrean y los CSV se sobrescriben.

### Opción empaquetada (para compartir con el equipo)

El proyecto se instala como paquete Python vía `pyproject.toml`, así cualquier
integrante lo corre igual sin depender de `python -m src...` ni de estar parado
en la raíz del repo:

```bash
git clone <url-del-repo>
cd Proyecto1_Gasolineras-
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
gasolineras-pipeline            # corre el pipeline completo
gasolineras-pipeline --no-eda   # o cualquier combinación de etapas
```

`pip install -e .` deja el comando `gasolineras-pipeline` disponible como CLI
(definido en `[project.scripts]` de `pyproject.toml`) y expone `src` como paquete
importable (`from src import config`) desde cualquier script o notebook.

**Para validar que corre en máquinas distintas** : probar `pip install -e .` y
`gasolineras-pipeline` corriendo sin errores en cada una.


---

## Etapa 1 — Extracción (la estrategia para valores dudosos)

El EXIF se lee en Python puro con `pillow-heif`. Los valores del display se leen a
través de una interfaz **intercambiable**:

```python
class DisplayReader:
    def read(self, image_id, path) -> DisplayReading: ...

class VisionAnnotationReader(DisplayReader):   # implementación por defecto
    # lee annotations/vision_readings.json (salida del pase de visión)
```

Cada valor trae un **puntaje de confianza (0–1)**. Los mini-displays de 7 segmentos
son pequeños/borrosos, así que la confianza captura explícitamente **qué tan seguro
es cada número**. Para automatizar la lectura basta con implementar otro
`DisplayReader` (Tesseract, EasyOCR, un modelo de visión por API…) que devuelva la
misma estructura — el resto del pipeline no cambia.

### La red de seguridad: reconciliación `venta = galones × precio`

Es la identidad física del surtidor. Con dos de los tres valores se deduce el
tercero. El **precio efectivo = `Esta_Venta / Galones`** identifica el combustible
surtido y **valida/corrige** su precio leído. En estas 5 fotos el residual máximo
fue **0.0046 Q/galón** → el combustible surtido fue **Super** en todas, y su precio
queda validado con total confianza aunque el display estuviera borroso.

---

## Etapa 2 — EDA

`src/eda.py` analiza la capa bronze **sin modificarla** y produce
[`reports/eda_report.md`](reports/eda_report.md) + 4 figuras:

1. Heatmap de confianza por precio (qué lecturas caen bajo el umbral).
2. Reconciliación: precio efectivo vs Super leído + residuales (control de calidad).
3. Evolución temporal de precios (marca las lecturas de baja confianza).
4. **Variación de precio entre visitas** — señal directa de *cuándo comprar*.
5. **Mapa de calor de correlación** entre combustibles — se mueven casi en bloque
   (regular/super/v_power ≈ 1.00), así que basta pronosticar uno y derivar el resto.

Las decisiones de limpieza del EDA son las que implementa la etapa 3.
Con solo 5 observaciones, un histograma de distribución no es informativo; por eso
el EDA prioriza tendencia, variación y correlación (más útiles para el objetivo).

---

## Etapa 3 — Transformación (limpieza)

Aplicada **en orden de confianza**, sin borrar nada (todo se marca con banderas):

1. **Reconciliación** — el precio del combustible surtido se fija con
   `venta/galones` (el número más preciso). `status = reconciled`.
2. **Lecturas confiables** (confianza ≥ `0.70`) → se conservan. `status = trusted`.
3. **Nulos** (confianza < `0.70`) → se vuelven faltantes y se **imputan** con esta
   prioridad, marcando `is_imputed` y el método:
   - `interp_time` — interpolación temporal entre dos anclas confiables
   - `weak_fallback` — si no hay dos anclas, se usa la lectura débil en rango
   - `carry` — si solo hay un ancla, se arrastra la más cercana
4. **Atípicos** → se **marcan** (no se eliminan):
   - `is_range_outlier` (rango de dominio), `is_iqr_outlier` (1.5·IQR por combustible),
   - `is_ladder_violation` (orden `regular ≤ super ≤ v_power`; el **diesel** es un
     producto aparte y no entra en la regla).
5. **Estandarización** → unidades unificadas (`GTQ/galón`), columna `GTQ/litro`,
   redondeo canónico.
   > La **normalización z-score** para ML **no** se hace aquí a propósito: debe
   > ajustarse solo con el conjunto de entrenamiento para evitar *data leakage*.
   > Pertenece a la etapa de modelado.

**Ejemplo real del dataset:** `regular` en `IMG_8286` tenía confianza 0.55 → se
descartó y se imputó por interpolación a **38.47**, muy cerca de la lectura débil
original (38.59): la interpolación se validó sola.

---

## Etapa 4 — Carga (dataset para el modelo)

El objetivo es **pronosticar el precio** para decidir *cuánto y cuándo comprar*. Por
eso la base **no** guarda metadatos de foto ni columnas internas del ETL: es **una
sola tabla desnormalizada** (`precios_combustible`), lista para exportar directo a
un dataframe. Grano: **un combustible por foto/fecha** (20 filas). No usa
`AUTOINCREMENT`, así que **no existe `sqlite_sequence`**.

**Tabla `precios_combustible`** (+ vista `v_precios_ancho`):

| Columna | Qué representa |
|---|---|
| `id` | Identificador de fila |
| `fecha`, `fecha_hora_local`, `anio`, `semana_iso` | Eje temporal (comparar el cambio en el tiempo) |
| `id_estacion`, `estacion`, `pais`, `latitud`, `longitud`, `altitud_m` | Ubicación mínima (futuro multi-estación) |
| `tipo_combustible`, `categoria` | Combustible (diesel/regular/super/v_power) y su tipo |
| **`precio_galon`**, `precio_litro`, `moneda` | **Precio limpio** (objetivo) y su versión por litro |
| `calidad_precio` | Confiabilidad en 1 columna: `leido` / `reconciliado` / `imputado` |
| `precio_galon_anterior`, `variacion_abs`, `variacion_pct`, `dias_desde_anterior` | Features temporales causales — señales de *cuándo/cuánto comprar* |

Ejemplos de consulta:

```sql
-- Serie de precios en formato ancho (para graficar / correlacionar)
SELECT fecha, diesel, regular, super, v_power FROM v_precios_ancho ORDER BY fecha;

-- Solo precios de alta confianza (excluye imputados) para entrenar
SELECT fecha, tipo_combustible, precio_galon
FROM precios_combustible WHERE calidad_precio <> 'imputado';

-- Ritmo de subida por combustible (¿acelera o se frena? -> cuándo comprar)
SELECT fecha, tipo_combustible, variacion_abs, variacion_pct
FROM precios_combustible WHERE variacion_abs IS NOT NULL ORDER BY fecha;
```

> La misma tabla se exporta a `artifacts/gold/dataset_precios.csv` para cargarla
> directo con `pandas.read_csv` en la etapa de modelado.

---

## Hallazgos

- **1 estación**, 5 visitas semanales (9–30 jul 2026); cada llenado fue de **Q150 exactos**.
- Precio **Super** subió de forma sostenida: **38.09 → 39.59 → 41.09 → 42.09** Q/galón.
- El display grande (venta/galones) es nítido; los 4 mini-displays de precio son la
  parte difícil — el **diesel** es el peor leído (4/5 lecturas de baja confianza).
- La reconciliación deja el precio del combustible surtido prácticamente exacto.

## Limitaciones y próximos pasos

- Muestra pequeña (5 fotos, 1 estación): la imputación temporal del **diesel** es de
  baja fiabilidad (casi no hay anclas confiables) y queda marcada como tal.
- **Automatizar la lectura**: implementar un `DisplayReader` con OCR/visión real para
  procesar lotes grandes sin intervención manual.
- **Modelado (ML/DL)**: exportar `v_prices_wide` / `fuel_prices` y aplicar la
  normalización dentro del split de entrenamiento. Con más historia, un modelo de
  serie temporal puede predecir el precio semanal por combustible.
