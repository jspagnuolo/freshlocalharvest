#!/usr/bin/env python3
# Why: normalize AMS Excel to a skinny, consistent schema for the MVP.

import argparse, hashlib, json, os, sqlite3, sys, time
from datetime import datetime
import pandas as pd

KEEP_COLS = [
    "market_id","name","street","city","state","zip","lat","lon",
    "website","phone","accepts_snap","hours_raw","season_start","season_end",
    "source","source_file","source_updated_at","ingested_at"
]

# Why: AMS headers drift; map by fuzzy keys.
CANDIDATES = {
    "market_id":   ["fmid","market_id","id"],
    "name":        ["marketname","market_name","name","market"],
    "street":      ["street","street_address","address1","address","addr1"],
    "city":        ["city","town","municipality"],
    "state":       ["state","st"],
    "zip":         ["zip","zipcode","postal_code","zip_code"],
    "lat":         ["lat","latitude","y"],
    "lon":         ["lon","long","longitude","x"],
    "website":     ["website","web","url","market_website"],
    "phone":       ["phone","telephone","contact_phone","market_phone"],
    "accepts_snap":["accepts_snap","snap","ebt","accepts_ebt","snap_status"],
    # hours/season arrive in many shapes; aggregate below
    "season_start":["season_start","season1start","season1date_start"],
    "season_end":  ["season_end","season1end","season1date_end"],
    "hours_raw":   ["hours","schedule","season1time","season1times","season1time_range"],
}

def norm(s): return s.strip().lower().replace(" ", "_")

def pick(series, aliases):
    for a in aliases:
        if a in series: return series[a]
    return None

def coerce_bool_snap(v):
    if pd.isna(v): return None
    s = str(v).strip().lower()
    if s in ("y","yes","true","1","snap","accepts snap","ebt","accepts_ebt"): return True
    if s in ("n","no","false","0"): return False
    return None

def stable_id(row):
    # Why: some files won’t have FMID; we need a stable key for the MVP.
    base = "|".join(str(row.get(k,"") or "").strip().lower() for k in ("name","street","city","state","zip"))
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

def first_nonempty(*vals):
    for v in vals:
        if isinstance(v,str) and v.strip(): return v.strip()
    return None

def load_excel(path):
    # Why: dtype=str keeps leading zeros (ZIP), and we re-type lat/lon later.
    df = pd.read_excel(path, dtype=str, engine="openpyxl")
    df.columns = [norm(c) for c in df.columns]
    return df

