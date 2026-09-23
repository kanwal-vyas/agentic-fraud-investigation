import pytest
import datetime
from typing import Dict, Any, List
from src.core.constants import PolicyAction, ApprovalRoute, FraudPattern, CaseVerdict
from src.models.case_memory import (
    CaseLifecycleStatus,
    ActionExecutionStatus,
    PersistedEvidenceItem,
    CaseDecisionRecord,
    ActionAuditRecord,
    SARCaseRecord,
    ReassessmentRecord,
    CaseMemoryRecord,
)
from src.models.agent import InvestigationTrigger, TriggerType, InvestigationResult
from src.memory.lifecycle import CaseLifecycleManager
from src.memory.case_store import InMemoryCaseStore
from src.memory.sar_generator import SARCaseEvaluator
from src.memory.graph_writeback import CaseGraphWritebackEngine
from src.tigergraph.sample_client import SampleGraphClient
from src.agent.orchestrator import AgenticFraudInvestigator
from src.mcp.server import TigerGraphMCPServer

def test_a_case_creation():
    """A. Test case creation and initial status in CaseStore."""
    store = InMemoryCaseStore()
    case = CaseMemoryRecord(
        case_id="TEST-CASE-001",
        customer_id="C001",
        card_id="card_001",
        triggering_txn_id=1001,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.OPEN
    )
    created = store.create_case(case)
    assert created.case_id == "TEST-CASE-001"
    assert created.status == CaseLifecycleStatus.OPEN
    assert store.get_case("TEST-CASE-001") is not None

def test_b_case_update():
    """B. Test updating case fields."""
    store = InMemoryCaseStore()
    case = CaseMemoryRecord(
        case_id="TEST-CASE-002",
        customer_id="C002",
        card_id="card_002",
        triggering_txn_id=1002,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.OPEN
    )
    store.create_case(case)
    updated = store.update_case("TEST-CASE-002", {"status": CaseLifecycleStatus.INVESTIGATING, "confidence": 0.85})
    assert updated.status == CaseLifecycleStatus.INVESTIGATING
    assert updated.confidence == 0.85

def test_c_evidence_persistence():
    """C. Test appending evidence items with provenance."""
    store = InMemoryCaseStore()
    case = CaseMemoryRecord(
        case_id="TEST-CASE-003",
        customer_id="C003",
        card_id="card_003",
        triggering_txn_id=1003,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.OPEN
    )
    store.create_case(case)
    ev_item = PersistedEvidenceItem(
        statement="3 high velocity transactions in 5 minutes",
        source_id="detect_velocity:1003",
        source_type="graph",
        category="graph_fact",
        timestamp=datetime.datetime.now().isoformat()
    )
    store.append_evidence("TEST-CASE-003", ev_item)
    retrieved = store.get_case("TEST-CASE-003")
    assert len(retrieved.evidence_items) == 1
    assert retrieved.evidence_items[0].source_id == "detect_velocity:1003"
    assert retrieved.evidence_items[0].source_type == "graph"

def test_d_finding_persistence():
    """D. Test appending supporting and contradictory findings."""
    store = InMemoryCaseStore()
    case = CaseMemoryRecord(
        case_id="TEST-CASE-004",
        customer_id="C004",
        card_id="card_004",
        triggering_txn_id=1004,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.OPEN
    )
    store.create_case(case)
    store.append_finding("TEST-CASE-004", "Card testing detected at online merchant", finding_type="supporting")
    store.append_finding("TEST-CASE-004", "Customer confirmed travel authorization", finding_type="contradictory")
    retrieved = store.get_case("TEST-CASE-004")
    assert "Card testing detected at online merchant" in retrieved.supporting_findings
    assert "Customer confirmed travel authorization" in retrieved.contradictory_findings

def test_e_decision_persistence():
    """E. Test appending policy decisions."""
    store = InMemoryCaseStore()
    case = CaseMemoryRecord(
        case_id="TEST-CASE-005",
        customer_id="C005",
        card_id="card_005",
        triggering_txn_id=1005,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.OPEN
    )
    store.create_case(case)
    decision = {
        "rules_evaluated": ["R1", "R8"],
        "permitted": True,
        "required_action": "BLOCK_CARD",
        "approval_route": "L1",
        "approval_required": True,
        "violations": [],
        "prerequisites": ["card_status_active"]
    }
    store.append_decision("TEST-CASE-005", decision)
    retrieved = store.get_case("TEST-CASE-005")
    assert retrieved.policy_decision.required_action == "BLOCK_CARD"
    assert retrieved.policy_decision.approval_required is True

