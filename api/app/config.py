"""Configuración de la API (se lee de variables de entorno / .env).

En el Droplet, el `.env` trae las credenciales S3 de SOLO LECTURA del bucket oro.
Para desarrollo local se usa `GOLD_MODE=local`, que lee una copia de las tablas
oro en `LOCAL_GOLD_DIR` (sin necesidad de credenciales).
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # origen de los datos oro: "s3" (producción) | "local" (desarrollo/pruebas)
    gold_mode: str = "s3"

    # ubicación de las tablas oro en S3 (equipo3)
    gold_bucket: str = "cc3105-au-869227452861-us-east-2-an"
    team: str = "equipo3"

    # credenciales S3 de SOLO LECTURA (solo se usan si gold_mode == "s3")
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-2"

    # Databricks (solo se usan si gold_mode == "databricks"): la API lee el oro
    # vía el SQL Warehouse en vez de S3, con un token (PAT) del usuario.
    databricks_host: str = "https://dbc-a56ba7f1-976e.cloud.databricks.com"
    databricks_token: str = ""
    databricks_warehouse_id: str = "aa1fd558f80e0607"
    uc_catalog: str = "workspace"

    # carpeta con los parquet de oro para gold_mode == "local"
    local_gold_dir: str = "local_gold"

    # metadatos de la API
    api_title: str = "API Precios Gasolina GT — equipo3"
    api_version: str = "1.0.0"

    # segundos que se cachean las tablas oro en memoria (frescura vs. latencia)
    cache_ttl_seconds: int = 300


settings = Settings()
