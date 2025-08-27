# RUNBOOK

Purpose: repeatable steps to boot, verify, and shut down cleanly.  
Everything below is ready for copy/paste.

---

## Start of Day (SOD)

~~~bash
# Copy/paste: SOD bootstrap
cd ~/freshlocalharvest
make serve                 # uvicorn on :8001 (reload)
open http://127.0.0.1:8001/web/
make smoke                 # hits running server (/health + queries)
make test                  # in-process tests (no server needed)
~~~

---

## End of Day (EOD)

~~~bash
# Copy/paste: EOD checkpoint
make test
make smoke
git status -s
git add -A
git commit -m "chore: end-of-session checkpoint (tests pass, smoke green)"
# Optional checkpoint tag:
git tag -a v0.2.x -m "Phase 1 stable"
~~~

---

## Recovery Recipes

### Port busy

~~~bash
# Copy/paste: find/kill server on 8001
lsof -nP -iTCP:8001 -sTCP:LISTEN
kill <PID>     # or: pkill -f 'uvicorn .* --port 8001'
~~~

### Rebuild venv fully

~~~bash
# Copy/paste: rebuild virtualenv from lockfile
rm -rf .venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
~~~

### Re-ingest AMS workbook

~~~bash
# Copy/paste: normalize AMS Excel into SQLite
make ingest     # alias: make injest
sqlite3 db/markets.db 'SELECT COUNT(*) FROM markets_usda;'
~~~

### Re-run server & smoke

~~~bash
# Copy/paste: run server and quick checks
make serve
make smoke
~~~

### Silence pytest warning

We filter Starlette’s `python_multipart` PendingDeprecationWarning via `pytest.ini`.  
(Already added; no action needed unless you remove `pytest.ini`.)

---

## Optional: Daily Journal

Create a dated note so tomorrow’s “Next” is obvious.

~~~bash
# Copy/paste: create journal folder and today's entry
mkdir -p docs/journal
d=$(date +%F)
cat > docs/journal/$d.md <<'MD'
# YYYY-MM-DD

## Done
- 

## Next
- 

## Notes
- 
MD
~~~

---

## Makefile Targets (quick reference)

- `ingest` → normalize AMS Excel into `db/markets.db` (alias: **injest**)  
- `serve` → run API + web UI (port **8001**)  
- `test` → run pytest (no server needed)  
- `smoke` → quick curl checks against running server  
- `enrich` → (future) SNAP/EBT join when enabled  
- `deps` → create venv + install requirements (if defined)  
