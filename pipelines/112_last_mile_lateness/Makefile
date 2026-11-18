SHELL := /bin/bash
VENV  := .venv
PY    := $(VENV)/bin/python
ENV   := set -a; source .env; set +a;
export PYTHONPATH := src

FIRST ?= 2018-07-19
LAST  ?= 2018-08-26

.PHONY: setup up down data run backfill freshness model dashboard test lint package tf-validate clean

setup:
	python3.11 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r requirements-dev.txt
	cp -n .env.example .env || true

up:
	docker compose up -d --wait

down:
	docker compose down

data:  ## downloads ~2.3 GB once, then writes one folder per route date
	mkdir -p data/source
	for f in route_data actual_sequences package_data travel_times; do \
	  [ -f data/source/$$f.json ] || curl -fsSL -o data/source/$$f.json \
	  https://amazon-last-mile-challenges.s3.amazonaws.com/almrrc2021/almrrc2021-data-training/model_build_inputs/$$f.json; \
	done
	$(PY) -m lastmile.split_source --source data/source --out data/drops

run:  ## make run DATE=2018-07-27
	$(ENV) $(PY) -m lastmile.runner run $(DATE)

backfill:
	$(ENV) $(PY) -m lastmile.runner backfill $(FIRST) $(LAST)

freshness:
	$(ENV) $(PY) -m lastmile.runner freshness --expect $(LAST)

model:
	$(ENV) $(PY) -m lastmile.model

dashboard:
	$(ENV) $(VENV)/bin/streamlit run dashboard/app.py

test:
	$(PY) -m pytest -q

lint:
	$(VENV)/bin/ruff check src tests dashboard

package:  ## build/lambda (handler code) and build/lastmile.zip (Glue --extra-py-files)
	rm -rf build && mkdir -p build/lambda
	cp -r src/lastmile build/lambda/
	cp sql/redshift/load_partition.sql build/lambda/lastmile/
	find build -name __pycache__ -prune -exec rm -rf {} +
	cd src && zip -qr ../build/lastmile.zip lastmile -x '*/__pycache__/*'

tf-validate: package
	docker run --rm -v $(PWD):/w -w /w/infra/terraform hashicorp/terraform:1.9.8 init -backend=false -input=false >/dev/null
	docker run --rm -v $(PWD):/w -w /w/infra/terraform hashicorp/terraform:1.9.8 fmt -check -diff
	docker run --rm -v $(PWD):/w -w /w/infra/terraform hashicorp/terraform:1.9.8 validate

clean:
	docker compose down -v
	rm -rf data/drops spark-warehouse artifacts
