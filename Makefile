PORT ?= 8001
.PHONY: serve test smoke ingest

serve:
	uvicorn --app-dir . scripts.phase1.api:app --reload --port $(PORT)

test:
	pytest -q

smoke:
	./scripts/phase1/smoke.sh http://127.0.0.1:$(PORT)

ingest:
	python3 scripts/phase1/ingest_ams_v2.py