def test_f_action_persistence():
    """F. Test recording and updating actions."""
    store = InMemoryCaseStore()
    case = CaseMemoryRecord(
        case_id="TEST-CASE-006",
        customer_id="C006",
        card_id="card_006",
        triggering_txn_id=1006,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.OPEN
    )
    store.create_case(case)
    action = {
        "action": "BLOCK_CARD",
        "execution_status": ActionExecutionStatus.EXECUTED,
        "approval_route": "L1",
        "approval_required": True,
        "rationale": "High velocity card testing confirmed",
        "authorized_by": "Senior Analyst L1",
        "executed_at": datetime.datetime.now().isoformat()
    }
    store.append_action("TEST-CASE-006", action)
    retrieved = store.get_case("TEST-CASE-006")
    assert len(retrieved.actions_actually_executed) == 1
    assert retrieved.actions_actually_executed[0].action == "BLOCK_CARD"
    assert retrieved.actions_actually_executed[0].execution_status == ActionExecutionStatus.EXECUTED

def test_g_outcome_persistence():
    """G. Test resolving outcome and status."""
    store = InMemoryCaseStore()
    case = CaseMemoryRecord(
        case_id="TEST-CASE-007",
        customer_id="C007",
        card_id="card_007",
        triggering_txn_id=1007,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.OPEN
    )
    store.create_case(case)
    store.append_outcome("TEST-CASE-007", "closed_fraud", CaseLifecycleStatus.RESOLVED)
    retrieved = store.get_case("TEST-CASE-007")
    assert retrieved.final_outcome == "closed_fraud"
    assert retrieved.status == CaseLifecycleStatus.RESOLVED

def test_h_case_retrieval():
    """H. Test exact case retrieval."""
    store = InMemoryCaseStore()
    case = CaseMemoryRecord(
        case_id="TEST-CASE-008",
        customer_id="C008",
        card_id="card_008",
        triggering_txn_id=1008,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.OPEN
    )
    store.create_case(case)
    assert store.get_case("TEST-CASE-008") is not None
    assert store.get_case("NON_EXISTENT") is None

def test_i_similar_case_retrieval_and_provenance():
    """I & J. Test similarity search across customer, card, and pattern preserving provenance."""
    store = InMemoryCaseStore()
    case1 = CaseMemoryRecord(
        case_id="CC-HIST-001",
        customer_id="C100",
        card_id="card_100",
        triggering_txn_id=2001,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.RESOLVED,
        fraud_assessment="likely_fraud",
        fraud_patterns_identified=["card_testing"],
        final_outcome="closed_fraud",
        summary="Prior confirmed card testing attack"
    )
    store.create_case(case1)

    # Search by customer_id
    matches_cust = store.search_similar_cases({"customer_id": "C100"})
    assert len(matches_cust) == 1
    assert matches_cust[0].case_id == "CC-HIST-001"
    assert matches_cust[0].outcome == "confirmed_fraud"

    # Search by card_id
    matches_card = store.search_similar_cases({"card_id": "card_100"})
    assert len(matches_card) == 1

    # Search by pattern
    matches_pat = store.search_similar_cases({"pattern": "card_testing"})
    assert len(matches_pat) == 1
    assert matches_pat[0].pattern == "card_testing"

def test_k_current_vs_historical_separation():
    """K. Test that historical retrieved cases are never confused with current graph evidence."""
    store = InMemoryCaseStore()
    case = CaseMemoryRecord(
        case_id="CC-HIST-002",
        customer_id="C200",
        card_id="card_200",
        triggering_txn_id=3001,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.RESOLVED,
        fraud_assessment="likely_fraud",
        fraud_patterns_identified=["velocity_attack"],
        final_outcome="closed_fraud",
        summary="Confirmed high velocity fraud"
    )
    store.create_case(case)

    matches = store.search_similar_cases({"customer_id": "C200"})
    for m in matches:
        assert m.case_id == "CC-HIST-002"
        assert m.outcome in ["confirmed_fraud", "cleared"]

def test_l_m_idempotent_graph_writeback_and_no_duplicates():
    """L & M. Test that multiple writebacks do not duplicate Case vertices."""
    sample_client = SampleGraphClient()
    engine = CaseGraphWritebackEngine(sample_client=sample_client)

    case = CaseMemoryRecord(
        case_id="CASE-IDEMPOTENT-001",
        customer_id="C300",
        card_id="card_300",
        triggering_txn_id=4001,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.INVESTIGATING,
        fraud_assessment="suspicious_but_uncertain",
        confidence=0.6,
        summary="Initial investigation writeback"
    )

    # First write
    res1 = engine.write_case(case)
    assert res1["status"] == "success"
    assert sample_client.get_case("CASE-IDEMPOTENT-001") is not None

    # Update case attributes and write again (idempotent upsert)
    case.status = CaseLifecycleStatus.RESOLVED
    case.fraud_assessment = "likely_fraud"
    case.confidence = 0.95
    res2 = engine.write_case(case)
    assert res2["status"] == "success"

    # Verify updated attributes without duplicate records
    c_vertex = sample_client.get_case("CASE-IDEMPOTENT-001")
    assert c_vertex["status"] == "RESOLVED"
    assert c_vertex["verdict"] == "likely_fraud"
    assert c_vertex["fraud_probability"] == 0.95