def build_hours_raw(row, cols):
    parts = []
    for c in cols:
        v = row.get(c)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    return " | ".join(parts) if parts else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="", help="path to AMS Excel (.xlsx); default: latest in data/usda/raw/")
    ap.add_argument("--out-dir", default=os.path.expanduser("~/freshlocalharvest/data/usda/processed"))
    ap.add_argument("--db", default=os.path.expanduser("~/freshlocalharvest/db/markets.db"))
    args = ap.parse_args()

    raw_dir = os.path.expanduser("~/freshlocalharvest/data/usda/raw")
    if not args.inp:
        # pick latest farmersmarket*.xlsx
        xs = [os.path.join(raw_dir,f) for f in os.listdir(raw_dir) if f.lower().startswith("farmersmarket") and f.lower().endswith(".xlsx")]
        if not xs:
            print("No farmersmarket*.xlsx found in data/usda/raw/", file=sys.stderr); sys.exit(2)
        inp = max(xs, key=os.path.getmtime)
    else:
        inp = os.path.expanduser(args.inp)
    if not os.path.exists(inp):
        print(f"Input not found: {inp}", file=sys.stderr); sys.exit(2)

    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(os.path.dirname(args.db), exist_ok=True)

    df = load_excel(inp)

    # fast-access dict view per row
    out = []
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    src_file = os.path.basename(inp)
    src_updated = datetime.utcfromtimestamp(os.path.getmtime(inp)).isoformat(timespec="seconds") + "Z"

    for _, r in df.iterrows():
        row = r.to_dict()

        # alias resolution
        get = lambda key: pick(row, [a for a in CANDIDATES.get(key, [])])

        name   = get("name")
        street = get("street")
        city   = get("city")
        state  = (get("state") or "").upper()
        zipc   = (get("zip") or "")
        website= get("website")
        phone  = get("phone")

        # hours/season aggregation (keep raw)
        hours_raw = first_nonempty(
            get("hours_raw"),
            build_hours_raw(row, [a for a in CANDIDATES["hours_raw"] if a in row]),
            # some files include multiple season/time columns: collect a few common alternates
            build_hours_raw(row, [c for c in row.keys() if "time" in c or "schedule" in c])
        )
        season_start = get("season_start")
        season_end   = get("season_end")

        # lat/lon handling
        lat = get("lat"); lon = get("lon")
        try:
            lat = float(str(lat).strip()) if lat not in (None,"","nan") else None
        except: lat = None
        try:
            lon = float(str(lon).strip()) if lon not in (None,"","nan") else None
        except: lon = None

        accepts_snap = coerce_bool_snap(get("accepts_snap"))

        market_id = get("market_id")
        if not market_id or str(market_id).strip()=="":
            market_id = stable_id({"name":name,"street":street,"city":city,"state":state,"zip":zipc})

        # zip as string (keep leading zeros)
        zipc = str(zipc).zfill(5) if zipc and zipc.isdigit() and len(zipc) <= 5 else (zipc or None)

        out.append({
            "market_id": market_id,
            "name": name, "street": street, "city": city, "state": state, "zip": zipc,
            "lat": lat, "lon": lon,
            "website": website, "phone": phone,
            "accepts_snap": accepts_snap,
            "hours_raw": hours_raw, "season_start": season_start, "season_end": season_end,
            "source": "usda_ams_farmersmarket",
            "source_file": src_file,
            "source_updated_at": src_updated,
            "ingested_at": now
        })

    out_df = pd.DataFrame(out, columns=KEEP_COLS)
    # drop obvious empties
    out_df = out_df.dropna(subset=["name"]).reset_index(drop=True)

    # outputs
    stamp = datetime.utcnow().strftime("%Y%m%d")
    csv_path = os.path.join(args.out_dir, f"ams_farmersmarket_{stamp}.csv")
    pq_path  = os.path.join(args.out_dir, f"ams_farmersmarket_{stamp}.parquet")

    out_df.to_csv(csv_path, index=False)
    try:
        out_df.to_parquet(pq_path, index=False)  # why: smaller + faster loads
    except Exception as e:
        print(f"Parquet skipped ({e})", file=sys.stderr)

    # SQLite (why: the prototype can query this directly)
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS markets_usda")
    cols_sql = ", ".join([
        "market_id TEXT PRIMARY KEY",
        "name TEXT","street TEXT","city TEXT","state TEXT","zip TEXT",
        "lat REAL","lon REAL","website TEXT","phone TEXT",
        "accepts_snap BOOLEAN","hours_raw TEXT","season_start TEXT","season_end TEXT",
        "source TEXT","source_file TEXT","source_updated_at TEXT","ingested_at TEXT"
    ])
    cur.execute(f"CREATE TABLE markets_usda ({cols_sql})")
    # indexes (why: cheap filters)
    cur.execute("CREATE INDEX idx_markets_usda_state ON markets_usda(state)")
    cur.execute("CREATE INDEX idx_markets_usda_city  ON markets_usda(city)")
    cur.execute("CREATE INDEX idx_markets_usda_geo   ON markets_usda(lat,lon)")
    # bulk insert
    out_df.to_sql("markets_usda", conn, if_exists="append", index=False)
    conn.commit(); conn.close()

    print("rows=", len(out_df))
    print("csv=", csv_path)
    print("parquet=", pq_path)
    print("sqlite=", args.db)
    return 0

if __name__ == "__main__":
    sys.exit(main())
