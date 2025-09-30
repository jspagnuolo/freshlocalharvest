# File: ingest/scripts/stage_raw.py
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict

import yaml

RAW_DIR = Path("data/raw")
DATASETS = Path("ingest/config/datasets.yml")


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_dataset_config() -> Dict[str, dict]:
    with open(DATASETS, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f) or {}
    return conf.get("datasets", {})


def stage_raw(src_path: str, dataset_key: str | None = None) -> str:
    """Copy a source Excel into data/raw with a timestamp + checksum in the filename."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(src_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")

    datasets = _load_dataset_config()
    key = dataset_key or "farmers_market"
    cfg = datasets.get(key)
    if cfg is None:
        raise KeyError(f"Unknown dataset '{key}'. Available: {', '.join(sorted(datasets))}")

    prefix = cfg.get("prefix") or f"{key}_"
    stamp = datetime.utcnow().strftime("%Y-%m-%d")
    digest = sha256sum(src)[:12]
    dst_name = f"{prefix}{stamp}_sha256={digest}{src.suffix}"
    dst = RAW_DIR / dst_name
    shutil.copy2(src, dst)
    return str(dst)
