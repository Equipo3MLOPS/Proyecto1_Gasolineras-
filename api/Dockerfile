# API de precios/predicción — imagen con uv (instalación rápida y reproducible).
FROM python:3.12-slim

# uv (gestor de paquetes rápido) desde la imagen oficial de astral.
COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /bin/uv

WORKDIR /app

# Dependencias primero (mejor caché de capas).
COPY requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt

# Código de la API.
COPY app ./app

EXPOSE 8000

# 0.0.0.0 para que sea accesible desde fuera del contenedor.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
