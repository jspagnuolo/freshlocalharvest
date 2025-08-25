# Why: exercise the API with a temporary SQLite DB; no network, no running server required.
import os, sqlite3, tempfile
import importlib

from fastapi.testclient import TestClient

def make_db(path):
    conn = sqlite3.connect(path)
    conn.executescript("""
    DROP TABLE IF EXISTS markets_usda;
    CREATE TABLE markets_usda (
      market_id TEXT PRIMARY KEY,
      name TEXT, street TEXT, city TEXT, state TEXT, zip TEXT,
      lat REAL, lon REAL, website TEXT, phone TEXT,
      accepts_snap BOOLEAN, hours_raw TEXT, season_start TEXT, season_end TEXT,
      source TEXT, source_file TEXT, source_updated_at TEXT, ingested_at TEXT
    );
    """)
    # Miami row (SNAP yes)
    conn.execute("""INSERT INTO markets_usda
      (market_id,name,city,state,zip,lat,lon,accepts_snap)
      VALUES (?,?,?,?,?,?,?,?)""",
      ("m1","Test Miami Market","Miami","FL","33130",25.7617,-80.1918,1))
    # Tampa-ish row (SNAP no)
    conn.execute("""INSERT INTO markets_usda
      (market_id,name,city,state,zip,lat,lon,accepts_snap)
      VALUES (?,?,?,?,?,?,?,?)""",
      ("t1","Test Tampa Market","Tampa","FL","33602",27.951,-82.457,0))
    conn.commit(); conn.close()

def app_with_db(tmpdb):
    # Import the API module and point it at tmpdb
    api = importlib.import_module("scripts.phase1.api")
    api.DB_PATH = tmpdb
    return api.app

def test_health(tmp_path):
    tmpdb = tmp_path / "db.sqlite"
    make_db(str(tmpdb))
    app = app_with_db(str(tmpdb))
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}

def test_text_search_state(tmp_path):
    tmpdb = tmp_path / "db.sqlite"
    make_db(str(tmpdb))
    client = TestClient(app_with_db(str(tmpdb)))
    r = client.get("/markets", params={"q":"miami","state":"FL","limit":5})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    names = [it["name"] for it in data["items"]]
    assert any("Miami" in n or "Test Miami Market" in n for n in names)

def test_spatial_radius(tmp_path):
    tmpdb = tmp_path / "db.sqlite"
    make_db(str(tmpdb))
    client = TestClient(app_with_db(str(tmpdb)))
    # Center near Miami, small radius: should include Miami, not Tampa
    r = client.get("/markets", params={"lat":25.7617,"lon":-80.1918,"radius_miles":5,"limit":50})
    assert r.status_code == 200
    ids = [it["market_id"] for it in r.json()["items"]]
    assert "m1" in ids
    assert "t1" not in ids

def test_snap_filter(tmp_path):
    tmpdb = tmp_path / "db.sqlite"
    make_db(str(tmpdb))
    client = TestClient(app_with_db(str(tmpdb)))
    r = client.get("/markets", params={"state":"FL","accepts_snap": "true", "limit":50})
    assert r.status_code == 200
    ids = [it["market_id"] for it in r.json()["items"]]
    assert "m1" in ids and "t1" not in ids
