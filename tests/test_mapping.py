# File: tests/test_mapping.py
import pandas as pd
from ingest.scripts.map_programs import map_program_flags
import tempfile, yaml, os

def test_map_programs_basic():
    df = pd.DataFrame({
        "FNAP_1": [1, 0, None],
        "FNAP_2": [0, 1, None],
        "FNAP_3": [1, 0, None],
        "FNAP_4": [0, 1, None],
        "FNAP_5": [0, 0, None],
        "SNAP_option": ["Accept EBT at a central location", None, "Some/all vendors accept EBT"],
        "SNAP_option_1": [1, 0, 0],
        "SNAP_option_2": [0, 1, 1],
        "FNAP": ["WIC;SNAP", "SNAP", None],
        "FNAP_3_desc": ["Market Bucks", None, None],
    })

    cfg = {
        "fnap_flags": {
            "FNAP_1": "program_wic",
            "FNAP_2": "program_snap",
            "FNAP_3": "program_incentives",
            "FNAP_4": "program_wic_fmnp",
            "FNAP_5": "program_senior_fmnp",
        },
        "text_fields": {
            "programs_raw": "FNAP",
            "program_incentives_desc": "FNAP_3_desc",
        },
        "snap": {
            "option_text": "SNAP_option",
            "central_booth_flag": "SNAP_option_1",
            "vendor_pos_flag": "SNAP_option_2",
        }
    }

    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        yaml.dump(cfg, f)
        path = f.name

    out = map_program_flags(df, path)
    os.unlink(path)

    assert out["program_wic"].tolist() == [True, False, False]
    assert out["program_snap"].tolist() == [False, True, False]
    assert out["program_incentives"].tolist() == [True, False, False]
    assert out["snap_central_booth"].tolist() == [True, False, False]
    assert out["snap_vendor_pos"].tolist() == [False, True, True]
    assert out["program_incentives_desc"].tolist()[0] == "Market Bucks"
