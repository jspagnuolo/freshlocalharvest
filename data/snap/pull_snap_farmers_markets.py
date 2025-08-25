# Why Python: avoids ArcGIS GUI limits; paginates via objectIds and writes a clean CSV.
# Why flexible fields: FNS has used RETAILER_TYPE / STORE_TYPE names in different layers.

import csv, json, sys, time, urllib.parse, urllib.request, datetime

BASE = "https://services1.arcgis.com/RLQu0rK7h4kbsBq5/arcgis/rest/services/snap_retailer_location_data/FeatureServer/0"
OUT = f"snap_farmers_markets_{datetime.date.today().isoformat()}.csv"

def get(url, params=None, retries=5, backoff=2):
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return r.read()
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

def get_json(url, params=None):
    data = get(url, params)
    return json.loads(data.decode("utf-8"))

# discover fields to pick the store-type column
info = get_json(BASE, {"f":"json"})
field_names = {f["name"] for f in info.get("fields", [])}
type_field = "RETAILER_TYPE" if "RETAILER_TYPE" in field_names else ("STORE_TYPE" if "STORE_TYPE" in field_names else None)
if not type_field:
    sys.exit("Could not find store-type field (expected RETAILER_TYPE or STORE_TYPE).")

# get all object IDs for Farmers & Markets
where = f"{type_field}='Farmers and Markets'"
ids_resp = get_json(BASE + "/query", {
    "f":"json",
    "where": where,
    "returnIdsOnly":"true"
})
oids = ids_resp.get("objectIds") or []
if not oids:
    sys.exit("No object IDs returned; store-type value may have changed.")

# fetch features in chunks under maxRecordCount
oids.sort()
chunk = 1000
features = []
for i in range(0, len(oids), chunk):
    subset = ",".join(map(str, oids[i:i+chunk]))
    data = get_json(BASE + "/query", {
        "f":"json",
        "objectIds": subset,
        "outFields": "*",
        "returnGeometry": "false"
    })
    features.extend(data.get("features", []))
    time.sleep(0.5)  # be polite

# build columns from union of attributes (stable header if present)
cols = ["RETAILER_ID","RETAILER_NAME","ADDRESS","ADDITIONAL_ADDRESS","CITY","STATE","ZIP_CODE","ZIP4","COUNTY",
        type_field,"LATITUDE","LONGITUDE","INCENTIVE_PROGRAM","GRANTEE_NAME"]
all_keys = set().union(*(f.get("attributes", {}).keys() for f in features)) if features else set()
cols = [c for c in cols if c in all_keys] + sorted(k for k in all_keys if k not in cols)

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for feat in features:
        w.writerow({k: feat.get("attributes", {}).get(k) for k in cols})

print(f"Wrote {len(features)} rows -> {OUT}")
