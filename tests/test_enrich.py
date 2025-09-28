import pandas as pd
import pytest

from ingest.scripts.enrich import enrich_markets, generate_zip_centroids, generate_city_centroids


def make_df(address, name="Test Market", org="Org", desc="Desc", lat=40.0, lon=-75.0):
    return pd.DataFrame({
        "listing_name": [name],
        "organization": [org],
        "location_address": [address],
        "location_desc": [desc],
        "listing_desc": [""],
        "latitude": [lat],
        "longitude": [lon],
    })


def test_enrich_parses_city_state_zip():
    df = make_df("123 Main St, Columbus, Ohio 43215")
    out = enrich_markets(df)
    row = out.iloc[0]
    assert row.street == "123 Main St"
    assert row.city == "Columbus"
    assert row.state == "OH"
    assert row.zip == "43215"
    assert row.full_address == "123 Main St, Columbus, OH, 43215"


def test_enrich_handles_minimal_address():
    df = make_df("Somewhere in Alaska")
    out = enrich_markets(df)
    row = out.iloc[0]
    assert row.street == "Somewhere in Alaska"
    assert pd.isna(row.city)
    assert (pd.isna(row.state) or row.state == "AK")
    assert row.zip == ""
    assert row.full_address in {"Somewhere in Alaska", "Somewhere in Alaska, AK"}


def test_search_tokens_include_core_fields():
    df = make_df("10 Market Rd, Miami, FL 33101", name="Little Havana Market")
    out = enrich_markets(df)
    hay = out.iloc[0].search_haystack
    assert "miami" in hay
    assert "fl" in hay
    assert "33101" in hay
    assert "little havana market" in hay


def test_enrich_adds_zip_lat_lon():
    df = make_df("6601 Biscayne Blvd, Miami, FL 33138", lat=25.836, lon=-80.183)
    out = enrich_markets(df)
    row = out.iloc[0]
    assert row.zip_lat is not None
    assert row.zip_lon is not None
    # Rough check near Miami
    assert pytest.approx(row.zip_lat, abs=0.5) == 25.8
    assert pytest.approx(row.zip_lon, abs=0.5) == -80.18


def test_generate_zip_centroids_contains_known_zip():
    df = pd.concat([
        make_df("10 Peachtree St NE, Atlanta, GA 30303", lat=33.753, lon=-84.390),
        make_df("20 Peachtree St NE, Atlanta, GA 30303", lat=33.754, lon=-84.389),
        make_df("200 Biscayne Blvd, Miami, FL 33131", lat=25.770, lon=-80.189),
    ], ignore_index=True)
    enriched = enrich_markets(df)
    centroids = generate_zip_centroids(enriched)
    assert '30303' in centroids
    lat, lon = centroids['30303']
    assert pytest.approx(lat, abs=0.1) == 33.7535
    assert pytest.approx(lon, abs=0.1) == -84.3895
    # Prefix key available as fallback
    assert '303' in centroids


def test_generate_city_centroids_handles_city_state_and_fallback():
    df = pd.concat([
        make_df("10 Peachtree St NE, Atlanta, GA 30303", name="A1", lat=33.753, lon=-84.390),
        make_df("20 Peachtree St NE, Atlanta, GA 30303", name="A2", lat=33.754, lon=-84.389),
        make_df("123 Main St, Springfield, IL 62701", name="S1", lat=39.801, lon=-89.643),
        make_df("456 State St, Springfield, MO 65806", name="S2", lat=37.208, lon=-93.292),
    ], ignore_index=True)
    enriched = enrich_markets(df)
    centroids = generate_city_centroids(enriched)

    atl_key = 'atlanta|GA'
    assert atl_key in centroids
    atl_lat, atl_lon = centroids[atl_key]
    assert pytest.approx(atl_lat, abs=0.1) == 33.7535
    assert pytest.approx(atl_lon, abs=0.1) == -84.3895

    # Fallback without explicit state should exist
    assert 'atlanta' in centroids

    # Multiple Springfield entries keep individual state centroids separate
    assert centroids['springfield|IL'][0] != centroids['springfield|MO'][0]
    assert 'springfield' not in centroids
