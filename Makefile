SHELL := /bin/bash
.ONESHELL:

VENV    := .venv
PY      := $(VENV)/bin/python3
PIP     := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST  := $(VENV)/bin/pytest
PORT    ?= 8001

# Ensure Python sees the src/ layout
PYENV := PYTHONPATH=src

.PHONY: deps ingest injest serve test smoke enrich

deps:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

ingest:
	$(PY) src/ingest/ingest_ams_farmersmarket.py
	@echo -n "markets_usda rows: "
	@sqlite3 db/markets.db 'SELECT COUNT(*) FROM markets_usda;'

# alias for fat-finger muscle memory
injest: ingest

serve:
	@if lsof -tiTCP:$(PORT) -sTCP:LISTEN >/dev/null; then \
	  echo "Port $(PORT) is busy. Run 'make stop' first."; exit 1; \
	fi
	$(UVICORN) --app-dir src api.app:app --reload --port $(PORT)

test:
	$(PYENV) $(PYTEST) -q

smoke:
	scripts/ops/smoke.sh http://127.0.0.1:$(PORT)

# placeholder for SNAP join later
enrich:
	@echo "No enrich step yet."

.PHONY: stop restart status

stop:
	- pkill -f 'uvicorn .* --port $(PORT)' || true
	- PIDS="$$(lsof -tiTCP:$(PORT) -sTCP:LISTEN)"; \
	  if [ -n "$$PIDS" ]; then kill $$PIDS || true; fi
	@sleep 1
	@echo "Stopped anything on :$(PORT) (if it was running)."

restart: stop
	$(MAKE) serve

status:
	@lsof -nP -iTCP:$(PORT) -sTCP:LISTEN || true
	
# --- Hugo site ---------------------------------------------------------------

site-dev:
	# why: consistent local preview with drafts and live reload
	cd site && hugo server -D

site-build:
	# why: reproduce CI build locally; publishes to site/public
	cd site && hugo --gc --minify --environment production
