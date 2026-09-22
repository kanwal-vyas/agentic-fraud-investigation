from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import pandas as pd
from src.core.config import settings
from src.data.loader import (
    load_case_pack,
    load_closed_cases,
    load_identity,
    load_transactions_sample,
    get_data_path,
)

REQUIRED_FILES = [
    "case_pack.csv",
    "closed_cases_history.csv",
    "identity.csv",
    "transactions.csv",
    "README.md",
]

REQUIRED_CASE_PACK_COLS = [
    "case_id",
    "opened_at",
    "trigger_type",
    "trigger_text",
    "flagged_txn_id",
    "card_id",
    "customer_id",
    "risk_score",
]

REQUIRED_CLOSED_CASES_COLS = [
    "case_id",
    "customer_id",
    "card_id",
    "opened_at",
    "closed_at",
    "outcome",
    "pattern",
    "first_fraud_txn_id",
    "txn_ids",
    "n_txns",
    "exposure_usd",
    "connected_card_ids",
    "actions_taken",
    "report_filed",
    "analyst_notes",
]

REQUIRED_IDENTITY_COLS = [
    "TransactionID",
    "DeviceInfo",
    "DeviceType",
    "id_15",
    "id_23",
    "id_30",
    "id_31",
    "id_33",
]

REQUIRED_TRANSACTIONS_COLS = [
    "TransactionID",
    "customer_id",
    "card1",
    "card4",
    "card6",
    "TransactionAmt",
    "TransactionDT",
    "ts",
    "ProductCD",
    "channel",
    "risk_score",
    "addr1",
    "addr2",
    "P_emaildomain",
]

def validate_dataset_files(data_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    base = Path(data_dir) if data_dir else settings.data_dir
    results = {}
    for filename in REQUIRED_FILES:
        path = base / filename
        exists = path.exists()
        size_bytes = path.stat().st_size if exists else 0
        results[filename] = {
            "exists": exists,
            "path": str(path),
            "size_bytes": size_bytes,
        }
    all_exist = all(r["exists"] for r in results.values())
    return {
        "valid": all_exist,
        "files": results,
    }

def validate_schemas(data_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    cp = load_case_pack(data_dir)
    cc = load_closed_cases(data_dir)
    id_df = load_identity(data_dir, nrows=100)
    tx_sample = load_transactions_sample(data_dir, nrows=100)

    cp_missing = [c for c in REQUIRED_CASE_PACK_COLS if c not in cp.columns]
    cc_missing = [c for c in REQUIRED_CLOSED_CASES_COLS if c not in cc.columns]
    id_missing = [c for c in REQUIRED_IDENTITY_COLS if c not in id_df.columns]
    tx_missing = [c for c in REQUIRED_TRANSACTIONS_COLS if c not in tx_sample.columns]

    valid = not (cp_missing or cc_missing or id_missing or tx_missing)
    return {
        "valid": valid,
        "missing_columns": {
            "case_pack": cp_missing,
            "closed_cases": cc_missing,
            "identity": id_missing,
            "transactions": tx_missing,
        },
        "row_counts": {
            "case_pack": len(cp),
            "closed_cases": len(cc),
        },
    }

def validate_case_pack_integrity(data_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    cp = load_case_pack(data_dir)
    
    # 20 benchmark cases
    is_20_cases = len(cp) == 20
    case_ids = cp["case_id"].tolist()
    expected_ids = [f"HHG-{i:03d}" for i in range(1, 21)]
    ids_match = case_ids == expected_ids

    no_null_keys = bool(
        cp["case_id"].notna().all()
        and cp["flagged_txn_id"].notna().all()
        and cp["card_id"].notna().all()
        and cp["customer_id"].notna().all()
    )

    is_valid = bool(is_20_cases and ids_match and no_null_keys)

    return {
        "valid": is_valid,
        "case_count": len(cp),
        "case_ids_match": bool(ids_match),
        "no_null_keys": bool(no_null_keys),
    }
