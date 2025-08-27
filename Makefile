SHELL := /bin/bash
.ONESHELL:

VENV    := .venv
PY      := $(VENV)/bin/python3
PIP     := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST  := $(VENV)/bin/pytest

PORT ?= 8001

# Why: ensure deps are installed in the venv we will actually use
deps:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

ingest:  ## normalize AMS workbook -> db/markets.db
	$(PY) scripts/phase1/ingest_ams_farmersmarket.py
	@echo -n "markets_usda rows: "
	@sqlite3 db/markets.db 'SELECT COUNT(*) FROM markets_usda;'

serve:
	$(UVICORN) --app-dir . scripts.phase1.api:app --reload --port $(PORT)

test:
	$(PYTEST) -q

smoke:
	./scripts/phase1/smoke.sh http://127.0.0.1:$(PORT)

.PHONY: ingest injest serve test smoke enrich deps

injest: ingest   # alias for my future self who types fast
