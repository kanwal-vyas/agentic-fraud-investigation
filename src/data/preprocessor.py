import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple, Union
import pandas as pd
import numpy as np

def build_device_profile_id(device_info: Any, os_val: Any, browser_val: Any, screen_val: Any) -> str:
    """Creates normalized composite DeviceProfile ID: DeviceInfo | OS | Browser | Screen"""
    d = str(device_info).strip() if pd.notna(device_info) and str(device_info).strip() != "" else "UnknownDevice"
    o = str(os_val).strip() if pd.notna(os_val) and str(os_val).strip() != "" else "UnknownOS"
    b = str(browser_val).strip() if pd.notna(browser_val) and str(browser_val).strip() != "" else "UnknownBrowser"
    s = str(screen_val).strip() if pd.notna(screen_val) and str(screen_val).strip() != "" else "UnknownScreen"
    return f"{d} | {o} | {b} | {s}"

def extract_device_profiles(identity_df: pd.DataFrame) -> pd.DataFrame:
    """Extracts unique DeviceProfile vertices from identity records."""
    profiles = []
    seen = set()
    for _, row in identity_df.iterrows():
        prof_id = build_device_profile_id(
            row.get("DeviceInfo"),
            row.get("id_30"),
            row.get("id_31"),
            row.get("id_33")
        )
        if prof_id not in seen:
            seen.add(prof_id)
            profiles.append({
                "profile_id": prof_id,
                "device_info": str(row.get("DeviceInfo", "") or ""),
                "os": str(row.get("id_30", "") or ""),
                "browser": str(row.get("id_31", "") or ""),
                "screen": str(row.get("id_33", "") or ""),
                "device_type": str(row.get("DeviceType", "") or ""),
            })
    return pd.DataFrame(profiles)

def build_card_lookup(closed_cases_df: pd.DataFrame, case_pack_df: pd.DataFrame) -> Dict[int, str]:
    """
    Builds an exact transaction -> card_id lookup table from closed cases and case pack.
    """
    txn_to_card: Dict[int, str] = {}
    
    # 1. Closed cases
    for _, row in closed_cases_df.iterrows():
        card_id = str(row["card_id"]).strip()
        txn_ids_str = str(row.get("txn_ids", ""))
        if pd.notna(txn_ids_str) and txn_ids_str:
            for t_str in txn_ids_str.split("|"):
                if t_str.strip():
                    try:
                        tid = int(float(t_str.strip()))
                        txn_to_card[tid] = card_id
                    except ValueError:
                        continue
        first_txn = row.get("first_fraud_txn_id")
        if pd.notna(first_txn):
            try:
                tid = int(float(first_txn))
                txn_to_card[tid] = card_id
            except ValueError:
                pass
                
    # 2. Case pack benchmark cases
    for _, row in case_pack_df.iterrows():
        card_id = str(row["card_id"]).strip()
        flagged_tid = int(row["flagged_txn_id"])
        txn_to_card[flagged_tid] = card_id
        
    return txn_to_card

def assign_card_id(row: pd.Series, txn_card_lookup: Dict[int, str]) -> str:
    """
    Assigns card_id to a transaction record.
    1. If transaction has explicit card_id from closed cases or case pack, return it.
    2. Otherwise, defaults to primary card: customer_id-K1.
    """
    tid = int(row["TransactionID"])
    if tid in txn_card_lookup:
        return txn_card_lookup[tid]
    cust_id = str(row["customer_id"]).strip()
    return f"{cust_id}-K1"

def preprocess_subdataset(
    tx_df: pd.DataFrame,
    id_df: Optional[pd.DataFrame] = None,
    cc_df: Optional[pd.DataFrame] = None,
    cp_df: Optional[pd.DataFrame] = None
) -> Dict[str, pd.DataFrame]:
    """
    Transforms tabular dataframe chunks into clean, normalized graph entity tables:
    - customers
    - cards
    - device_profiles
    - email_domains
    - billing_regions
    - transactions
    - closed_cases (if cc_df provided)
    """
    cc = cc_df if cc_df is not None else pd.DataFrame()
    cp = cp_df if cp_df is not None else pd.DataFrame()
    txn_card_lookup = build_card_lookup(cc, cp)
    
    # 1. Identity / Device Profiles
    id_map = {}
    if id_df is not None and not id_df.empty:
        for _, r in id_df.iterrows():
            prof_id = build_device_profile_id(r.get("DeviceInfo"), r.get("id_30"), r.get("id_31"), r.get("id_33"))
            id_map[int(r["TransactionID"])] = prof_id
        dev_profiles_df = extract_device_profiles(id_df)
    else:
        dev_profiles_df = pd.DataFrame(columns=["profile_id", "device_info", "os", "browser", "screen", "device_type"])

    # 2. Transactions & Cards
    tx_records = []
    card_records = {}
    cust_records = set()
    email_domains = set()
    billing_regions = set()
    
    for _, r in tx_df.iterrows():
        tid = int(r["TransactionID"])
        cust_id = str(r["customer_id"]).strip()
        card_id = assign_card_id(r, txn_card_lookup)
        
        cust_records.add(cust_id)
        
        if card_id not in card_records:
            card_records[card_id] = {
                "card_id": card_id,
                "customer_id": cust_id,
                "issuer_code": int(r["card1"]),
                "card_network": str(r["card4"]) if pd.notna(r["card4"]) else "unknown",
                "card_type": str(r["card6"]) if pd.notna(r["card6"]) else "unknown",
                "card1": int(r["card1"]),
                "card4": str(r["card4"]) if pd.notna(r["card4"]) else "unknown",
                "card6": str(r["card6"]) if pd.notna(r["card6"]) else "unknown",
            }
            
        prof_id = id_map.get(tid, "")
        
        email_dom = str(r["P_emaildomain"]).strip() if pd.notna(r.get("P_emaildomain")) and str(r["P_emaildomain"]).strip() else ""
        if email_dom:
            email_domains.add(email_dom)
            
        addr1_val = str(r["addr1"]).strip() if pd.notna(r.get("addr1")) and str(r["addr1"]).strip() else ""
        addr2_val = str(r["addr2"]).strip() if pd.notna(r.get("addr2")) and str(r["addr2"]).strip() else "87.0"
        if addr1_val:
            billing_regions.add((addr1_val, addr2_val))
            
        tx_records.append({
            "txn_id": str(tid),
            "amount": float(r["TransactionAmt"]),
            "ts": str(r["ts"]),
            "channel": str(r["channel"]),
            "risk_score": float(r["risk_score"]),
            "product_cd": str(r["ProductCD"]),
            "addr1": addr1_val,
            "addr2": addr2_val,
            "card_id": card_id,
            "customer_id": cust_id,
            "profile_id": prof_id,
            "email_domain": email_dom,
        })

    customers_df = pd.DataFrame([{"customer_id": c} for c in cust_records])
    cards_df = pd.DataFrame(list(card_records.values()))
    transactions_df = pd.DataFrame(tx_records)
    email_domains_df = pd.DataFrame([{"domain": d} for d in email_domains])
    billing_regions_df = pd.DataFrame([{"region_code": r[0], "country_code": r[1]} for r in billing_regions])
    
    return {
        "customers": customers_df,
        "cards": cards_df,
        "device_profiles": dev_profiles_df,
        "email_domains": email_domains_df,
        "billing_regions": billing_regions_df,
        "transactions": transactions_df,
    }
