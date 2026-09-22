import pytest
from src.core.constants import (
    CaseStatus,
    CaseVerdict,
    FraudPattern,
    PolicyAction,
    ApprovalRoute,
    EvidenceSource,
    EvidenceRequestType,
)
from src.models.case import (
    CaseAnswerSubmission,
    CaseData,
    EvidenceItem,
    EvidenceRequest,
    NextBestActions,
    ActionItem,
    SARData,
)

def test_case_submission_model_validation():
    # Construct an example matching the README Example schema
    example_submission = {
        "case_id": "HHG-017",
        "case": {
            "status": "closed_fraud",
            "verdict": "fraud",
            "fraud_probability": 0.86,
            "pattern": "card_testing",
            "pattern_description": "",
            "affected_txn_ids": ["T0412877", "T0412878", "T0412879", "T0412883"],
            "first_suspicious_txn_id": "T0412877",
            "connected_card_ids": ["C00877-K1"],
            "connected_device_profiles": ["SAMSUNG SM-G892A Build/NRD90M | Android 7.0 | samsung browser 6.2 | 2220x1080"],
            "exposure_usd": 268.43,
            "evidence": [
                {
                    "claim": "Three online authorizations under $3 within 40 minutes, then a $259 purchase",
                    "source": "graph",
                    "ref": "query:card_window(card_id=C00377-K1, hours=2)",
                    "entity_ids": ["T0412877", "T0412878", "T0412879", "T0412883"]
                }
            ],
            "similar_prior_cases": ["CC-0141"],
            "summary": "Textbook card testing...",
            "written_to_graph": True,
            "graph_case_id": "CASE-2016-1187"
        },
        "evidence_requests": [
            {
                "type": "customer_validation",
                "asked_after_step": 4,
                "assumed_response": "Customer states they did not make these purchases"
            }
        ],
        "next_best_actions": {
            "initial": [
                {"action": "DECLINE_TRANSACTION", "route": "L1", "reason": "R5: testing sequence observed"},
                {"action": "VERIFY_WITH_CUSTOMER", "route": "auto", "reason": "R1: confirm before blocking"}
            ],
            "final": [
                {"action": "BLOCK_CARD", "route": "L1", "reason": "R2 and R5: customer denied"},
                {"action": "CREATE_CASE", "route": "auto", "reason": "R2"},
                {"action": "FILE_REPORT", "route": "L2", "reason": "R2: shared device links to another card"},
                {"action": "MONITOR_CONNECTED_CARDS", "route": "auto", "reason": "Same device profile on C00877-K1"}
            ],
            "what_changed": "Customer denial raised probability from 0.72 to 0.86 and confirmed the block."
        },
        "sar": {
            "file": True,
            "reason": "R2: confirmed unauthorized use linked by a shared device to a second compromised card",
            "narrative": "On 2016-11-14 between 09:12 and 09:52, card C00377-K1 belonging to customer C00377...",
            "subjects": ["C00377", "C00377-K1", "C00877-K1"],
            "total_amount_usd": 268.43,
            "activity_dates": ["2016-11-14", "2016-11-14"]
        },
        "stop_reason": "Customer denial settled the verdict.",
        "tool_calls": 9,
        "tokens": 12480,
        "latency_s": 18.7
    }

    sub = CaseAnswerSubmission.model_validate(example_submission)
    assert sub.case_id == "HHG-017"
    assert sub.case.status == CaseStatus.CLOSED_FRAUD
    assert sub.case.verdict == CaseVerdict.FRAUD
    assert sub.case.pattern == FraudPattern.CARD_TESTING
    assert sub.next_best_actions.final[0].action == PolicyAction.BLOCK_CARD
    assert sub.next_best_actions.final[0].route == ApprovalRoute.L1
    assert sub.sar.file is True
