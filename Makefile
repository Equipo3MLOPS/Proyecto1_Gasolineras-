DATABRICKS_PROFILE ?= uvg-mlops

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
	python -m src.pipeline model

validate:             
	databricks bundle validate -p $(DATABRICKS_PROFILE)

deploy:               
	databricks bundle deploy -p $(DATABRICKS_PROFILE)

clean:                
	rm -rf artifacts reports/figures db/gasolineras.db mlflow.db mlruns mlartifacts
