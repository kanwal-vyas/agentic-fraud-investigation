import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from src.core.config import settings
from src.data.loader import load_closed_cases
from src.models.dataset import ClosedCaseRecord

# Official Bank Fraud Policy Rules (Rules R1 - R10)
OFFICIAL_POLICY_RULES = [
    {
        "rule_id": "R1",
        "name": "Weak Signal Triage & Verification",
        "condition": "Transaction flagged with model risk score < 0.70 or single weak anomaly without corroboration",
        "actions": ["VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH"],
        "approval": "auto",
        "description": "Verify before you block on a weak single signal (probability < 0.70). Do not block card automatically without customer confirmation or secondary corroboration.",
        "keywords": ["weak signal", "model score", "verify", "step up auth", "probability", "low risk", "unconfirmed"]
    },
    {
        "rule_id": "R2",
        "name": "Customer Denies Transaction",
        "condition": "Cardholder explicitly denies authorizing the transaction upon verification",
        "actions": ["BLOCK_CARD", "CREATE_CASE", "FILE_REPORT"],
        "approval": "L1",
        "description": "Customer denies transaction -> BLOCK_CARD and CREATE_CASE. Add FILE_REPORT (SAR) if exposure > $1,000 or shared link found.",
        "keywords": ["customer denies", "denied", "unauthorized", "block card", "create case", "file report", "chargeback"]
    },
    {
        "rule_id": "R3",
        "name": "Customer Confirms Transaction",
        "condition": "Cardholder verifies that transaction was authorized and legitimate",
        "actions": ["CLOSE_NO_FRAUD", "ALLOW_TRANSACTION"],
        "approval": "auto",
        "description": "Customer confirms transaction -> CLOSE_NO_FRAUD. Remove temporary hold and unfreeze card if restricted.",
        "keywords": ["customer confirms", "authorized", "close no fraud", "allow transaction", "legitimate", "travel verified"]
    },
    {
        "rule_id": "R4",
        "name": "Unresponsive Customer Escalation",
        "condition": "Customer has not responded to verification inquiry within 24 hours",
        "actions": ["MONITOR_CARD", "DECLINE_TRANSACTION", "ESCALATE_TO_ANALYST"],
        "approval": "L1",
        "description": "No reply within 24 hours -> MONITOR_CARD and DECLINE_TRANSACTION. Escalate to fraud analyst if exposure > $500.",
        "keywords": ["no reply", "unresponsive", "24 hours", "monitor card", "decline transaction", "timeout"]
    },
    {
        "rule_id": "R5",
        "name": "Card Testing Rapid Reaction",
        "condition": "Burst of >=3 micro-authorizations (<= $5.00) followed by larger authorization (>= $50.00)",
        "actions": ["DECLINE_TRANSACTION", "STEP_UP_AUTH", "BLOCK_CARD"],
        "approval": "L1",
        "description": "Card testing sequence -> DECLINE_TRANSACTION and STEP_UP_AUTH. If cleared purchase > $100 -> BLOCK_CARD immediately to prevent balance drain.",
        "keywords": ["card testing", "micro authorization", "small amount", "rapid sequence", "burst", "block card"]
    },
    {
        "rule_id": "R6",
        "name": "Shared Device / Syndicate Ring",
        "condition": "Device profile or network fingerprint shared across >=2 distinct customer accounts",
        "actions": ["CREATE_CASE", "FILE_REPORT", "MONITOR_CONNECTED_CARDS"],
        "approval": "L2",
        "description": "Shared origin across multiple cards -> CREATE_CASE, FILE_REPORT, and MONITOR_CONNECTED_CARDS. Place all connected secondary cards on fraud watchlist.",
        "keywords": ["shared device", "device profile", "syndicate", "multi card", "connected cards", "fingerprint"]
    },
    {
        "rule_id": "R7",
        "name": "Disputed But Recurring Baseline Exception",
        "condition": "Flagged transaction matches cardholder's established recurring merchant or geographic baseline",
        "actions": ["CREATE_CASE", "VERIFY_WITH_CUSTOMER", "WARN_CUSTOMER"],
        "approval": "auto",
        "description": "Disputed but recurring baseline -> CREATE_CASE, VERIFY_WITH_CUSTOMER, and WARN_CUSTOMER. Do not block card immediately.",
        "keywords": ["recurring", "historical baseline", "home region", "familiar merchant", "warn customer", "do not block"]
    },
    {
        "rule_id": "R8",
        "name": "High Exposure & Conflicting Evidence Escalation",
        "condition": "Investigative uncertainty remains high and exposure > $500 or conflicting evidence observed",
        "actions": ["ESCALATE_TO_ANALYST"],
        "approval": "L1",
        "description": "Escalate when uncertain and exposure > $500 or conflicting evidence -> ESCALATE_TO_ANALYST for manual review.",
        "keywords": ["uncertain", "conflicting evidence", "exposure > 500", "escalate", "analyst review"]
    },
    {
        "rule_id": "R9",
        "name": "Undocumented Coordinated Anomaly",
        "condition": "Multi-dimensional anomaly detected not fitting known standard patterns",
        "actions": ["CREATE_CASE", "FILE_REPORT", "ESCALATE_TO_ANALYST"],
        "approval": "L2",
        "description": "Undocumented coordinated pattern -> CREATE_CASE, FILE_REPORT, ESCALATE_TO_ANALYST for deep forensic examination.",
        "keywords": ["undocumented", "coordinated", "novel pattern", "anomaly", "forensic"]
    },
    {
        "rule_id": "R10",
        "name": "Proportional Blocking Safeguard",
        "condition": "Multi-card customer with isolated fraud on single card",
        "actions": ["BLOCK_CARD", "MONITOR_CARD"],
        "approval": "L2",
        "description": "Never BLOCK_ALL_CARDS unless >=2 cards show confirmed fraud or account credentials confirmed compromised.",
        "keywords": ["block all cards", "proportional", "credential compromise", "isolated fraud", "safeguard"]
    }
]

