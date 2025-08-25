# Runbook (ad hoc commands worth remembering)

## AMS ingest (Phase 1)
source .venv/bin/activate
python scripts/phase1/ingest_ams_v2.py

## Start API
uvicorn scripts.phase1.api:app --reload --port 8000

## Map UI
open http://127.0.0.1:8000/web/
