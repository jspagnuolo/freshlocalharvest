# Runbook Cheatsheet

Short reminders for the Excel ingest workflow.

## Stage & ingest
```bash
make stage RAW=/path/to/usda_download.xlsx
make run
```

## Quick validation only
```bash
make validate
```

## View outputs
```bash
ls -lh site/static/data/markets.map.json site/static/data/markets.search.json
cat data/processed/manifest.json | jq '.records_valid'
```

## Preview Hugo site
```bash
make site-dev   # press Ctrl+C to exit
```

## Stop Hugo
```bash
make site-stop
```

## Clean virtualenv
```bash
rm -rf .venv && python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```