# Official Regulatory & Compliance Reference Corpus
OFFICIAL_REGULATORY_REFERENCES = [
    {
        "regulation_id": "FINCEN-BSA-31CFR1020.320",
        "title": "FinCEN Suspicious Activity Report (SAR) Mandate",
        "section": "31 CFR § 1020.320",
        "excerpt": "A bank shall file a Suspicious Activity Report (SAR) for any suspicious transaction conducted or attempted by, at, or through the bank involving $2,000 or more when a suspect can be identified, or $5,000 or more regardless of potential suspects. The report must be filed within 30 calendar days of initial detection. Strict confidentiality applies: no subject may be notified.",
        "mandate_summary": "Mandatory SAR filing for confirmed fraud exposure >= $2,000 (or bank internal threshold >= $1,000 on syndicate links) within 30 days.",
        "keywords": ["fincen", "sar", "suspicious activity report", "bsa", "2000", "5000", "30 days", "file report", "confidentiality"]
    },
    {
        "regulation_id": "CFPB-REG-E-12CFR1005",
        "title": "Electronic Fund Transfers Act (Regulation E)",
        "section": "12 CFR Part 1005 (§ 1005.6 & § 1005.11)",
        "excerpt": "Establishes consumer liability caps for unauthorized electronic fund transfers: consumer liability is capped at $50 if reported within 2 business days of learning of loss/theft, up to $500 if reported within 60 days of periodic statement, and unlimited thereafter. Financial institutions must investigate notices of error and provide provisional credit within 10 business days if investigation is ongoing.",
        "mandate_summary": "Consumer liability limitation ($50/$500) and 10-day provisional credit requirement for disputed electronic transactions.",
        "keywords": ["regulation e", "reg e", "consumer liability", "50 dollar", "provisional credit", "unauthorized transfer", "dispute window"]
    },
    {
        "regulation_id": "PCI-NETWORK-ZERO-LIABILITY",
        "title": "Payment Card Network Zero Liability & CNP Rules",
        "section": "Visa Core Rules / Mastercard Rules (Condition 10.4)",
        "excerpt": "Cardholders are protected by Zero Liability for unauthorized card-not-present (CNP) and counterfeit transactions provided reasonable care was taken to protect the card. Chargeback Condition 10.4 governs Card-Absent Environment fraud claims where merchants did not implement 3D-Secure or CVV/AVS verification.",
        "mandate_summary": "Zero consumer liability for verified unauthorized CNP transactions; merchant liability shift when 3D-Secure/AVS is omitted.",
        "keywords": ["zero liability", "chargeback", "cnp fraud", "card not present", "card network", "visa", "mastercard"]
    },
    {
        "regulation_id": "NIST-SP-800-63B",
        "title": "NIST Digital Identity Guidelines - Authentication & Lifecycle",
        "section": "NIST SP 800-63B Section 5.1.4",
        "excerpt": "Out-of-Band (OOB) authenticators utilizing a separate communication channel (e.g. SMS OTP, push notification) provide Authenticator Assurance Level 2 (AAL2). When automated anomaly detection scores risk above threshold, Step-Up Out-of-Band verification is mandated prior to processing high-value or unusual transactions.",
        "mandate_summary": "Step-up authentication (2FA/SMS/Push) mandated for high-risk or geographically anomalous transactions before taking irreversible blocking action.",
        "keywords": ["nist", "800-63b", "out of band", "oob", "step up auth", "two factor", "2fa", "authentication assurance"]
    },
    {
        "regulation_id": "FFIEC-AUTH-GUIDANCE",
        "title": "FFIEC Layered Security & Anomaly Monitoring Guidance",
        "section": "FFIEC Authentication in an Internet Banking Environment",
        "excerpt": "Financial institutions must implement layered security programs comprising dual-factor authentication, transaction anomaly detection, velocity monitoring, and multi-account correlation to mitigate sophisticated account takeover (ATO) and organized syndicate attacks.",
        "mandate_summary": "Layered anomaly monitoring (velocity, device fingerprinting, multi-account correlation) required to identify syndicated fraud.",
        "keywords": ["ffiec", "layered security", "anomaly monitoring", "account takeover", "velocity", "device fingerprint"]
    }
]

