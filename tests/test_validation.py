# File: tests/test_validation.py
import pandas as pd
from ingest.scripts.validate import basic_validate

def test_basic_validate():
    df = pd.DataFrame({
        "listing_id": ["1", "1", "2", None],
        "listing_name": ["A", "A", "B", "C"],
        "location_address": ["addr", "addr", "addr2", "addr3"],
        "longitude": [-81.0, -81.0, 999.0, -82.0],
        "latitude": [28.0, 28.0, 28.0, None],
    })
    valid, rejects = basic_validate(df)
    # Row 0 valid, row1 dup, row2 bad longitude, row3 missing lat
    assert len(valid) == 1
    assert len(rejects) == 3
