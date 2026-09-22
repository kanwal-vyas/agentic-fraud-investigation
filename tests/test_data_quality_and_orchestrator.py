import pytest
import numpy as np
from src.core.validation import is_valid_entity_id, clean_entity_id
from src.tigergraph.sample_client import SampleGraphClient
from src.mcp.server import TigerGraphMCPServer
from src.agent.orchestrator import AgenticFraudInvestigator
from src.models.agent import InvestigationTrigger, TriggerType
from src.reasoning.engine import DeterministicReasoningEngine
from src.reasoning.evidence_planner import ControlledEvidencePlanner
from src.models.reasoning import EvidenceSufficiencyState, UncertaintyAssessment, UncertaintyLevel
from src.models.context import InvestigationContext

def test_entity_id_validation():
    # Test invalid device identifiers
    assert not is_valid_entity_id(None, "DeviceProfile")
    assert not is_valid_entity_id("", "DeviceProfile")
    assert not is_valid_entity_id("   ", "DeviceProfile")
    assert not is_valid_entity_id("nan", "DeviceProfile")
    assert not is_valid_entity_id("NaN", "DeviceProfile")
    assert not is_valid_entity_id("None", "DeviceProfile")
    assert not is_valid_entity_id("null", "DeviceProfile")
    assert not is_valid_entity_id("unknown", "DeviceProfile")
    assert not is_valid_entity_id("UnknownDevice | UnknownOS | UnknownBrowser | UnknownResolution", "DeviceProfile")
    assert not is_valid_entity_id(float("nan"), "DeviceProfile")

    # Test valid device identifiers
    assert is_valid_entity_id("iOS 11.1.2 | Safari 11.0 | 2208x1242 | Apple iPhone 7 Plus", "DeviceProfile")
    assert is_valid_entity_id("Windows 10 | Chrome 66.0 | 1920x1080 | Windows Desktop", "DeviceProfile")

    # Test invalid email and region identifiers
    assert not is_valid_entity_id("nan", "EmailDomain")
    assert not is_valid_entity_id("unknown", "EmailDomain")
    assert not is_valid_entity_id("nan", "BillingRegion")
    assert not is_valid_entity_id("unknown", "BillingRegion")

    # Test valid email and region
    assert is_valid_entity_id("gmail.com", "EmailDomain")
    assert is_valid_entity_id("315", "BillingRegion")

def test_clean_entity_id():
    assert clean_entity_id(None) is None
    assert clean_entity_id("nan") is None
    assert clean_entity_id("NaN") is None
    assert clean_entity_id("  ") is None
    assert clean_entity_id("gmail.com") == "gmail.com"

def test_sample_client_missing_device_safety():
    client = SampleGraphClient()
    # find_shared_devices on invalid string must return safe empty dictionary
    res_nan = client.find_shared_devices("nan")
    assert res_nan["profile_id"] == ""
    assert res_nan["is_shared"] is False
    assert len(res_nan["connected_cards"]) == 0
    assert len(res_nan["connected_customers"]) == 0

    res_none = client.find_shared_devices("")
    assert res_none["is_shared"] is False
    assert len(res_none["connected_cards"]) == 0
    assert len(res_none["connected_customers"]) == 0

def test_mcp_find_shared_devices_invalid_id():
    server = TigerGraphMCPServer()
    res = server.call_tool("find_shared_devices", {"profile_id": "nan"})
    assert res["status"] == "invalid_entity"
    assert res["subject"]["is_shared"] is False
    assert any("Device profile identifier is missing or invalid" in e for e in res["evidence"])

def test_agent_missing_device_hhg003_trace():
    investigator = AgenticFraudInvestigator()
    # HHG-003 is a customer report with a missing/null device
    trigger = InvestigationTrigger(
        case_id="HHG-003",
        trigger_type=TriggerType.CUSTOMER_REPORT,
        transaction_id=3530164,
        customer_id="C08623",
        card_id="C08623-K2",
        model_risk_score=0.04,
        trigger_details="Customer C08623 message: 'I never made this $49.00 purchase. Please check my card.' Refers to 3530164."
    )
    result = investigator.investigate(trigger)
    
    # Verify no 'device nan' or synthetic device profile in steps or evidence
    for step in result.investigation_steps:
        assert "device nan" not in step.reason.lower()
        assert "device nan" not in step.result_summary.lower()
        for k, v in step.input_args.items():
            assert str(v).lower() != "nan"

    for ev in result.final_assessment.supporting_evidence:
        assert "'nan'" not in ev.lower()
        assert "device profile 'nan'" not in ev.lower()

    # Rule R2 mandates immediate card block for customer-reported fraud
    assert result.next_best_action.action.value == "BLOCK_CARD"
    assert result.stop_decision.should_stop is True

def test_dynamic_tool_selection_and_early_stop():
    investigator = AgenticFraudInvestigator()
    # Benign routine transaction with low risk score and normal velocity
    trigger = InvestigationTrigger(
        case_id="HHG-BENIGN",
        trigger_type=TriggerType.RISK_SCORE,
        transaction_id=3000014,
        customer_id="C08945",
        card_id="C08945-K1",
        model_risk_score=0.02,
        trigger_details="Routine transaction monitored by ML model (Risk Score: 0.02)"
    )
    result = investigator.investigate(trigger)
    
    # Agent stops after checking transaction and velocity, without calling unrelated investigation tools
    assert result.total_tool_calls <= 2
    assert result.next_best_action is not None
    assert result.final_assessment is not None

def test_evidence_planner_justification():
    planner = ControlledEvidencePlanner()
    
    # Case 1: Customer Report -> No customer validation request needed (authorization denial known)
    ctx_report = InvestigationContext(
        case_id="HHG-003",
        opened_at="2016-07-01 00:00:00",
        trigger_type="customer_report",
        trigger_text="Customer reported fraud",
        flagged_txn_id=2987114,
        card_id="card_123",
        customer_id="cust_123",
        profile_id="",
        model_risk_score=0.04
    )
    reqs_report = planner.plan_requests(ctx_report, EvidenceSufficiencyState.SUFFICIENT, UncertaintyAssessment(level=UncertaintyLevel.LOW, reasons=[]))
    assert not any(r.request_type == "customer_validation" for r in reqs_report)

    # Case 2: Weak signal risk score (0.55) -> Customer validation request is justified under Rule R1
    ctx_weak = InvestigationContext(
        case_id="HHG-002",
        opened_at="2016-07-01 00:00:00",
        trigger_type="risk_score",
        trigger_text="Model risk score alert",
        flagged_txn_id=2987002,
        card_id="card_456",
        customer_id="cust_456",
        profile_id="",
        model_risk_score=0.55
    )
    reqs_weak = planner.plan_requests(ctx_weak, EvidenceSufficiencyState.INSUFFICIENT, UncertaintyAssessment(level=UncertaintyLevel.MATERIAL, reasons=["Weak score"]))
    assert any(r.request_type == "customer_validation" for r in reqs_weak)
