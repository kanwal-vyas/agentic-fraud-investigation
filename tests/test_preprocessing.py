import pytest
import pandas as pd
from src.data.preprocessor import (
    build_device_profile_id,
    extract_device_profiles,
    preprocess_subdataset,
)

def test_build_device_profile_id():
    prof = build_device_profile_id("SAMSUNG SM-G892A", "Android 7.0", "samsung browser 6.2", "2220x1080")
    assert prof == "SAMSUNG SM-G892A | Android 7.0 | samsung browser 6.2 | 2220x1080"
    
    prof_empty = build_device_profile_id(None, None, None, None)
    assert prof_empty == "UnknownDevice | UnknownOS | UnknownBrowser | UnknownScreen"

def test_preprocess_subdataset_entities():
    # Construct small test DataFrames
    tx_df = pd.DataFrame([
        {
            "TransactionID": 3000001,
            "customer_id": "C001",
            "card1": 12345,
            "card4": "visa",
            "card6": "debit",
            "TransactionAmt": 150.00,
            "TransactionDT": 1000,
            "ts": "2016-07-02 00:00:00",
            "ProductCD": "C",
            "channel": "online",
            "risk_score": 0.45,
            "addr1": 299.0,
            "addr2": 87.0,
            "P_emaildomain": "gmail.com",
            "R_emaildomain": "gmail.com",
        }
    ])
    id_df = pd.DataFrame([
        {
            "TransactionID": 3000001,
            "DeviceInfo": "SM-G892A",
            "DeviceType": "mobile",
            "id_15": "New",
            "id_23": "IP_PROXY:TRANSPARENT",
            "id_30": "Android 7.0",
            "id_31": "chrome 62.0",
            "id_33": "1920x1080",
        }
    ])
    
    res = preprocess_subdataset(tx_df, id_df)
    assert "customers" in res
    assert "cards" in res
    assert "device_profiles" in res
    assert "transactions" in res
    
    assert len(res["customers"]) == 1
    assert len(res["cards"]) == 1
    assert len(res["device_profiles"]) == 1
    assert len(res["transactions"]) == 1
    
    assert res["transactions"].iloc[0]["card_id"] == "C001-K1"
    assert res["transactions"].iloc[0]["profile_id"] == "SM-G892A | Android 7.0 | chrome 62.0 | 1920x1080"
