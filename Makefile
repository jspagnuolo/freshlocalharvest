# File: Makefile
SHELL := /bin/bash
.ONESHELL:

# --- Virtualenv & tools -------------------------------------------------------
VENV    := .venv
PY      := $(VENV)/bin/python3
PIP     := $(VENV)/bin/pip
PYTEST  := $(VENV)/bin/pytest

# --- Options ------------------------------------------------------------------
RAW     ?=                              # optional: path to USDA Excel for staging
CLI     := $(PY) -m ingest.scripts.cli  # Typer CLI entrypoint for the new pipeline

.PHONY: deps stage run validate export ingest injest test site-build update-data site-stop site-dev

# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------
deps:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# -----------------------------------------------------------------------------
# New Excel → JSON pipeline (preferred)
# -----------------------------------------------------------------------------
# Stage a freshly downloaded USDA Excel into data/raw/ with checksum in filename
stage:
	@if [ -z "$(RAW)" ]; then \
	  echo "Usage: make stage RAW=/absolute/path/to/usda_download.xlsx"; \
	  exit 2; \
	fi
	$(CLI) stage-raw "$(RAW)"

# Run the full pipeline (ingest → map programs → validate → export → manifest)
run:
	@if [ -n "$(RAW)" ]; then \
	  $(CLI) run --raw "$(RAW)"; \
	else \
	  $(CLI) run; \
	fi

# Validate only (quick sanity checks; writes rejects.csv)
validate:
	$(CLI) validate

# Export from a pre-staged parquet (advanced)
export:
	$(CLI) export

# -----------------------------------------------------------------------------
# Back-compat targets (keep muscle memory working)
# -----------------------------------------------------------------------------
# Legacy "ingest" now routes to the new pipeline
ingest:
	@echo "[info] 'make ingest' now uses the Excel pipeline (see 'make run')."
	$(MAKE) run

# Alias for fat-finger muscle memory
injest: ingest

test:
	$(PY) -m pytest -q

# -----------------------------------------------------------------------------
# Hugo site
# -----------------------------------------------------------------------------
site-build:
	# why: reproduce CI build locally; publishes to site/public
	cd site && hugo --gc --minify --environment production

# Update site data files.
# If RAW is provided, this will stage then run; otherwise it runs using the latest staged Excel.
update-data:
	@if [ -n "$(RAW)" ]; then \
	  $(MAKE) stage RAW="$(RAW)"; \
	fi
	$(MAKE) run
	@ls -lh site/static/data/markets.map.json site/static/data/markets.search.json || true

site-stop:
	- pkill -f "hugo server.*1313" || true
	- PIDS="$$(lsof -tiTCP:1313 -sTCP:LISTEN)"; \
	  if [ -n "$$PIDS" ]; then kill $$PIDS || true; fi
	@sleep 1
	@echo "Stopped Hugo on :1313 (if it was running)."

site-dev:
	cd site && hugo server -D --disableFastRender --ignoreCache --forceSyncStatic --port 1313
