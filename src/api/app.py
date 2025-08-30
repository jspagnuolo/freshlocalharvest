#!/usr/bin/env python3
# FastAPI app for Fresh Local Harvest (Phase 1)
# Comments explain "why" tradeoffs, not line-by-line "what".

import hashlib
import math
import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles


# Why: allow override in tests/CI, but default to your local dev DB
DB_PATH = os.getenv("FLH_DB", os.path.expanduser("~/freshlocalharvest/db/markets.db"))

# Why: resolve static web directory relative to this file so refactors don't break paths
WEB_DIR = (Path(__file__).resolve().parent / "web")
WEB_DIR.mkdir(parents=True, exist_ok=True)  # safe if exists

app = FastAPI(title="FreshLocalHarvest API", version="0.3.1")

# Why: local map page and future site may be served from separate origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the map UI at /web/ (expects index.html in WEB_DIR)
app.mount("/web", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


# ---- helpers ----

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Why: accurate enough and dependency-free for small radii
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def bbox_from_point(lat: float, lon: float, radius_m: float):
    # Why: cheap coarse filter before precise distance calc
    dlat = radius_m / 111_000.0
    dlon = radius_m / (111_000.0 * max(math.cos(math.radians(lat)), 1e-6))
    return (lat - dlat, lat + dlat, lon - dlon, lon + dlon)

def table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    # Why: schema may evolve (e.g., ebt_active). This keeps selects resilient.
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r["name"] for r in rows]

def make_market_id(row: Dict[str, Any]) -> str:
    """
    Why: tests and clients need a stable identifier even if the DB lacks one.
    Use a deterministic SHA1 of key fields (name/city/state/zip/lat/lon).
    """
    parts = [
        str(row.get("name", "")).strip().lower(),
        str(row.get("city", "")).strip().lower(),
        str(row.get("state", "")).strip().upper(),
        str(row.get("zip", "")).strip(),
        str(row.get("lat", "")),
        str(row.get("lon", "")),
    ]
    h = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"usda_{h}"

def ensure_market_id(d: Dict[str, Any]) -> Dict[str, Any]:
    if "market_id" not in d or not d["market_id"]:
        d["market_id"] = make_market_id(d)
    return d


# ---- routes ----

@app.get("/")
def root_redirect():
    # Why: make the base URL useful in the browser
    return RedirectResponse(url="/web/")

@app.get("/health")
def health():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=503, detail="db not found")
    # quick sanity: table exists?
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1 FROM markets_usda LIMIT 1").fetchone()
    except sqlite3.DatabaseError as e:
        raise HTTPException(status_code=503, detail=f"db error: {e}")
    return {"ok": True}


