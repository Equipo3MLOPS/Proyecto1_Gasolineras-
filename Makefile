DATABRICKS_PROFILE ?= uvg-mlops
PY ?= .venv-oro/bin/python

.PHONY: help install test lint run run-no-eda model validate deploy clean

help:                 
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:              
	python -m pip install -U pip
	python -m pip install -e ".[dev]"

test:                 
	pytest -q

lint:                 
	ruff check src tests

run:                  
	python -m src.pipeline

run-no-eda:           
	python -m src.pipeline --no-eda

model:                
	python -m src.pipeline modelo

validate:             
	databricks bundle validate -p $(DATABRICKS_PROFILE)

deploy:               
	databricks bundle deploy -p $(DATABRICKS_PROFILE)

clean:                
	rm -rf artifacts reports/figures db/gasolineras.db mlflow.db mlruns mlartifacts

# --- Modelo en local con los datos reales de Oro -------------------------
venv-modelo:          ## crea .venv-oro con lo necesario para el modelo
	python3.14 -m venv .venv-oro
	.venv-oro/bin/pip install databricks-sdk pandas scikit-learn mlflow pillow pillow-heif pytest

oro-descargar:        ## baja las tablas Oro de S3 (vía Databricks) a artifacts/gold/
	$(PY) scripts/descargar_oro.py

modelo-local: oro-descargar   ## descarga Oro y entrena/predice en local
	PIPELINE_BACKEND=local MLFLOW_DISABLE_AGENT_HINT=1 $(PY) -m src.pipeline modelo

mlflow-ui:            ## abre la interfaz de MLflow local en http://127.0.0.1:5001
	$(PY) -m mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5001

modelo-databricks: oro-descargar   ## entrena en local y registra todo en el MLflow de Databricks
	PIPELINE_BACKEND=local MLFLOW_DISABLE_AGENT_HINT=1 \
	MLFLOW_TRACKING_URI=databricks://$(DATABRICKS_PROFILE) \
	MLFLOW_EXPERIMENT_PATH=/Shared/equipo3_gasolina_direccion \
	MLFLOW_REGISTERED_MODEL=workspace.default.equipo3_modelo_direccion \
	$(PY) -m src.pipeline modelo