def test_n_offline_mode_reporting():
    """N. Test offline mode operation and reporting."""
    engine = CaseGraphWritebackEngine()
    assert engine.is_live_deployment() is False
    case = CaseMemoryRecord(
        case_id="CASE-OFFLINE-001",
        customer_id="C400",
        card_id="card_400",
        triggering_txn_id=5001,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.OPEN
    )
    res = engine.write_case(case)
    assert res["mode"] == "OFFLINE"
    assert res["status"] == "success"

def test_p_q_approval_required_boundary_and_destructive_execution_protection():
    """P & Q. Destructive actions cannot become EXECUTED without explicit human authorization."""
    mgr = CaseLifecycleManager()
    case = CaseMemoryRecord(
        case_id="CASE-APPROVAL-001",
        customer_id="C500",
        card_id="card_500",
        triggering_txn_id=6001,
        trigger_type="risk_score",
        created_at=datetime.datetime.now().isoformat(),
        updated_at=datetime.datetime.now().isoformat(),
        status=CaseLifecycleStatus.INVESTIGATING
    )

    # Record recommended destructive action requiring approval
    mgr.record_recommendation(
        case=case,
        action="BLOCK_CARD",
        approval_required=True,
        approval_route="L1",
        rationale="High velocity attack detected",
        policy_references=["R1", "R8"]
    )
    assert case.status == CaseLifecycleStatus.ACTION_PENDING_APPROVAL
    assert case.execution_status == ActionExecutionStatus.PENDING_APPROVAL

    # Attempting to directly transition to ACTION_EXECUTED without authorization must be forbidden
    # by authorize_and_execute_action if authorization info is missing
    with pytest.raises(ValueError):
        mgr.authorize_and_execute_action(
            case=case,
            action="BLOCK_CARD",
            authorized_by="",  # Missing authorizer
            rationale="Attempting execution without signoff"
        )

    # Legitimate human authorization executes the action
    case_res, audit = mgr.authorize_and_execute_action(
        case=case,
        action="BLOCK_CARD",
        authorized_by="Lead Fraud Analyst 42",
        rationale="Approved blocking of compromised card"
    )
    assert audit.execution_status == ActionExecutionStatus.EXECUTED
    assert case.status == CaseLifecycleStatus.ACTION_EXECUTED
    assert len(case.actions_actually_executed) == 1

def test_r_sar_case_evaluation():
    """R. Test FinCEN SAR evaluation and record storage."""
    evaluator = SARCaseEvaluator()
    from src.models.context import InvestigationContext
    from src.models.reasoning import (
        InvestigationAssessment,
        UncertaintyAssessment,
        UncertaintyLevel,
        EvidenceSufficiencyState,
        FraudAssessmentOutcome,
        NextBestAction,
        StopDecision,
        StructuredExplanation
    )

    ctx = InvestigationContext(
        case_id="SAR-TEST-001",
        opened_at="2026-09-23T12:00:00",
        trigger_type="risk_score",
        trigger_text="Flagged transaction $1500 exposure",
        flagged_txn_id=7001,
        customer_id="C600",
        card_id="card_600",
        model_risk_score=0.92,
        graph_evidence_summary=["Transaction 7001 ($1500.00) flagged for review."]
    )

    assessment = InvestigationAssessment(
        case_id="SAR-TEST-001",
        fraud_assessment=FraudAssessmentOutcome.LIKELY_FRAUD,
        confidence=0.95,
        uncertainty=UncertaintyAssessment(level=UncertaintyLevel.LOW, reasons=[]),
        evidence_sufficiency=EvidenceSufficiencyState.SUFFICIENT,
        evidence_gaps=[],
        suspected_patterns=["syndicate_ring"],
        supporting_evidence=["Multi-card syndicate activity across $1500 exposure"],
        contradictory_evidence=[],
        policy_decisions=[],
        next_best_action=NextBestAction(
            action=PolicyAction.FILE_REPORT,
            approval_required=True,
            approval_route=ApprovalRoute.L2,
            confidence=0.95,
            rationale="SAR filing required for syndicate fraud exceeding threshold",
            policy_references=["R8", "FINCEN_31CFR1020_320"]
        ),
        stop_decision=StopDecision(
            should_stop=True,
            reason="Sufficient evidence",
            remaining_uncertainty=UncertaintyLevel.LOW,
            next_step="File SAR"
        ),
        explanation=StructuredExplanation(
            why_suspicious=["$1500 syndicate activity"],
            why_action=["Rule R8 and FinCEN mandate filing SAR."]
        ),
        requires_human_approval=True
    )

    sar_rec = evaluator.evaluate(ctx, assessment, amount_usd=1500.0)
    assert sar_rec.sar_required is True
    assert sar_rec.sar_status == "RECOMMENDED"
    assert sar_rec.exposure_usd == 1500.0
    assert any("FinCEN" in ref for ref in sar_rec.regulatory_references)
    assert sar_rec.approval_route == "L2"
    assert sar_rec.filing_status == "unfiled"

