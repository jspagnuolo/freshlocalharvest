#!/usr/bin/env python3
# Phase-1 API: read-only over SQLite.
# Why changes: add /markets/bbox to fetch by map bounds (less guessy than center+radius).
import math, os, sqlite3
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

DB_PATH = os.path.expanduser("~/freshlocalharvest/db/markets.db")
WEB_DIR = os.path.expanduser("~/freshlocalharvest/scripts/phase1/web")

app = FastAPI(title="FreshLocalHarvest Phase 1 API", version="0.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(WEB_DIR, exist_ok=True)
app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

def get_conn():
    # Why: simple per-request connection; SQLite is fine for read-mostly.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Why: correct ranking after bbox prefilter (used by /markets).
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

def bbox_from_point(lat: float, lon: float, radius_m: float):
    # Why: cheap SQL prefilter for /markets (center+radius).
    dlat = radius_m / 111_000
    dlon = radius_m / (111_000 * max(math.cos(math.radians(lat)), 1e-6))
    return (lat - dlat, lat + dlat, lon - dlon, lon + dlon)

@app.get("/health")
def health():
    if not os.path.exists(DB_PATH):
        raise HTTPException(503, "db not found")
    return {"ok": True}

def _filters(state: Optional[str], accepts_snap: Optional[bool], q: Optional[str]):
    # Why: reuse same predicate assembly in both endpoints.
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
    return where, params

@app.get("/markets")
def markets(
    lat: Optional[float] = Query(None, description="center lat"),
    lon: Optional[float] = Query(None, description="center lon"),
    radius_miles: Optional[float] = Query(25.0, ge=0.1, le=200.0, description="search radius (miles)"),
    state: Optional[str] = Query(None, min_length=2, max_length=2),
    accepts_snap: Optional[bool] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    # Why: keep this for compatibility; prefetch more before exact distance rerank.
    where, params = _filters(state, accepts_snap, q)
    bbox_sql = ""; bbox_params = []
    prefetch = min(max(limit * 10, 500), 3000)

    if lat is not None and lon is not None:
        radius_m = radius_miles * 1609.344
        lat_min, lat_max, lon_min, lon_max = bbox_from_point(lat, lon, radius_m)
        bbox_sql = " AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?"
        bbox_params = [lat_min, lat_max, lon_min, lon_max]

    sql = f"""
      SELECT market_id,name,street,city,state,zip,lat,lon,website,phone,
             accepts_snap,hours_raw,season_start,season_end,source,source_updated_at
      FROM markets_usda
      WHERE {' AND '.join(where)} {bbox_sql}
      LIMIT ? OFFSET ?
    """
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, (*params, *bbox_params, prefetch, offset)).fetchall()]

    if lat is not None and lon is not None:
        for r in rows:
            try:
                r["distance_m"] = haversine_m(lat, lon, float(r["lat"]), float(r["lon"]))
            except Exception:
                r["distance_m"] = None
        rows.sort(key=lambda r: (r["distance_m"] is None, r.get("distance_m", 1e18)))
        rows = rows[:limit]

    return {"count": len(rows), "items": rows}

@app.get("/markets/bbox")
def markets_bbox(
    lat_min: float = Query(..., description="south latitude"),
    lat_max: float = Query(..., description="north latitude"),
    lon_min: float = Query(..., description="west longitude"),
    lon_max: float = Query(..., description="east longitude"),
    state: Optional[str] = Query(None, min_length=2, max_length=2),
    accepts_snap: Optional[bool] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    # Why: fetch exactly what's visible. Caller (map) provides current bounds.
    if lat_min > lat_max or lon_min > lon_max:
        raise HTTPException(400, "invalid bbox")
    where, params = _filters(state, accepts_snap, q)
    where.append("lat BETWEEN ? AND ?")
    where.append("lon BETWEEN ? AND ?")
    params.extend([lat_min, lat_max, lon_min, lon_max])

    sql = f"""
      SELECT market_id,name,street,city,state,zip,lat,lon,website,phone,
             accepts_snap,hours_raw,season_start,season_end,source,source_updated_at
      FROM markets_usda
      WHERE {' AND '.join(where)}
      LIMIT ? OFFSET ?
    """
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, (*params, limit, offset)).fetchall()]
    return {"count": len(rows), "items": rows}

@app.get("/markets/{market_id}")
def market_by_id(market_id: str):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT market_id,name,street,city,state,zip,lat,lon,website,phone,
                      accepts_snap,hours_raw,season_start,season_end,source,source_updated_at
               FROM markets_usda WHERE market_id = ?""",
            (market_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "market not found")
        return dict(row)
