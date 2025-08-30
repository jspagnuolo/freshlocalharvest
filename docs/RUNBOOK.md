# RUNBOOK

Purpose: repeatable steps to boot, verify, and shut down cleanly.  
Everything below is ready for copy/paste.

---

## Start of Day (SOD)

~~~bash
cd ~/freshlocalharvest
make serve                 # uvicorn on :8001 (reload)
open http://127.0.0.1:8001/web/
make smoke                 # hits running server (/health + queries)
make test                  # in-process tests (no server needed)
~~~

---

## Stop / Restart / Status

~~~bash
make stop                  # kill anything on :8001
make restart               # stop then serve
make status                # show what's listening on :8001
~~~

---

## End of Day (EOD)

~~~bash
make test
make smoke
git status -s
git add -A
git commit -m "chore: end-of-session checkpoint (tests pass, smoke green)"
# Optional checkpoint tag (adjust version as you like):
git tag -a v0.2.x -m "Phase 1 stable"
~~~

---

## Recovery Recipes

### Port busy (manual)

~~~bash
lsof -nP -iTCP:8001 -sTCP:LISTEN
pkill -f 'uvicorn .* --port 8001' || true
PIDS=$(lsof -tiTCP:8001 -sTCP:LISTEN); [ -z "$PIDS" ] || kill -9 $PIDS
~~~

### Rebuild venv fully

~~~bash
rm -rf .venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
~~~

### Re-ingest AMS workbook

~~~bash
make ingest     # alias: make injest
sqlite3 db/markets.db 'SELECT COUNT(*) FROM markets_usda;'
~~~

### Re-run server & smoke

~~~bash
make serve
make smoke
~~~

### If `/web/` returns 404 after refactors

~~~bash
# Ensure static mount points to src/api/web and index.html exists
ls -l src/api/web/index.html
python3 - <<'PY'
from pathlib import Path
app = Path("src/api/app.py").resolve()
web = app.parent/"web"/"index.html"
print("app.py:", app)
print("index exists:", web.exists(), "at", web)
PY
# If missing, restore/copy index.html into src/api/web/
~~~

### Use a different DB path (optional)

~~~bash
export FLH_DB="$HOME/freshlocalharvest/db/markets.db"   # default
# or point to an alternate db for manual testing:
export FLH_DB="$HOME/tmp/alt.db"; make serve
~~~

### Notes

- API items include a stable `market_id` (SHA1 of name/city/state/zip/lat/lon) if the DB doesn’t provide one.
- Starlette’s `python_multipart` PendingDeprecationWarning is filtered in `pytest.ini`.
- `PYTHONPATH=src` is used for tests; runtime uses `--app-dir src` and imports `api.app:app`.

---

## Makefile Targets (quick reference)

```text
deps     -> create venv + install requirements
ingest   -> normalize AMS Excel into db/markets.db (alias: injest)
serve    -> run API + web UI (port 8001)
stop     -> kill anything bound to :8001
restart  -> stop then serve
status   -> show process bound to :8001
test     -> run pytest (no server needed)
smoke    -> quick curl checks against running server
enrich   -> (future) SNAP/EBT join when enabled