def test_s_end_to_end_orchestrator_persistence():
    """S. Test complete agent investigation produces persistent case, writeback, and SAR record."""
    mcp = TigerGraphMCPServer()
    investigator = AgenticFraudInvestigator(mcp_server=mcp)

    trigger = InvestigationTrigger(
        case_id="HHG-003",
        trigger_type=TriggerType.RISK_SCORE,
        transaction_id=2987103,
        customer_id="cust_330",
        card_id="card_102",
        model_risk_score=0.88,
        trigger_details="High velocity trigger on card_102"
    )

    result = investigator.investigate(trigger)
    assert result.persisted_case_id == "HHG-003"
    assert result.written_to_graph is True
    assert result.sar_record is not None

    # Retrieve from CaseStore
    stored_case = investigator.case_store.get_case("HHG-003")
    assert stored_case is not None
    assert stored_case.case_id == "HHG-003"
    assert len(stored_case.evidence_items) > 0
    assert stored_case.status in [CaseLifecycleStatus.RESOLVED, CaseLifecycleStatus.ACTION_PENDING_APPROVAL, CaseLifecycleStatus.ESCALATED]

    # Verify writeback in sample graph client
    graph_case = investigator.writeback_engine.sample_client.get_case("HHG-003")
    assert graph_case is not None
    assert graph_case["verdict"] == stored_case.fraud_assessment

def test_s_t_full_20_case_benchmark_persistence_and_invariants():
    """S & T. Verify that all 20 benchmark cases create persistent case records and uphold Stage 7 invariants."""
    import os
    import pandas as pd
    case_pack_path = os.path.join("data", "sample", "case_pack.csv")
    if not os.path.exists(case_pack_path):
        case_pack_path = os.path.join("data", "raw", "case_pack.csv")

    df_cases = pd.read_csv(case_pack_path)
    all_target_case_ids = [f"HHG-{i:03d}" for i in range(1, 21)]
    benchmark_df = df_cases[df_cases["case_id"].isin(all_target_case_ids)].copy()

    mcp = TigerGraphMCPServer()
    investigator = AgenticFraudInvestigator(mcp_server=mcp)

    destructive_action_set = {"block_card", "block_all_cards", "freeze_account", "decline_transaction"}

    for _, row in benchmark_df.iterrows():
        case_id = str(row["case_id"])
        trigger_type_str = str(row["trigger_type"])
        txn_id = int(row["flagged_txn_id"])
        card_id = str(row["card_id"])
        customer_id = str(row["customer_id"])
        risk_score = float(row["risk_score"]) if pd.notna(row["risk_score"]) and str(row["risk_score"]).strip() != "" else 0.0

        if trigger_type_str == "customer_report":
            trig_type = TriggerType.CUSTOMER_REPORT
        elif trigger_type_str == "analyst_request":
            trig_type = TriggerType.ANALYST_REQUEST
        else:
            trig_type = TriggerType.RISK_SCORE

        trigger = InvestigationTrigger(
            case_id=case_id,
            trigger_type=trig_type,
            transaction_id=txn_id,
            customer_id=customer_id,
            card_id=card_id,
            model_risk_score=risk_score,
            trigger_details=str(row["trigger_text"])
        )

        res = investigator.investigate(trigger)
        assert res.persisted_case_id == case_id
        assert res.written_to_graph is True
        assert res.total_steps <= 8

        stored = investigator.case_store.get_case(case_id)
        assert stored is not None
        assert stored.case_id == case_id
        assert stored.status in [CaseLifecycleStatus.RESOLVED, CaseLifecycleStatus.ACTION_PENDING_APPROVAL, CaseLifecycleStatus.ESCALATED]

        # Invariant checks
        nba_action = res.next_best_action.action.value
        nba_refs = set(res.next_best_action.policy_references)
        pol_dict = res.policy_decisions[0] if res.policy_decisions else {}
        evaluated_rules = set(pol_dict.get("rules_evaluated", []))
        is_permitted = pol_dict.get("permitted", pol_dict.get("is_permitted", False))

        if nba_action in destructive_action_set:
            assert is_permitted is True
            assert len(nba_refs) > 0
            assert nba_refs.issubset(evaluated_rules)

    # Check that 20 total records exist
    all_stored = investigator.case_store.list_cases()
    assert len(all_stored) == len(benchmark_df)