@app.get("/markets")
def markets(
    q: Optional[str] = Query(None, description="Case-insensitive search on name/city"),
    state: Optional[str] = Query(None, min_length=2, max_length=2),
    accepts_snap: Optional[bool] = Query(None, description="Filter by AMS-claimed SNAP"),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_miles: float = Query(25.0, ge=0.0),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    radius_m = float(radius_miles) * 1609.34

    where = ["name IS NOT NULL"]
    params: List[Any] = []

    if state:
        where.append("state = ?")
        params.append(state.upper())

    if accepts_snap is True:
        where.append("accepts_snap = 1")
    elif accepts_snap is False:
        # Why: explicit false filter; avoids NULLs being counted as false
        where.append("accepts_snap = 0")

    if q:
        like = f"%{q.lower()}%"
        where.append("(LOWER(name) LIKE ? OR LOWER(city) LIKE ?)")
        params.extend([like, like])

    # coarse bbox if a point is provided
    bbox_clause = ""
    bbox_params: List[Any] = []
    if lat is not None and lon is not None and radius_m > 0:
        lat_min, lat_max, lon_min, lon_max = bbox_from_point(lat, lon, radius_m)
        bbox_clause = " AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?"
        bbox_params = [lat_min, lat_max, lon_min, lon_max]

    sql_where = " WHERE " + " AND ".join(where) if where else ""
    base_select = (
        "SELECT name, city, state, zip, lat, lon, website, phone, accepts_snap "
        "FROM markets_usda"
    )

    with get_conn() as conn:
        cols = set(table_columns(conn, "markets_usda"))
        # include optional columns if present
        opt_cols = []
        for c in ("market_id", "ebt_active", "snap_match_count", "snap_min_distance_m", "ebt_last_seen"):
            if c in cols:
                opt_cols.append(c)
        if opt_cols:
            base_select = (
                "SELECT name, city, state, zip, lat, lon, website, phone, accepts_snap, "
                + ", ".join(opt_cols)
                + " FROM markets_usda"
            )

        # Why: for distance-sorted responses, fetch a generous window to sort in Python
        fetch_limit = limit + offset
        if lat is not None and lon is not None and radius_m > 0:
            fetch_limit = min(max(fetch_limit * 4, 200), 2000)  # widen window under bbox

        sql = f"{base_select}{sql_where}{bbox_clause} LIMIT ? OFFSET ?"
        rows = conn.execute(sql, (*params, *bbox_params, fetch_limit, 0)).fetchall()

    items: List[Dict[str, Any]] = []
    if lat is not None and lon is not None and radius_m > 0:
        # refine by true haversine distance and sort by distance
        for r in rows:
            if r["lat"] is None or r["lon"] is None:
                continue
            dist = haversine_m(lat, lon, float(r["lat"]), float(r["lon"]))
            if dist <= radius_m:
                d = ensure_market_id(dict(r))
                d["distance_m"] = round(float(dist), 1)
                items.append(d)
        items.sort(key=lambda x: x["distance_m"])
        total = len(items)
        items = items[offset:offset + limit]
    else:
        # no distance sorting; just slice
        total = len(rows)
        items = [ensure_market_id(dict(r)) for r in rows][offset:offset + limit]

    return {"count": total, "items": items}


@app.get("/markets/bbox")
def markets_bbox(
    lat_min: float = Query(...),
    lat_max: float = Query(...),
    lon_min: float = Query(...),
    lon_max: float = Query(...),
    q: Optional[str] = Query(None),
    state: Optional[str] = Query(None, min_length=2, max_length=2),
    accepts_snap: Optional[bool] = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    # Why: tile/viewport fetches from the map; cheaper than per-point haversine
    where = ["name IS NOT NULL", "lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?"]
    params: List[Any] = [lat_min, lat_max, lon_min, lon_max]

    if state:
        where.append("state = ?")
        params.append(state.upper())

    if accepts_snap is True:
        where.append("accepts_snap = 1")
    elif accepts_snap is False:
        where.append("accepts_snap = 0")

    if q:
        like = f"%{q.lower()}%"
        where.append("(LOWER(name) LIKE ? OR LOWER(city) LIKE ?)")
        params.extend([like, like])

    sql_where = " WHERE " + " AND ".join(where)

    base_select = (
        "SELECT name, city, state, zip, lat, lon, website, phone, accepts_snap "
        "FROM markets_usda"
    )

    with get_conn() as conn:
        cols = set(table_columns(conn, "markets_usda"))
        opt_cols = []
        for c in ("market_id", "ebt_active", "snap_match_count", "snap_min_distance_m", "ebt_last_seen"):
            if c in cols:
                opt_cols.append(c)
        if opt_cols:
            base_select = (
                "SELECT name, city, state, zip, lat, lon, website, phone, accepts_snap, "
                + ", ".join(opt_cols)
                + " FROM markets_usda"
            )

        sql = f"{base_select}{sql_where} LIMIT ? OFFSET ?"
        rows = conn.execute(sql, (*params, limit, offset)).fetchall()

    items = [ensure_market_id(dict(r)) for r in rows]
    return {"count": len(items), "items": items}
