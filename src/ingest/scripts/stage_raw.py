# File: ingest/scripts/stage_raw.py
import os, shutil, hashlib
from datetime import datetime
from pathlib import Path

RAW_DIR = Path("data/raw")

def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def stage_raw(src_path: str) -> str:
    """Copy a source Excel into data/raw with a timestamp + checksum in the filename.
    Returns the destination path string.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(src_path).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    stamp = datetime.utcnow().strftime("%Y-%m-%d")
    digest = sha256sum(src)[:12]
    dst_name = f"farmersmarket_{stamp}_sha256={digest}{src.suffix}"
    dst = RAW_DIR / dst_name
    shutil.copy2(src, dst)
    return str(dst)
