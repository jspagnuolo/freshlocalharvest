#!/usr/bin/env python3
# Normalize AMS "listing_* / location_*" workbook into a skinny table.
# Why: this schema differs from classic FMID; we coerce types, parse addresses, and persist to CSV/Parquet/SQLite.

import os, re, sqlite3, hashlib
from datetime import datetime
import pandas as pd

INPUT   = os.environ.get("AMS_XLS", "data/usda/raw/farmersmarket_2025-824194152.xlsx")
OUT_DIR = "data/usda/processed"
DB      = "db/markets.db"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB), exist_ok=True)

df = pd.read_excel(INPUT, dtype=object, engine="openpyxl", keep_default_na=True)
df.columns = [c.strip().lower() for c in df.columns]

need = {"listing_id","listing_name","location_address","location_x","location_y"}
missing = need - set(df.columns)
if missing: raise SystemExit(f"Sheet missing required columns: {missing}")

def as_str(v):
    if v is None: return ""
    if isinstance(v, float) and pd.isna(v): return ""
    return str(v)

STATE_MAP = {k:v for k,v in {
'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA','colorado':'CO','connecticut':'CT','delaware':'DE',
'florida':'FL','georgia':'GA','hawaii':'HI','idaho':'ID','illinois':'IL','indiana':'IN','iowa':'IA','kansas':'KS','kentucky':'KY',
'louisiana':'LA','maine':'ME','maryland':'MD','massachusetts':'MA','michigan':'MI','minnesota':'MN','mississippi':'MS','missouri':'MO',
'montana':'MT','nebraska':'NE','nevada':'NV','new hampshire':'NH','new jersey':'NJ','new mexico':'NM','new york':'NY',
'north carolina':'NC','north dakota':'ND','ohio':'OH','oklahoma':'OK','oregon':'OR','pennsylvania':'PA','rhode island':'RI',
'south carolina':'SC','south dakota':'SD','tennessee':'TN','texas':'TX','utah':'UT','vermont':'VT','virginia':'VA','washington':'WA',
'west virginia':'WV','wisconsin':'WI','wyoming':'WY','district of columbia':'DC','washington, dc':'DC','dc':'DC'}.items()}
ZIP_RE = re.compile(r'(\d{5})(?:-\d{4})?$')

def parse_address(s):
    s = as_str(s).strip()
    if not s: return None, None, None, None
    parts = [p.strip() for p in s.split(",")]
    if len(parts) < 3:
        m = ZIP_RE.search(s); return s or None, None, None, (m.group(1) if m else None)
    street = ", ".join(parts[:-2]); city = parts[-2]; state_zip = parts[-1]
    toks = state_zip.split(); st=None; z=None
    if toks:
        m = ZIP_RE.match(toks[-1])
        if m: z=m.group(1); st_txt=" ".join(toks[:-1]).strip()
        else: st_txt=state_zip.strip()
        low = st_txt.lower()
        if len(st_txt)==2 and st_txt.isalpha(): st=st_txt.upper()
        elif low in STATE_MAP: st=STATE_MAP[low]
        elif low.replace(".","") in STATE_MAP: st=STATE_MAP[low.replace(".","")]
        else: st = st_txt.upper() if len(st_txt)==2 else None
    return street or None, (city or None), st, z

def to_float(v):
    s = as_str(v).strip()
    if not s: return None
    try: return float(s)
    except: return None

def to_bool_snap(row):
    fnap = as_str(row.get('fnap')).lower()
    if 'snap' in fnap: return True
    has_opt=False; truthy=False
    for k,v in row.items():
        if isinstance(k,str) and k.startswith('snap_option'):
            has_opt=True
            if as_str(v).strip()=='1': truthy=True
    if has_opt: return True if truthy else False
    return None

def stable_id(name, street, city, state, zipc):
    base = "|".join([as_str(name).lower().strip(), as_str(street).lower().strip(),
                     as_str(city).lower().strip(), as_str(state).upper().strip(), as_str(zipc).strip()])
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

rows=[]; src_file=os.path.basename(INPUT)
src_updated=datetime.utcfromtimestamp(os.path.getmtime(INPUT)).isoformat(timespec="seconds")+"Z"
ingested_at=datetime.utcnow().isoformat(timespec="seconds")+"Z"

for _, r in df.iterrows():
    name = as_str(r.get('listing_name')).strip()
    if not name: continue
    street, city, state, zipc = parse_address(r.get('location_address'))
    lat = to_float(r.get('location_y')); lon = to_float(r.get('location_x'))
    accepts_snap = to_bool_snap(r)
    market_id = as_str(r.get('listing_id')).strip() or stable_id(name, street, city, state, zipc)
    if zipc and zipc.isdigit() and len(zipc)<=5: zipc = zipc.zfill(5)
    rows.append({
        "market_id": market_id, "name": name, "street": street, "city": city, "state": state, "zip": zipc,
        "lat": lat, "lon": lon, "website": None, "phone": None,
        "accepts_snap": accepts_snap, "hours_raw": None, "season_start": None, "season_end": None,
        "source": "usda_ams_farmersmarket_v2", "source_file": src_file,
        "source_updated_at": src_updated, "ingested_at": ingested_at
    })

out = pd.DataFrame(rows, columns=[
    "market_id","name","street","city","state","zip","lat","lon","website","phone",
    "accepts_snap","hours_raw","season_start","season_end",
    "source","source_file","source_updated_at","ingested_at"
])

stamp = datetime.utcnow().strftime("%Y%m%d")
csv_path = f"{OUT_DIR}/ams_farmersmarket_{stamp}.csv"
pq_path  = f"{OUT_DIR}/ams_farmersmarket_{stamp}.parquet"
out.to_csv(csv_path, index=False)
try: out.to_parquet(pq_path, index=False)
except Exception as e: print("Parquet skipped:", e)

conn = sqlite3.connect(DB)
out.to_sql("markets_usda", conn, if_exists="replace", index=False)
conn.execute("CREATE INDEX IF NOT EXISTS idx_usda_state ON markets_usda(state)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_usda_city  ON markets_usda(city)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_usda_geo   ON markets_usda(lat,lon)")
conn.commit(); conn.close()

print("rows=", len(out))
print("csv=", csv_path)
print("parquet=", pq_path)
print("sqlite=", DB)
