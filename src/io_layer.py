from __future__ import annotations

import io as _io
from pathlib import Path

import pandas as pd

from . import config as C

_SPARK = None


def _spark():
    """Devuelve (y cachea) la SparkSession. Solo se usa en backends uc/s3."""
    global _SPARK
    if _SPARK is None:
        try:
            from pyspark.sql import SparkSession
        except ImportError as exc:
            raise RuntimeError(
                f"El backend '{C.BACKEND}' necesita pyspark/Databricks, pero no "
                "está disponible en este entorno. "
            ) from exc
        _SPARK = SparkSession.builder.getOrCreate()
    return _SPARK





def read_df(dataset: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    if C.BACKEND == "local":
        return pd.read_csv(C.DATASETS[dataset]["csv"], parse_dates=parse_dates)

    if C.BACKEND == "uc":
        sdf = _spark().table(C.uc_table(dataset))
    else:  
        sdf = _spark().read.format("delta").load(C.s3_path(dataset))

    pdf = sdf.toPandas()
    for col in parse_dates or []:
        if col in pdf.columns:
            pdf[col] = pd.to_datetime(pdf[col])
    return pdf


def write_df(df: pd.DataFrame, dataset: str) -> None:
    """Escribe (overwrite) una tabla. En uc/s3 crea tabla EXTERNA Delta en el
    bucket del equipo."""
    if C.BACKEND == "local":
        path = C.DATASETS[dataset]["csv"]
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        return

    writer = (
        _spark()
        .createDataFrame(df)
        .write.mode("overwrite")
        .option("overwriteSchema", "true")
    )
    if C.BACKEND == "uc":
        full = C.uc_table(dataset)
        loc = C.s3_path(dataset)
        _drop_if_relocating(full, loc)
        writer.format("delta").option("path", loc).saveAsTable(full)
        _set_table_comment(full, C.DATASETS[dataset].get("comment"))
        set_column_comments(dataset)
    else:
        writer.format("delta").save(C.s3_path(dataset))


def merge_df(df: pd.DataFrame, dataset: str, keys: list[str]) -> None:
    """Escritura idempotente (upsert) por `keys`. En local deduplica el CSV;
    en uc hace MERGE INTO sobre la tabla externa Delta. Un df vacío crea (o
    conserva) la tabla con su esquema, sin insertar filas."""
    if C.BACKEND == "local":
        path = C.DATASETS[dataset]["csv"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not df.empty:
            old = pd.read_csv(path)
            df = pd.concat([old, df], ignore_index=True)
        df = df.drop_duplicates(subset=keys, keep="last").reset_index(drop=True)
        df.to_csv(path, index=False)
        return

    if df.empty:
        sdf = _spark().createDataFrame([], _pandas_to_spark_schema(df))
    else:
        sdf = _spark().createDataFrame(df)
    _merge_sdf(sdf, dataset, keys)
    _set_table_comment(C.uc_table(dataset), C.DATASETS[dataset].get("comment"))
    set_column_comments(dataset)


def _pandas_to_spark_schema(df: pd.DataFrame):
    from pyspark.sql.types import (
        BooleanType, DoubleType, LongType, StringType, StructField, StructType,
    )
    mapping = {"object": StringType(), "float64": DoubleType(),
               "int64": LongType(), "bool": BooleanType()}
    fields = [
        StructField(c, mapping.get(str(df[c].dtype), StringType()), True)
        for c in df.columns
    ]
    return StructType(fields)





def write_photos_bronze(dataset: str, images_dir: str) -> int:
    """Ingesta las fotos .HEIC a `bronze.fotos_precios`.

    `images_dir` es un string (ruta local, Volume o URI s3://) — NO un Path, para
    no manglear el '//' de las URIs S3.

    - uc: las lee con Spark `binaryFile` (contenido binario) y hace MERGE por
      `path` (carga incremental: una segunda corrida no duplica).
    - local: registra metadatos + ruta (sin binario, para pruebas sin Spark).
    """
    if C.BACKEND == "local":
        d = Path(images_dir)
        files = sorted(d.glob("*.HEIC")) + sorted(d.glob("*.heic"))
        ahora = pd.Timestamp.utcnow()
        rows = [
            {
                "path": str(p),
                "modificationTime": pd.Timestamp(p.stat().st_mtime, unit="s"),
                "length": p.stat().st_size,
                "_source_file": str(p),
                "_ingestion_timestamp": ahora,
            }
            for p in files
        ]
        merge_df(pd.DataFrame(rows), dataset, keys=["path"])
        return len(rows)

    from pyspark.sql import functions as F

    sdf = (
        _spark()
        .read.format("binaryFile")
        .option("pathGlobFilter", "*.[Hh][Ee][Ii][Cc]")
        .option("recursiveFileLookup", "true")      
        .load(str(images_dir))
        .select("path", "modificationTime", "length", "content")
        .withColumn("_source_file", F.col("path"))
        .withColumn("_ingestion_timestamp", F.current_timestamp())
    )
    _merge_sdf(sdf, dataset, keys=["path"])
    _set_table_comment(C.uc_table(dataset), C.DATASETS[dataset].get("comment"))
    return sdf.count()


def open_photo(row) -> object:
    """Devuelve algo que PIL.Image.open acepta para leer el EXIF de la foto:
    la ruta local, o un buffer con el binario guardado en bronce (uc)."""
    if C.BACKEND == "local":
        return Path(row["_source_file"])
    return _io.BytesIO(row["content"])


def photo_bytes(row) -> bytes:
    """Bytes crudos de la foto (para mandarla al modelo de visión)."""
    if C.BACKEND == "local":
        return Path(row["_source_file"]).read_bytes()
    return bytes(row["content"])





def _merge_sdf(sdf, dataset: str, keys: list[str]) -> None:
    full = C.uc_table(dataset)
    loc = C.s3_path(dataset)
    spark = _spark()
    _drop_if_relocating(full, loc)
    if not spark.catalog.tableExists(full):
        sdf.limit(0).write.format("delta").option("path", loc).saveAsTable(full)
    sdf.createOrReplaceTempView("_src_merge")
    on = " AND ".join(f"t.`{k}` = s.`{k}`" for k in keys)
    spark.sql(
        f"MERGE INTO {full} t USING _src_merge s ON {on} "
        "WHEN MATCHED THEN UPDATE SET * "
        "WHEN NOT MATCHED THEN INSERT *"
    )


def _drop_if_relocating(full_name: str, target_loc: str) -> None:
    """Migra tablas 'managed' a externas sin romper reruns.

    Si la tabla existe pero NO apunta ya al bucket destino, la elimina para
    recrearla como tabla externa en S3. Ojo: UC reporta la ubicacion de una
    tabla *managed* como vacia, por eso el criterio es "distinta del destino"
    (incluye vacia), no "truthy". Si ya es externa en el destino, no hace nada.
    """
    spark = _spark()
    try:
        if not spark.catalog.tableExists(full_name):
            return
    except Exception:
        return
    cur_loc = ""
    try:
        row = spark.sql(f"DESCRIBE DETAIL {full_name}").select("location").collect()
        if row and row[0][0]:
            cur_loc = row[0][0]
    except Exception:
        cur_loc = ""
    if cur_loc.rstrip("/") != target_loc.rstrip("/"):
        print(f"[io] recreando {full_name} como externa en {target_loc} "
              f"(ubicacion previa: {cur_loc or 'managed/desconocida'})")
        spark.sql(f"DROP TABLE {full_name}")


def _set_table_comment(full_name: str, comment: str | None) -> None:
    if not comment:
        return
    try:
        _spark().sql(f"COMMENT ON TABLE {full_name} IS '{comment.replace(chr(39), chr(8217))}'")
    except Exception as exc:
        print(f"[io] aviso: no se pudo comentar {full_name}: {exc}")


def set_column_comments(dataset: str) -> None:
    """Comenta cada columna de las tablas oro (la rubrica lo pide)."""
    if C.BACKEND != "uc":
        return
    cols = C.COMENTARIOS_COLUMNAS.get(dataset)
    if not cols:
        return
    full = C.uc_table(dataset)
    for col, com in cols.items():
        try:
            _spark().sql(
                f"ALTER TABLE {full} ALTER COLUMN `{col}` "
                f"COMMENT '{com.replace(chr(39), chr(8217))}'"
            )
        except Exception as exc:
            print(f"[io] aviso: no se pudo comentar {full}.{col}: {exc}")


def target_name(dataset: str) -> str:
    if C.BACKEND == "local":
        return str(C.DATASETS[dataset]["csv"])
    return C.uc_table(dataset) if C.BACKEND == "uc" else C.s3_path(dataset)
