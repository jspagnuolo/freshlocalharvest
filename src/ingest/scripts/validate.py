# File: ingest/scripts/validate.py
from typing import Tuple
import pandas as pd

REJECT_COL = "_reject_reason"

def basic_validate(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split into (valid, rejects) with reason codes."""
    df = df.copy()
    df[REJECT_COL] = ""

    # Required basic fields
    req = ["listing_id", "listing_name", "location_address", "longitude", "latitude"]
    for col in req:
        df.loc[df[col].isna() | (df[col].astype(str).str.len() == 0), REJECT_COL] += f"missing:{col};"

    # Coordinate bounds
    df.loc[(df["longitude"] < -180) | (df["longitude"] > 180) | df["longitude"].isna(), REJECT_COL] += "bad:longitude;"
    df.loc[(df["latitude"] < -90) | (df["latitude"] > 90) | df["latitude"].isna(), REJECT_COL] += "bad:latitude;"

    # Deduplicate by listing_id, keep first
    dupes = df.duplicated(subset=["listing_id"], keep="first")
    df.loc[dupes, REJECT_COL] += "dup:listing_id;"

    rejects = df[df[REJECT_COL] != ""].copy()
    valid = df[df[REJECT_COL] == ""].copy()

    return valid, rejects
