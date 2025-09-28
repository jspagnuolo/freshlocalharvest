# File: ingest/scripts/export_artifacts.py
from __future__ import annotations
from typing import Dict
from pathlib import Path
import json
import yaml
import pandas as pd

def _ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

def export_from_profile(df: pd.DataFrame, profile_path: str) -> Dict[str, str]:
    with open(profile_path, "r", encoding="utf-8") as f:
        profiles = yaml.safe_load(f)

    shas = {}
    for name, spec in profiles.items():
        path = Path(spec["path"])
        fields = spec["fields"]

        _ensure_parent(path)

        if fields == ["*"]:
            data = df
        else:
            keep = [f for f in fields if f in df.columns]
            data = df[keep]

        if path.suffix == ".json":
            # Write JSON (minified for web)
            with open(path, "w", encoding="utf-8") as out:
                json.dump(json.loads(data.to_json(orient="records")), out, ensure_ascii=False, separators=(",", ":"))
        elif path.suffix == ".parquet":
            data.to_parquet(path, index=False)
        else:
            # Default to CSV
            data.to_csv(path, index=False)

        shas[name] = str(path)

    return shas
