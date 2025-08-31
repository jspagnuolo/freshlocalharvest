#!/usr/bin/env python3
import re, json, pathlib
import httpx

API_BASE = "https://search.ams.usda.gov/farmersmarkets/v1/data.svc"

# State centers to sweep the US coarsely
states = {
  "AL": (32.806671,-86.791130), "AK": (61.370716,-152.404419), "AZ": (33.729759,-111.431221),
  "AR": (34.969704,-92.373123), "CA": (36.116203,-119.681564), "CO": (39.059811,-105.311104),
  "CT": (41.597782,-72.755371), "DE": (39.318523,-75.507141), "FL": (27.766279,-81.686783),
  "GA": (33.040619,-83.643074), "HI": (21.094318,-157.498337), "ID": (44.240459,-114.478828),
  "IL": (40.349457,-88.986137), "IN": (39.849426,-86.258278), "IA": (42.011539,-93.210526),
  "KS": (38.526600,-96.726486), "KY": (37.668140,-84.670067), "LA": (31.169546,-91.867805),
  "ME": (44.693947,-69.381927), "MD": (39.063946,-76.802101), "MA": (42.230171,-71.530106),
  "MI": (43.326618,-84.536095), "MN": (45.694454,-93.900192), "MS": (32.741646,-89.678696),
  "MO": (38.456085,-92.288368), "MT": (46.921925,-110.454353), "NE": (41.125370,-98.268082),
  "NV": (38.313515,-117.055374), "NH": (43.452492,-71.563896), "NJ": (40.298904,-74.521011),
  "NM": (34.840515,-106.248482), "NY": (42.165726,-74.948051), "NC": (35.630066,-79.806419),
  "ND": (47.528912,-99.784012), "OH": (40.388783,-82.764915), "OK": (35.565342,-96.928917),
  "OR": (44.572021,-122.070938), "PA": (40.590752,-77.209755), "RI": (41.680893,-71.511780),
  "SC": (33.856892,-80.945007), "SD": (44.299782,-99.438828), "TN": (35.747845,-86.692345),
  "TX": (31.054487,-97.563461), "UT": (40.150032,-111.862434), "VT": (44.045876,-72.710686),
  "VA": (37.769337,-78.169968), "WA": (47.400902,-121.490494), "WV": (38.491226,-80.954453),
  "WI": (44.268543,-89.616508), "WY": (42.755966,-107.302490), "DC": (38.9072, -77.0369),
}

BROWSER_HEADERS = {
    # Emulate a modern browser; include Origin to satisfy some edge checks
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://search.ams.usda.gov/",
    "Origin": "https://search.ams.usda.gov",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}

def strip_distance(name: str) -> str:
    # USDA locSearch marketname may start with "2.4 Market Name"
    return re.sub(r"^\s*\d+(?:\.\d+)?\s+", "", name or "").strip()

def parse_latlon_from_google_link(link: str):
    # Example: http://maps.google.com/?q=39.1234%2C-77.5678
    if not link:
        return None, None
    m = re.search(r"[?&]q=([\-0-9\.]+)%2C([\-0-9\.]+)", link)
    if not m:
        m = re.search(r"[?&]q=([\-0-9\.]+),([\-0-9\.]+)", link)
    try:
        return float(m.group(1)), float(m.group(2)) if m else (None, None)
    except Exception:
        return None, None

def split_city_state_zip(address: str):
    # Very loose parser: "... City, ST 12345"
    if not address or "," not in address:
        return None, None, None
    parts = [p.strip() for p in address.split(",")]
    last = parts[-1] if parts else ""
    m = re.search(r"([A-Z]{2})\s+(\d{5})", last)
    state = m.group(1) if m else None
    zipc = m.group(2) if m else None
    city = parts[-2] if len(parts) >= 2 else None
    return city, state, zipc

def fetch_json(client, path, params=None):
    url = f"{API_BASE}/{path}"
    r = client.get(url, params=params or {}, headers=BROWSER_HEADERS)
    r.raise_for_status()
    return r.json()

def main():
    seen = set()
    items = []

    with httpx.Client(
        timeout=30,
        verify=False,           # USDA TLS chain quirk
        follow_redirects=True,  # handle 303 -> HTTPS
        http2=False             # stick to HTTP/1.1
    ) as client:
        for abbr, (lat, lon) in states.items():
            # Nearby search around state "center"
            payload = fetch_json(client, "locSearch", {"lat": lat, "lng": lon})
            results = payload.get("results") or payload.get("items") or []
            for row in results:
                market_id = str(row.get("id") or "").strip()
                market_name = strip_distance(row.get("marketname") or row.get("name") or "Market")
                if not market_id:
                    continue

                detail = fetch_json(client, "mktDetail", {"id": market_id})
                md = detail.get("marketdetails") or {}
                g_link = md.get("GoogleLink") or ""
                lat2, lon2 = parse_latlon_from_google_link(g_link)
                address = md.get("Address") or ""
                city, state, zipc = split_city_state_zip(address)

                key = (market_name, lat2, lon2)
                if lat2 is None or lon2 is None or key in seen:
                    continue
                seen.add(key)

                items.append({
                    "name": market_name,
                    "lat": lat2, "lon": lon2,
                    "city": city, "state": state, "zip": zipc,
                    "website": md.get("Website") or md.get("Facebook") or None,
                    "phone": md.get("Phone") or None,
                    "source_id": market_id,
                })

    print("deduped items:", len(items))
    out = pathlib.Path("site/static/data/markets.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items), encoding="utf-8")
    print("wrote", len(items), "to", str(out))

if __name__ == "__main__":
    main()
