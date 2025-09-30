# File: ingest/scripts/cli.py
import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import typer
import yaml

from ingest.scripts.export_artifacts import export_from_profile
from ingest.scripts.ingest_excel import ingest_excel
from ingest.scripts.map_programs import map_program_flags
from ingest.scripts.stage_raw import stage_raw
from ingest.scripts.enrich import enrich_markets, generate_zip_centroids, generate_city_centroids
from ingest.scripts.validate import basic_validate

APP = typer.Typer(help="Fresh Local Harvest data pipeline.")

SCHEMA = "ingest/config/schema.yml"
DATASETS = "ingest/config/datasets.yml"
MAPPING = "ingest/config/mapping_programs.yml"
EXPORTS = "ingest/config/export_profiles.yml"

RAW_DIR = Path("data/raw")
PROC_DIR = Path("data/processed")
STAGE_DIR = Path("data/staging")


def _sha256_file(path: Path) -> str:
    h = sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_dataset_config() -> Dict[str, dict]:
    with open(DATASETS, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f) or {}
    datasets = conf.get("datasets", {})
    normalized = {}
    for key, cfg in datasets.items():
        if isinstance(cfg, dict):
            normalized[key] = cfg
    return normalized


def _latest_for_glob(pattern: str) -> Path | None:
    matches = sorted(RAW_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _detect_dataset_key(path: Path, datasets: Dict[str, dict]) -> str | None:
    name = path.name.lower()
    for key, cfg in datasets.items():
        prefix = (cfg.get("prefix") or "").lower()
        if prefix and name.startswith(prefix):
            return key
    return None


def _prepare_datasets(overrides: Dict[str, Path] | None = None) -> Tuple[pd.DataFrame, List[dict]]:
    datasets = _load_dataset_config()
    if not datasets:
        raise typer.Exit(code=2)

    overrides = overrides or {}
    frames: List[pd.DataFrame] = []
    sources_meta: List[dict] = []

    for key, cfg in datasets.items():
        schema = cfg.get("schema", SCHEMA)
        label = cfg.get("label", key.replace("_", " ").title())
        category = cfg.get("category", key)
        source_path = overrides.get(key)
        if not source_path:
            glob_pattern = cfg.get("glob")
            if glob_pattern:
                source_path = _latest_for_glob(glob_pattern)
        if not source_path:
            typer.echo(f"[warn] No source file found for dataset '{key}'", err=True)
            continue

        df = ingest_excel(str(source_path), schema)
        if df.empty:
            typer.echo(f"[warn] Source file '{source_path}' produced no records", err=True)
            continue

        df = df.copy()
        df['source_dataset'] = key
        df['source_dataset_label'] = label
        df['listing_type'] = category
        df['listing_type_label'] = label
        source_ids = df['listing_id'].astype('string').str.strip()
        df['source_listing_id'] = source_ids
        df = df[source_ids.notna() & (source_ids != "")]
        df['record_id'] = df['source_dataset'] + ":" + df['source_listing_id']

        frames.append(df)
        sources_meta.append({
            "dataset": key,
            "label": label,
            "path": str(source_path),
            "sha256": _sha256_file(Path(source_path)),
            "records": int(len(df)),
        })

    if not frames:
        typer.echo("[error] No datasets available for processing", err=True)
        raise typer.Exit(code=3)

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined.drop_duplicates(subset=['record_id'], inplace=True)

    return combined, sources_meta


def _run_pipeline(base_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    mapped = map_program_flags(base_df, MAPPING)
    enriched = enrich_markets(mapped)
    valid, rejects = basic_validate(enriched)
    return valid, rejects


def _write_artifacts(valid: pd.DataFrame, rejects: pd.DataFrame, sources_meta: List[dict], exports: dict) -> dict:
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    rejects_path = STAGE_DIR / "rejects.csv"
    rejects.to_csv(rejects_path, index=False)

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

    manifest = {
        "schema_version": "2.0.0",
        "ingested_at": datetime.utcnow().isoformat() + "Z",
        "records_total": int(len(valid) + len(rejects)),
        "records_valid": int(len(valid)),
        "records_rejected": int(len(rejects)),
        "sources": sources_meta,
        "exports": {**exports, "zip_centroids": str(zc_path), "city_centroids": str(cc_path)},
    }

    PROC_DIR.mkdir(parents=True, exist_ok=True)
    man_path = PROC_DIR / "manifest.json"
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    manifest['rejects_path'] = str(rejects_path)
    manifest['zip_centroids_path'] = str(zc_path)
    manifest['city_centroids_path'] = str(cc_path)

    return manifest


@APP.command("stage-raw")
def cmd_stage_raw(
    src: str = typer.Argument(..., help="Path to downloaded USDA Excel"),
    dataset: str = typer.Option("farmers_market", help="Dataset key to associate with this file"),
):
    dst = stage_raw(src, dataset_key=dataset)
    typer.echo(dst)


@APP.command("run")
def cmd_run(
    raw: str = typer.Option(None, help="Optional raw file path to override a dataset"),
    dataset: str = typer.Option(None, help="Dataset key when using --raw (e.g. farmers_market, csa)"),
):
    overrides: Dict[str, Path] = {}
    if raw:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            raise typer.BadParameter(f"Raw file not found: {path}")
        datasets = _load_dataset_config()
        dataset_key = dataset or _detect_dataset_key(path, datasets)
        if not dataset_key:
            raise typer.BadParameter("Unable to determine dataset key; supply --dataset explicitly")
        overrides[dataset_key] = path

    base_df, sources_meta = _prepare_datasets(overrides)
    valid, rejects = _run_pipeline(base_df)
    exports = export_from_profile(valid, EXPORTS)
    manifest = _write_artifacts(valid, rejects, sources_meta, exports)

    typer.echo(json.dumps(manifest, indent=2))


@APP.command("validate")
def cmd_validate():
    base_df, _ = _prepare_datasets()
    valid, rejects = _run_pipeline(base_df)
    typer.echo(f"valid={len(valid)} rejects={len(rejects)}")


@APP.command("export")
def cmd_export():
    staged = STAGE_DIR / "prepared.parquet"
    if not staged.exists():
        raise typer.Exit(code=2)
    df = pd.read_parquet(staged)
    export_from_profile(df, EXPORTS)
    typer.echo("Exported from staged parquet.")


if __name__ == "__main__":
    APP()
