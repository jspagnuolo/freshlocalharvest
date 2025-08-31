from __future__ import annotations
#!/usr/bin/env python3
"""
Fresh Local Harvest — FastAPI proxy for USDA Local Food Portal

- Uses documented endpoint: https://www.usdalocalfoodportal.com/api/{directory}/
- Sends API key as ?apikey=... (query param), with browser-like headers
- /proxy/usda  -> raw passthrough (debugging)
- /markets     -> normalized for Leaflet (name/lat/lon/etc.)
"""

import os
import time
import typing as t

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ----------------------------------------------------------------------------- #
# Config
# ----------------------------------------------------------------------------- #

USDA_API_BASE = "https://www.usdalocalfoodportal.com"
USDA_API_PATH = "/api/{directory}/"
USDA_API_KEY = os.getenv("USDA_API_KEY", "").strip()
HTTP_TIMEOUT = float(os.getenv("USDA_HTTP_TIMEOUT", "20"))
CACHE_TTL = float(os.getenv("USDA_CACHE_TTL", "60"))  # seconds

ALLOWED_ORIGINS = [
    "http://127.0.0.1:1313", "http://localhost:1313",
    "http://127.0.0.1:1314", "http://localhost:1314",
    "http://127.0.0.1:8000", "http://localhost:8000",
]

if not USDA_API_KEY:
    print("[WARN] USDA_API_KEY is not set. Set it to avoid 401/403 errors.")

# ----------------------------------------------------------------------------- #
# App
# ----------------------------------------------------------------------------- #

app = FastAPI(title="Fresh Local Harvest API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------- #
# Tiny in-memory cache
# ----------------------------------------------------------------------------- #

class CacheItem(t.TypedDict):
    t: float
    data: t.Any

_CACHE: dict[str, CacheItem] = {}

def _cache_key(path: str, params: dict[str, t.Any]) -> str:
    items = "&".join(f"{k}={params[k]}" for k in sorted(params))
    return f"{path}?{items}"

def _cache_get(path: str, params: dict[str, t.Any]) -> t.Any | None:
    key = _cache_key(path, params)
    item = _CACHE.get(key)
    if item and (time.time() - item["t"] <= CACHE_TTL):
        return item["data"]
    return None

def _cache_put(path: str, params: dict[str, t.Any], data: t.Any) -> None:
    key = _cache_key(path, params)
    _CACHE[key] = {"t": time.time(), "data": data}

# ----------------------------------------------------------------------------- #
# USDA helper
# ----------------------------------------------------------------------------- #

async def usda_get(session: httpx.AsyncClient, directory: str, params: dict[str, t.Any]) -> t.Any:
    """Call USDA documented endpoint /api/{directory}/ with ?apikey= param."""
    url = f"{USDA_API_BASE}{USDA_API_PATH.format(directory=directory.strip('/'))}"

    # Browser-ish headers (closer to your working curl)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, */*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.usdalocalfoodportal.com/",
        "Origin": "https://www.usdalocalfoodportal.com",
        "Connection": "keep-alive",
    }

    q = dict(params or {})
    if USDA_API_KEY:
        q["apikey"] = USDA_API_KEY

    # Use HTTP/2 (some CDNs gate behavior behind h2)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, http2=True, headers=headers) as client:
        r = await client.get(url, params=q)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data


# ----------------------------------------------------------------------------- #
# Routes
# ----------------------------------------------------------------------------- #

@app.get("/health")
def health():
    return {
        "ok": True,
        "usda_base": USDA_API_BASE,
        "path": USDA_API_PATH,
        "has_key": bool(USDA_API_KEY),
    }

@app.get("/proxy/usda")
async def proxy_usda(
    directory: str = "farmersmarket",
    x: float | None = None,
    y: float | None = None,
    radius: float = 30,
    state: str | None = None,
    city: str | None = None,
    zip: str | None = None,
    c: int = 0,
):
    """Raw passthrough to USDA (for debugging)."""
    params: dict[str, t.Any] = {"radius": radius, "c": c}
    if x is not None and y is not None:
        params.update({"x": x, "y": y})
    if state:
        params["state"] = state
    if city:
        params["city"] = city
    if zip:
        params["zip"] = zip

    cached = _cache_get(f"/proxy/{directory}", params)
    if cached is not None:
        return JSONResponse(content=cached)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as session:
        data = await usda_get(session, directory=directory, params=params)

    _cache_put(f"/proxy/{directory}", params, data)
    return JSONResponse(content=data)

@app.get("/markets")
async def markets(
    radius: float = 30,
    directory: str = "farmersmarket",
    x: float | None = None,
    y: float | None = None,
    state: str | None = None,
    city: str | None = None,
    zip: str | None = None,
    c: int = 0,
):
    """Normalized results for Leaflet (name/lat/lon + basic details)."""
    params: dict[str, t.Any] = {"radius": radius, "c": c}
    if x is not None and y is not None:
        params.update({"x": x, "y": y})
    if state:
        params["state"] = state
    if city:
        params["city"] = city
    if zip:
        params["zip"] = zip

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as session:
        raw = await usda_get(session, directory=directory, params=params)

    items: list[dict[str, t.Any]] = []
    arr = raw if isinstance(raw, list) else (raw or [])
    for m in arr:
        if not isinstance(m, dict):
            continue
        name = m.get("listing_name") or m.get("name") or "Market"
        lat  = m.get("location_latitude") or m.get("lat") or m.get("location_y")
        lon  = m.get("location_longitude") or m.get("lon") or m.get("location_x")
        try:
            lat = float(lat); lon = float(lon)
        except Exception:
            continue
        items.append({
            "name": name,
            "lat": lat, "lon": lon,
            "city": m.get("location_city"),
            "state": m.get("location_state"),
            "zip": m.get("location_zipcode"),
            "website": m.get("media_website"),
            "phone": m.get("contact_phone"),
        })
    return {"items": items}

# ----------------------------------------------------------------------------- #
# Entrypoint
# ----------------------------------------------------------------------------- #

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="127.0.0.1", port=8001, reload=True)
