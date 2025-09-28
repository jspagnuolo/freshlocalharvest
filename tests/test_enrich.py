import pandas as pd

from ingest.scripts.enrich import enrich_markets


def make_df(address, name="Test Market", org="Org", desc="Desc"):
    return pd.DataFrame({
        "listing_name": [name],
        "organization": [org],
        "location_address": [address],
        "location_desc": [desc],
        "listing_desc": [""],
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
    assert pd.isna(row.state)
    assert row.zip == ""
    assert row.full_address == "Somewhere in Alaska"


def test_search_tokens_include_core_fields():
    df = make_df("10 Market Rd, Miami, FL 33101", name="Little Havana Market")
    out = enrich_markets(df)
    hay = out.iloc[0].search_haystack
    assert "miami" in hay
    assert "fl" in hay
    assert "33101" in hay
    assert "little havana market" in hay
