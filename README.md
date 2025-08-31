# Fresh Local Harvest

Static site (Hugo) + tiny API proxy used during data export. The production site is deployed on **Cloudflare Pages** and reads prebuilt JSON (`site/static/data/markets.json`) for the map.

---

## Prereqs

- **Python 3.11+**
- **Hugo** (extended)
- Local dev uses Make targets (see below)

## Quick Start (Local)

```bash
# 1) Create venv and install deps
python3.11 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt "httpx[http2]"

# 2) Start the API (only needed when exporting data)
export USDA_API_KEY='YOUR_REAL_KEY'
make restart
curl -s http://127.0.0.1:8001/health  # -> has_key: true

# 3) Export markets.json for the site
make update-data
ls -lh site/static/data/markets.json

# 4) Preview the site
make site-dev
# open http://localhost:1313/map/

## Data Refresh

This project pulls farmers market data from the USDA Local Food Portal API.

### Regenerating the Database
The SQLite DB (`db/markets.db`) is **not tracked in Git** to keep the repo clean.  
If you need to regenerate it:

```bash
# Activate venv
. .venv/bin/activate

# Set your USDA API key
export USDA_API_KEY='your_key_here'

# Restart the API
make restart

# Export data to db/markets.db and site/static/data/markets.json
make update-data

## Status (Aug 2025): Paused — USDA TLS cert expired
USDA endpoint `https://search.ams.usda.gov/farmersmarkets/` presents an expired/invalid chain (expired Mar 22, 2025).
Automation is paused. Once fixed, we’ll switch the exporter to a Cloudflare Worker proxy and re-enable cron.
