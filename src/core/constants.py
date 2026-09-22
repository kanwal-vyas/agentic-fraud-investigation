from enum import Enum
from typing import Dict, List

class FraudPattern(str, Enum):
    CARD_TESTING = "card_testing"
    CARD_NOT_PRESENT_FRAUD = "card_not_present_fraud"
    CARD_NOT_PRESENT_NEW_DEVICE = "card_not_present_new_device"
    OUT_OF_REGION_USE = "out_of_region_use"
    ACCOUNT_TAKEOVER = "account_takeover"
    UNDOCUMENTED = "undocumented"
    NONE = "none"

class PolicyAction(str, Enum):
    ALLOW_TRANSACTION = "ALLOW_TRANSACTION"
    DECLINE_TRANSACTION = "DECLINE_TRANSACTION"
    MONITOR_CARD = "MONITOR_CARD"
    MONITOR_CONNECTED_CARDS = "MONITOR_CONNECTED_CARDS"
    WARN_CUSTOMER = "WARN_CUSTOMER"
    VERIFY_WITH_CUSTOMER = "VERIFY_WITH_CUSTOMER"
    STEP_UP_AUTH = "STEP_UP_AUTH"
    BLOCK_CARD = "BLOCK_CARD"
    BLOCK_ALL_CARDS = "BLOCK_ALL_CARDS"
    GENERATE_REPORT = "GENERATE_REPORT"
    CREATE_CASE = "CREATE_CASE"
    FILE_REPORT = "FILE_REPORT"
    ESCALATE_TO_ANALYST = "ESCALATE_TO_ANALYST"
    CLOSE_NO_FRAUD = "CLOSE_NO_FRAUD"

class ApprovalRoute(str, Enum):
    AUTO = "auto"
    L1 = "L1"  # Team lead
    L2 = "L2"  # Fraud manager

class CaseStatus(str, Enum):
    OPEN = "open"
    CLOSED_FRAUD = "closed_fraud"
    CLOSED_LEGITIMATE = "closed_legitimate"
    ESCALATED = "escalated"

class CaseVerdict(str, Enum):
    FRAUD = "fraud"
    LEGITIMATE = "legitimate"
    UNCERTAIN = "uncertain"

class EvidenceSource(str, Enum):
    GRAPH = "graph"
    DOCUMENT = "document"
    CUSTOMER = "customer"
    EXTERNAL = "external"

class EvidenceRequestType(str, Enum):
    CUSTOMER_VALIDATION = "customer_validation"
    STEP_UP_AUTH = "step_up_auth"
    ANALYST_INFO = "analyst_info"

# Default action routing rules based on exposure and action type
ACTION_DEFAULT_ROUTES: Dict[PolicyAction, ApprovalRoute] = {
    PolicyAction.ALLOW_TRANSACTION: ApprovalRoute.AUTO,
    PolicyAction.MONITOR_CARD: ApprovalRoute.AUTO,
    PolicyAction.MONITOR_CONNECTED_CARDS: ApprovalRoute.AUTO,
    PolicyAction.WARN_CUSTOMER: ApprovalRoute.AUTO,
    PolicyAction.VERIFY_WITH_CUSTOMER: ApprovalRoute.AUTO,
    PolicyAction.STEP_UP_AUTH: ApprovalRoute.AUTO,
    PolicyAction.GENERATE_REPORT: ApprovalRoute.AUTO,
    PolicyAction.CREATE_CASE: ApprovalRoute.AUTO,
    PolicyAction.ESCALATE_TO_ANALYST: ApprovalRoute.AUTO,
    PolicyAction.CLOSE_NO_FRAUD: ApprovalRoute.AUTO,
    PolicyAction.DECLINE_TRANSACTION: ApprovalRoute.L1,
    PolicyAction.BLOCK_CARD: ApprovalRoute.L1,  # L1 if exposure <= $2,500; L2 if exposure > $2,500
    PolicyAction.BLOCK_ALL_CARDS: ApprovalRoute.L2,
    PolicyAction.FILE_REPORT: ApprovalRoute.L2,
}

POLICY_RULES_SUMMARY = {
    "R1": "Verify before you block on a weak single signal (probability < 0.70) -> VERIFY_WITH_CUSTOMER or STEP_UP_AUTH",
    "R2": "Customer denies transaction -> BLOCK_CARD and CREATE_CASE. Add FILE_REPORT if exposure > $1,000 or shared link",
    "R3": "Customer confirms transaction -> CLOSE_NO_FRAUD",
    "R4": "No reply within 24 hours -> MONITOR_CARD and DECLINE_TRANSACTION. Escalate if exposure > $500",
    "R5": "Card testing sequence -> DECLINE_TRANSACTION and STEP_UP_AUTH. If cleared purchase > $100 -> BLOCK_CARD",
    "R6": "Shared origin across multiple cards -> CREATE_CASE, FILE_REPORT, and MONITOR_CONNECTED_CARDS",
    "R7": "Disputed but recurring baseline -> CREATE_CASE, VERIFY_WITH_CUSTOMER, and WARN_CUSTOMER. Do not block",
    "R8": "Escalate when uncertain and exposure > $500 or conflicting evidence -> ESCALATE_TO_ANALYST",
    "R9": "Undocumented coordinated pattern -> CREATE_CASE, FILE_REPORT, ESCALATE_TO_ANALYST",
    "R10": "Never BLOCK_ALL_CARDS unless >=2 cards show confirmed fraud or credentials confirmed compromised",
}
