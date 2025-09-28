# File: ingest/scripts/ingest_excel.py
from typing import Dict, Any, Tuple
import pandas as pd
from pathlib import Path
import yaml

def _coerce_bool(series: pd.Series) -> pd.Series:
    # Accept {1,0,True,False,"1","0"} and NaN → False
    return series.map(lambda v: bool(int(v)) if pd.notna(v) and str(v).strip().isdigit() else bool(v) if pd.notna(v) else False)

def load_config(schema_path: str) -> Tuple[dict, dict, dict]:
    with open(schema_path, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    required = conf.get("required", [])
    rename = conf.get("rename", {})
    dtypes = conf.get("dtypes", {})
    return required, rename, dtypes

def ingest_excel(raw_path: str, schema_path: str) -> pd.DataFrame:
    required, rename, dtypes = load_config(schema_path)
    df = pd.read_excel(raw_path)

    # Ensure required columns exist
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns in input: {missing}")

    # Rename
    to_rename = {k: v for k, v in rename.items() if k in df.columns}
    df = df.rename(columns=to_rename)

    # Type coercions
    for col, typ in dtypes.items():
        if col not in df.columns:
            continue
        if typ == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        elif typ == "float":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif typ == "bool":
            df[col] = _coerce_bool(df[col])
        elif typ == "str":
            df[col] = df[col].astype("string").str.strip()
        # else: leave as-is

    # Trim whitespace globally
    df = df.apply(lambda s: s.str.strip() if s.dtype == "string" else s)

    return df