class GraphRAGCorpus:
    """
    Unified knowledge corpus manager for GraphRAG.
    Loads and provides structured access to:
    1. 5,565 Historical Closed Investigation Cases
    2. 10 Official Bank Fraud Policy Rules (R1 - R10)
    3. 5 Regulatory Compliance Mandates & Standards
    """
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or settings.data_dir
        self.closed_cases_df = load_closed_cases(self.data_dir)
        self.policy_rules = OFFICIAL_POLICY_RULES
        self.regulatory_references = OFFICIAL_REGULATORY_REFERENCES

    def get_inventory(self) -> Dict[str, Any]:
        """Generates a complete documented inventory of all corpus sources."""
        confirmed_cases_count = len(self.closed_cases_df[self.closed_cases_df["outcome"] == "confirmed_fraud"])
        cleared_cases_count = len(self.closed_cases_df[self.closed_cases_df["outcome"] == "cleared"])

        return {
            "closed_cases": {
                "source": "closed_cases_history.csv",
                "source_type": "closed_case",
                "total_records": len(self.closed_cases_df),
                "confirmed_fraud_records": confirmed_cases_count,
                "cleared_records": cleared_cases_count,
                "date_range": "2016-07-01 to 2016-10-31",
                "fields_used": [
                    "case_id", "customer_id", "card_id", "opened_at", "closed_at",
                    "outcome", "pattern", "exposure_usd", "n_txns", "actions_taken",
                    "analyst_notes", "connected_card_ids"
                ],
                "identifier_field": "case_id"
            },
            "policy_rules": {
                "source": "Bank Fraud Policy Manual (Rules R1-R10)",
                "source_type": "policy",
                "total_records": len(self.policy_rules),
                "rules": [r["rule_id"] for r in self.policy_rules],
                "fields_used": ["rule_id", "name", "condition", "actions", "approval", "description", "keywords"],
                "identifier_field": "rule_id"
            },
            "regulatory_references": {
                "source": "FinCEN, CFPB Reg E, Payment Networks, NIST, FFIEC",
                "source_type": "regulation",
                "total_records": len(self.regulatory_references),
                "regulations": [reg["regulation_id"] for reg in self.regulatory_references],
                "fields_used": ["regulation_id", "title", "section", "excerpt", "mandate_summary", "keywords"],
                "identifier_field": "regulation_id"
            }
        }
