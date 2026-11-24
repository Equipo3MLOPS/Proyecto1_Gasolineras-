# Linaje de datos en Unity Catalog

## Cómo funciona
En Unity Catalog el **linaje se captura automáticamente** cuando el pipeline
lee/escribe tablas UC vía Spark/Delta. No hay que instrumentar nada en el código:
con solo correr el Job con `backend=uc`, UC registra:

- **Linaje de tablas:** raw → bronze → silver → gold.
- **Linaje de columnas:** de qué columna de origen sale cada columna.
- **Qué Job/notebook** produjo cada tabla.

> El grafo de linaje se **puebla al correr** el Job en Databricks (requiere el
> acceso de escritura a los buckets). Antes de la primera corrida está vacío.

## Cómo verlo
Catalog → `workspace` → schema (`bronze` / `silver` / `gold`) → tabla → pestaña
**Lineage** (upstream / downstream, y linaje a nivel de columna).

## Metadatos que agregamos (para dejarlo bien documentado)
- **Comentarios de schema** (ya existían): bronze/silver/gold describen cada capa.
- **Comentarios de tabla:** cada tabla se auto-comenta al escribirse — ver
  `src/io_layer.py` → `_set_table_comment`, con los textos en `config.DATASETS`.

## Versionado de datos — por qué NO usamos DVC
Delta Lake ya versiona cada escritura (**time travel**), que es justo lo que daría
DVC (versionar datos + reproducibilidad), sin un segundo sistema en paralelo:

```sql
DESCRIBE HISTORY workspace.gold.precios_combustible;
SELECT * FROM workspace.gold.precios_combustible VERSION AS OF 3;
```
