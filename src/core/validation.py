from typing import Any, Optional, Set
import math
import pandas as pd
import numpy as np

INVALID_ENTITY_STRINGS: Set[str] = {
    "",
    "nan",
    "none",
    "null",
    "unknown",
    "n/a",
    "na",
    "undefined",
    "unknowndevice",
    "unknownos",
    "unknownbrowser",
    "unknownscreen",
    "unknowncard",
    "unknowncustomer",
    "unknowndevice | unknownos | unknownbrowser | unknownscreen",
    "nan | nan | nan | nan",
    "none | none | none | none",
}

def clean_entity_id(value: Any) -> Optional[str]:
    """
    Cleans and normalizes an entity identifier.
    Returns None if the value is missing, NaN, null, or a placeholder string.
    """
    if value is None:
        return None
    
    if isinstance(value, float) and (math.isnan(value) or np.isnan(value)):
        return None
    
    if pd.isna(value):
        return None
    
    val_str = str(value).strip()
    if not val_str:
        return None
    
    val_lower = val_str.lower()
    if val_lower in INVALID_ENTITY_STRINGS:
        return None
    
    # Check if the string consists solely of empty separators or unknown tokens like "| | |"
    parts = [p.strip().lower() for p in val_str.split("|")]
    if all(not p or p in INVALID_ENTITY_STRINGS or p.startswith("unknown") for p in parts):
        return None
    
    return val_str

def is_valid_entity_id(value: Any, entity_type: str = "generic") -> bool:
    """
    Validates whether an entity identifier is legitimate and non-missing.
    Returns False for nulls, NaN, 'nan', 'unknown', or empty strings.
    """
    cleaned = clean_entity_id(value)
    if cleaned is None:
        return False
    
    if entity_type.lower() in ["device", "deviceprofile", "device_profile"]:
        # Devices must contain at least one meaningful hardware/browser/OS token
        parts = [p.strip().lower() for p in cleaned.split("|")]
        meaningful = [p for p in parts if p and p not in INVALID_ENTITY_STRINGS and not p.startswith("unknown")]
        return len(meaningful) > 0

    return True
