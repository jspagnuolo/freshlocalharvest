# File: ingest/scripts/cli.py
import json
from pathlib import Path
import typer
import pandas as pd
from datetime import datetime
from hashlib import sha256

from ingest.scripts.stage_raw import stage_raw
from ingest.scripts.ingest_excel import ingest_excel
from ingest.scripts.map_programs import map_program_flags
from ingest.scripts.validate import basic_validate
from ingest.scripts.export_artifacts import export_from_profile
from ingest.scripts.enrich import enrich_markets, generate_zip_centroids, generate_city_centroids

APP = typer.Typer(help="Fresh Local Harvest data pipeline.")

SCHEMA = "ingest/config/schema.yml"
MAPPING = "ingest/config/mapping_programs.yml"
EXPORTS = "ingest/config/export_profiles.yml"

RAW_DIR = Path("data/raw")
PROC_DIR = Path("data/processed")
STAGE_DIR = Path("data/staging")

def _latest_raw() -> Path:
    files = sorted(RAW_DIR.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise typer.Exit(code=1)
    return files[0]

def _sha256_file(path: Path) -> str:
    h = sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

@APP.command("stage-raw")
def cmd_stage_raw(src: str = typer.Argument(..., help="Path to downloaded USDA Excel")):
    dst = stage_raw(src)
    typer.echo(dst)

@APP.command("run")
def cmd_run(raw: str = typer.Option(None, help="Optional raw file path to use (defaults to latest in data/raw)")):
    raw_path = Path(raw) if raw else _latest_raw()
    raw_sha = _sha256_file(raw_path)

    # 1) Ingest
    df = ingest_excel(str(raw_path), SCHEMA)

    # 2) Map programs
    df = map_program_flags(df, MAPPING)

    # 3) Enrich with normalized address + search helpers
    df = enrich_markets(df)

    # 4) Validate (split valid/rejects)
    valid, rejects = basic_validate(df)

    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    rejects_path = STAGE_DIR / "rejects.csv"
    rejects.to_csv(rejects_path, index=False)

    # 5) Export
    exports = export_from_profile(valid, EXPORTS)

    # 6) ZIP and city centroid exports (for front-end radius lookups)
    zip_centroids = generate_zip_centroids(valid)
    zc_path = Path("site/static/data/zip.centroids.json")
    zc_path.parent.mkdir(parents=True, exist_ok=True)
    with open(zc_path, "w", encoding="utf-8") as f:
        json.dump(zip_centroids, f, separators=(",", ":"), sort_keys=True)

    city_centroids = generate_city_centroids(valid)
    cc_path = Path("site/static/data/city.centroids.json")
    cc_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cc_path, "w", encoding="utf-8") as f:
        json.dump(city_centroids, f, separators=(",", ":"), sort_keys=True)

    # 7) Manifest
    manifest = {
        "schema_version": "1.0.0",
        "source_file": str(raw_path),
        "source_sha256": raw_sha,
        "ingested_at": datetime.utcnow().isoformat() + "Z",
        "records_total": int(len(df)),
        "records_valid": int(len(valid)),
        "records_rejected": int(len(rejects)),
        "exports": {**exports, "zip_centroids": str(zc_path), "city_centroids": str(cc_path)},
    }
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    man_path = PROC_DIR / "manifest.json"
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    typer.echo(json.dumps(manifest, indent=2))

@APP.command("validate")
def cmd_validate():
    raw_path = _latest_raw()
    df = ingest_excel(str(raw_path), SCHEMA)
    df = map_program_flags(df, MAPPING)
    df = enrich_markets(df)
    valid, rejects = basic_validate(df)
    typer.echo(f"valid={len(valid)} rejects={len(rejects)}")

@APP.command("export")
def cmd_export():
    # Expect a prepared staging file (advanced use)
    staged = STAGE_DIR / "prepared.parquet"
    if not staged.exists():
        raise typer.Exit(code=2)
    df = pd.read_parquet(staged)
    export_from_profile(df, EXPORTS)
    typer.echo("Exported from staged parquet.")

if __name__ == "__main__":
    APP()
