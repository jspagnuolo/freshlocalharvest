# Makefile (only the relevant bits)
SHELL := /bin/bash
.ONESHELL:

PORT ?= 8001

ingest:
	set -euo pipefail
	python3 scripts/phase1/ingest_ams_farmersmarket.py
	@echo -n "markets_usda rows: "
	@sqlite3 db/markets.db 'SELECT COUNT(*) FROM markets_usda;'

serve:
	uvicorn --app-dir . scripts.phase1.api:app --reload --port $(PORT)

test:
	pytest -q

smoke:
	./scripts/phase1/smoke.sh http://127.0.0.1:$(PORT)
