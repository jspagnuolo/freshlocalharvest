<!-- File: README.md -->
# Fresh Local Harvest — Data Pipeline & Site

Static site (Hugo) + a **local ingest pipeline** that converts the manually downloaded USDA Excel file into small, app-ready JSON artifacts for the map/search UI. The production site is deployed on **Cloudflare Pages** and reads prebuilt JSON from `site/static/data/`.

> **Status (Sept 2025):** The FastAPI proxy has been removed. This repository now focuses solely on the Excel ingest pipeline that ships JSON/Parquet artifacts.

---

## Prereqs

- **Python 3.11+**
- **Hugo (extended)**
- Recommended: a fresh virtualenv for this repo.

## Quick Start

    # 0) Setup
    python3.11 -m venv .venv
    . .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    # 1) Stage the Excel you downloaded from the USDA site
    python -m ingest.scripts.cli stage-raw /path/to/usda_download.xlsx
    # -> copies to data/raw/farmersmarket_YYYY-MM-DD_sha256=<digest>.xlsx

    # 2) Run the full pipeline (ingest → map programs → validate → export → manifest)
    python -m ingest.scripts.cli run

    # 3) Verify outputs
    ls -lh site/static/data/markets.map.json
    ls -lh site/static/data/markets.search.json
    ls -lh data/processed/markets.full.parquet
    cat data/processed/manifest.json | jq .

    # 4) Preview the site locally (Hugo)
    # If you already have a Make target, use it; otherwise:
    hugo server -s site -D
    # open http://localhost:1313/map/

If you prefer Make targets, this repo includes:

    make stage RAW=/path/to/usda_download.xlsx
    make run
    make validate
    make export

---

## What the pipeline produces

- **site/static/data/markets.map.json**  
  Marker-friendly payload used by the Hugo map. Includes name, organization, geocode, full address pieces, location descriptions, and high-level SNAP details.

- **site/static/data/markets.search.json**  
  Extended search index powering the UI filters. Contains the address parts, search tokens, program flags, and coordinates for list/map synchronization.

- **site/static/data/zip.centroids.json**  
  ZIP code → latitude/longitude lookup generated from USPS data (via pgeocode). Used to power radius-based ZIP searches on the map.

- **data/processed/markets.full.parquet**  
  The cleaned canonical table for analysis (keep this out of the site bundle).

- **data/staging/rejects.csv**  
  Any rows excluded by validation, with reason codes.

- **data/processed/manifest.json**  
  Provenance (source filename + SHA256), record counts, and export paths.

---

## Config-driven behavior (edit without touching code)

- **ingest/config/schema.yml**  
  - Required columns  
  - Column renames (e.g., `location_x → longitude`, `orgnization → organization`)  
  - Type coercions (datetime/float/bool/string)

- **ingest/config/mapping_programs.yml**  
  - Maps USDA flags to canonical program fields:  
    `FNAP_1→program_wic`, `FNAP_2→program_snap`, `FNAP_3→program_incentives`, `FNAP_4→program_wic_fmnp`, `FNAP_5→program_senior_fmnp`  
  - Promotes SNAP acceptance details: `snap_acceptance`, `snap_central_booth`, `snap_vendor_pos`  
  - Preserves raw text fields: `programs_raw`, `program_incentives_desc`

- **ingest/config/export_profiles.yml**  
  - Which fields go into each artifact and where they’re written on disk.

> **Compatibility note:** If your current map code still expects `site/static/data/markets.json`, either (a) update it to read `markets.map.json` + `markets.search.json`, or (b) add an extra export profile writing a compatibility JSON at `site/static/data/markets.json`.

---

## Validation (what we check)

- Required fields present: `listing_id`, `listing_name`, `location_address`, `longitude`, `latitude`  
- Coordinate bounds (`lon ∈ [-180,180]`, `lat ∈ [-90,90]`)  
- Duplicate `listing_id` (first wins; dupes sent to `rejects.csv`)  
- Clean booleans from USDA 0/1/NaN to true/false  
- State normalization (2-letter uppercase when provided)

---

## Directory layout (high-level)

    ingest/
      config/                    # YAML configs (schema, mappings, export profiles)
      scripts/                   # CLI + step scripts (stage, ingest, map, validate, export)
    data/
      raw/                       # timestamped Excel drops (staged)
      staging/                   # rejects, intermediate
      processed/                 # parquet + manifest
    site/
      static/data/               # JSON artifacts consumed by the Hugo site

---

## Troubleshooting

- **“Missing required columns” on run**  
  Ensure you downloaded the correct Excel and didn’t open/save it with altered headers. Check `ingest/config/schema.yml` and update mappings if USDA changes column names.

- **Rows land in `rejects.csv`**  
  Open the file and review the `_reject_reason` column (e.g., `missing:latitude;bad:longitude;dup:listing_id;`).

- **Site can’t find JSON**  
  Confirm the files exist at `site/static/data/`. If your map still reads `markets.json`, switch to `markets.map.json` or add a compatibility export in `export_profiles.yml`.
