# Despliegue en Databricks — medallón de gasolineras

El mismo código de `src/` corre en **local** (CSV + SQLite) y en **Databricks**
(tablas Delta). Lo único que cambia es el *backend*, controlado por variables de
entorno (ver `src/config.py`):

| `PIPELINE_BACKEND` | Dónde escribe cada capa |
|---|---|
| `local` (default) | CSV en `artifacts/` + SQLite en `db/gasolineras.db` |
| `uc` | Tablas Delta de Unity Catalog: `workspace.bronze/silver/gold.*` |
| `s3` | Tablas Delta por ruta directa: `s3a://cc3105-<capa>-.../<equipo>/<capa>/<tabla>` |

Mapa de buckets (símbolos de la tabla periódica):

| Capa | Bucket | External location |
|---|---|---|
| raw (imágenes) | `cc3105-raw-...` | `xloc-raw` |
| bronze | `cc3105-cusn-...` (CuSn = bronce) | `xloc-cusn` |
| silver | `cc3105-ag-...` (Ag = plata) | `xloc-ag` |
| gold | `cc3105-au-...` (Au = oro) | `xloc-au` |

## Orquestación (Asset Bundle + Job)

`databricks.yml` define un Job con 4 tareas en DAG:

```
extract → transform → load → model
```

Cada tarea ejecuta `databricks/run_stage.py` con un parámetro `stage` distinto.

```bash
databricks bundle validate -p uvg-mlops
databricks bundle deploy   -p uvg-mlops
databricks bundle run medallon_gasolineras -p uvg-mlops
```

Para cambiar de backend o de equipo al desplegar:

```bash
databricks bundle deploy -p uvg-mlops --var="backend=s3,team=equipo3"
```

## ⚠️ Requisito de acceso (pendiente)

Hoy los external locations `xloc-raw/cusn/ag/au` están en **`read_only = true`** y
son propiedad de `arodriguezo@uvg.edu.gt`. Con eso **Unity Catalog no puede
escribir** en los buckets. Para correr la medallón de verdad hace falta UNA de:

- **Backend `uc`:** que el dueño ponga los external locations en modo escritura y
  otorgue `CREATE MANAGED STORAGE` sobre `xloc-cusn/ag/au`. Da tablas UC con nombre.
- **Backend `s3`:** credenciales AWS del equipo (como las usó equipo2) para escribir
  Delta por ruta a `s3a://.../equipo3/...`. No depende del profe, pero da tablas por
  ruta (no gobernadas por UC).

La **lectura** de imágenes del bucket raw ya funciona (los external locations
permiten lectura). El bloqueo es solo de **escritura** de bronze/silver/gold.
