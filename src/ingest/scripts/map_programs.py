# File: ingest/scripts/map_programs.py
from typing import Dict
import pandas as pd
import yaml

def map_program_flags(df: pd.DataFrame, mapping_path: str) -> pd.DataFrame:
    with open(mapping_path, "r", encoding="utf-8") as f:
        conf = yaml.safe_load(f)

    fnap_map: Dict[str, str] = conf.get("fnap_flags", {})
    texts = conf.get("text_fields", {})
    snap = conf.get("snap", {})

    # Initialize all target columns to sane defaults
    for target in fnap_map.values():
        if target not in df.columns:
            df[target] = False

    # Apply FNAP_* → canonical booleans
    for src_flag, target_col in fnap_map.items():
        if src_flag in df.columns:
            df[target_col] = df[src_flag].fillna(False).astype(bool)

    # Preserve text fields (programs_raw, incentives_desc)
    for target, source in texts.items():
        if source in df.columns:
            df[target] = df[source]
        else:
            df[target] = pd.NA

    # SNAP acceptance details
    opt_txt = snap.get("option_text")
    flag_central = snap.get("central_booth_flag")
    flag_vendor = snap.get("vendor_pos_flag")
    if opt_txt in df.columns:
        df["snap_acceptance"] = df[opt_txt]
    else:
        df["snap_acceptance"] = pd.NA

    df["snap_central_booth"] = df[flag_central].fillna(False).astype(bool) if flag_central in df.columns else False
    df["snap_vendor_pos"] = df[flag_vendor].fillna(False).astype(bool) if flag_vendor in df.columns else False

    return df
