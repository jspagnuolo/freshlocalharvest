#!/usr/bin/env python3
# Why: minimal read-only API over SQLite to power a map + filters; keep queries index-friendly.

import math, sqlite3, os
from typing import Optional, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = os.path.expanduser("~/freshlocalharvest/db/markets.db")

app = FastAPI(title="FreshLocalHarvest Phase 1 API", version="0.1")

# Why: allow local dev UIs (localhost, any port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

def get_conn():
    # Why: one connection per request scope is fine; SQLite is file-local and read-mostly here.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def haversine_m(lat1, lon1, lat2, lon2):
    # Why: exact distance for ranking after bounding-box prefilter.
    R=6371000.0
    p1,p2=math.radians(lat1),math.radians(lat2)
    dphi=p2-p1; dl=math.radians(lon2-lon1)
    a=math.sin(dphi/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def bbox_from_point(lat, lon, radius_m):
    # Why: cheap prefilter (lat≈111km/deg; lon scaled by cos(lat))
    dlat = radius_m / 111_000
    dlon = radius_m / (111_000 * max(math.cos(math.radians(lat)), 1e-6))
    return (lat-dlat, lat+dlat, lon-dlon, lon+dlon)

@app.get("/health")
def health():
    if not os.path.exists(DB_PATH): raise HTTPException(503, "db not found")
    return {"ok": True}

@app.get("/markets")
def markets(
    lat: Optional[float] = Query(None, description="center lat"),
    lon: Optional[float] = Query(None, description="center lon"),
    radius_miles: Optional[float] = Query(25.0, ge=0.1, le=200.0, description="search radius (miles)"),
    state: Optional[str] = Query(None, min_length=2, max_length=2, description="US state code"),
    accepts_snap: Optional[bool] = Query(None, description="True = must accept SNAP, False = must not, omit = any"),
    q: Optional[str] = Query(None, description="substring in name or city (case-insensitive)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    # Why: two paths—spatial search (lat/lon given) or simple filtered list (no lat/lon).
    where = ["name IS NOT NULL"]
    params = []

    if state:
        where.append("state = ?")
        params.append(state.upper())

    if accepts_snap is True:
        where.append("accepts_snap = 1")
    elif accepts_snap is False:
        where.append("(accepts_snap = 0)")

    if q:
        where.append("(LOWER(name) LIKE ? OR LOWER(city) LIKE ?)")
        like = f"%{q.lower()}%"
        params.extend([like, like])

    order_sql = "name COLLATE NOCASE ASC"
    bbox_sql = ""
    bbox_params: List[float] = []

    if lat is not None and lon is not None:
        radius_m = radius_miles * 1609.344
        lat_min, lat_max, lon_min, lon_max = bbox_from_point(lat, lon, radius_m)
        bbox_sql = " AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?"
        bbox_params = [lat_min, lat_max, lon_min, lon_max]
        order_sql = "lat ASC"  # placeholder; we’ll re-rank by distance in Python

    sql = f"""
        SELECT market_id, name, street, city, state, zip, lat, lon, website, phone,
               accepts_snap, hours_raw, season_start, season_end, source, source_updated_at
        FROM markets_usda
        WHERE {' AND '.join(where)} {bbox_sql}
        LIMIT ? OFFSET ?
    """
    with get_conn() as conn:
        cur = conn.execute(sql, (*params, *bbox_params, limit, offset))
        rows = [dict(r) for r in cur.fetchall()]

    if lat is not None and lon is not None:
        # Why: precise distance ranking only on the small bbox subset.
        for r in rows:
            rlat, rlon = r.get("lat"), r.get("lon")
            try:
                d = haversine_m(lat, lon, float(rlat), float(rlon)) if rlat is not None and rlon is not None else None
            except Exception:
                d = None
            r["distance_m"] = d
        rows.sort(key=lambda r: (r["distance_m"] is None, r.get("distance_m", 1e18)))
        # Trim to requested limit after rerank (keep consistent with LIMIT/OFFSET usage)
        rows = rows[:limit]

    return {"count": len(rows), "items": rows}

@app.get("/markets/{market_id}")
def market_by_id(market_id: str):
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT market_id, name, street, city, state, zip, lat, lon, website, phone,
                      accepts_snap, hours_raw, season_start, season_end, source, source_updated_at
               FROM markets_usda WHERE market_id = ?""",
            (market_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "market not found")
        return dict(row)
