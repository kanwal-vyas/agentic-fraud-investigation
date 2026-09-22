import pytest
from src.rag.corpus import GraphRAGCorpus
from src.rag.retriever import GraphRAGRetriever
from src.rag.synthesis import InvestigationContextSynthesizer
from src.tigergraph.sample_client import SampleGraphClient
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.reasoning.engine import DeterministicReasoningEngine
from src.reasoning.evidence_evaluator import DeterministicEvidenceEvaluator
from src.reasoning.uncertainty_evaluator import UncertaintyEvaluator
from src.reasoning.sufficiency_evaluator import EvidenceSufficiencyEvaluator
from src.reasoning.evidence_planner import ControlledEvidencePlanner
from src.reasoning.policy_engine import PolicyDecisionEngine
from src.reasoning.nba_engine import NextBestActionEngine
from src.reasoning.stop_evaluator import StopConditionEvaluator
from src.reasoning.explanation_engine import ExplanationEngine
from src.models.reasoning import (
    InvestigationAssessment,
    FraudAssessmentOutcome,
    EvidenceSufficiencyState,
    UncertaintyLevel,
    NextBestAction,
    StopDecision
)
from src.core.constants import PolicyAction, ApprovalRoute

@pytest.fixture
def reasoning_setup(raw_data_dir, sample_data_dir):
    corpus = GraphRAGCorpus(data_dir=raw_data_dir)
    retriever = GraphRAGRetriever(corpus=corpus)
    sample_client = SampleGraphClient(sample_data_dir)
    tools = TigerGraphInvestigationTools(tg_client=sample_client)
    synthesizer = InvestigationContextSynthesizer(retriever=retriever, tools=tools)
    engine = DeterministicReasoningEngine()
    return synthesizer, engine

def test_assessment_model_customer_report(reasoning_setup):
    synthesizer, engine = reasoning_setup
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-001",
        opened_at="2016-12-04 19:55:28",
        trigger_type="customer_report",
        trigger_text="Cardholder reported unauthorized purchase.",
        flagged_txn_id=3514030,
        card_id="C12382-K1",
        customer_id="C12382",
        risk_score=0.61
    )

    assessment = engine.assess(ctx)
    assert isinstance(assessment, InvestigationAssessment)
    assert assessment.fraud_assessment == FraudAssessmentOutcome.LIKELY_FRAUD
    assert assessment.confidence >= 0.70
    assert assessment.next_best_action.action == PolicyAction.BLOCK_CARD
    assert assessment.next_best_action.execution_status == "recommended"
    assert assessment.requires_human_approval is True
    assert assessment.stop_decision.should_stop is True

def test_evidence_weighting_dimensions(reasoning_setup):
    synthesizer, _ = reasoning_setup
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-001",
        opened_at="2016-12-04 19:55:28",
        trigger_type="customer_report",
        trigger_text="Cardholder reported unauthorized purchase.",
        flagged_txn_id=3514030,
        card_id="C12382-K1",
        customer_id="C12382",
        risk_score=0.61
    )
    evaluator = DeterministicEvidenceEvaluator()
    factors, suspicion, confidence, patterns = evaluator.evaluate(ctx)

    assert len(factors) > 0
    assert any(f.dimension == "transaction" for f in factors)
    assert any(f.dimension == "historical" for f in factors)
    assert suspicion > 0.0
    assert confidence > 0.0

def test_uncertainty_and_contradictory_evidence(reasoning_setup):
    synthesizer, engine = reasoning_setup
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-004",
        opened_at="2016-12-29 01:53:54",
        trigger_type="analyst_request",
        trigger_text="Analyst requested secondary check.",
        flagged_txn_id=3583227,
        card_id="C08106-K1",
        customer_id="C08106",
        risk_score=0.34
    )

    assessment = engine.assess(ctx)
    assert assessment.uncertainty.level in [UncertaintyLevel.MODERATE, UncertaintyLevel.MATERIAL, UncertaintyLevel.HIGH]
    assert len(assessment.contradictory_evidence) > 0
    assert len(assessment.uncertainty.reasons) > 0

def test_evidence_sufficiency_states(reasoning_setup):
    synthesizer, engine = reasoning_setup
    
    # Case with weak risk score trigger
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-004",
        opened_at="2016-12-29 01:53:54",
        trigger_type="risk_score",
        trigger_text="Model score 0.34",
        flagged_txn_id=3583227,
        card_id="C08106-K1",
        customer_id="C08106",
        risk_score=0.34
    )
    assessment = engine.assess(ctx)
    assert assessment.evidence_sufficiency in [EvidenceSufficiencyState.INSUFFICIENT, EvidenceSufficiencyState.CONFLICTING]

def test_controlled_evidence_request_planning(reasoning_setup):
    synthesizer, engine = reasoning_setup
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-010",
        opened_at="2016-12-02 15:18:27",
        trigger_type="risk_score",
        trigger_text="High risk model score 0.90",
        flagged_txn_id=3506725,
        card_id="C10434-K1",
        customer_id="C10434",
        risk_score=0.90
    )
    requests = engine.plan_evidence(ctx)
    assert len(requests) > 0
    req_types = [r.request_type for r in requests]
    assert "customer_validation" in req_types
    # Verify ranking by expected information gain
    gains = [r.expected_information_gain for r in requests]
    assert gains == sorted(gains, reverse=True)

def test_policy_engine_rule_enforcement(reasoning_setup):
    synthesizer, _ = reasoning_setup
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-004",
        opened_at="2016-12-29 01:53:54",
        trigger_type="risk_score",
        trigger_text="Score 0.34",
        flagged_txn_id=3583227,
        card_id="C08106-K1",
        customer_id="C08106",
        risk_score=0.34
    )
    policy_engine = PolicyDecisionEngine()
    
    # Try to block card on weak uncorroborated score -> Rule R1 violation
    mock_unc = engine_eval_uncertainty()
    res = policy_engine.evaluate_policy_compliance(
        action=PolicyAction.BLOCK_CARD,
        ctx=ctx,
        assessment=FraudAssessmentOutcome.SUSPICIOUS_BUT_UNCERTAIN,
        sufficiency=EvidenceSufficiencyState.INSUFFICIENT,
        uncertainty=mock_unc
    )
    assert res["is_permitted"] is False
    assert len(res["violations"]) > 0
    assert any("Rule R1" in v for v in res["violations"])

def engine_eval_uncertainty():
    from src.models.reasoning import UncertaintyAssessment, UncertaintyLevel
    return UncertaintyAssessment(level=UncertaintyLevel.MATERIAL, reasons=["Customer unverified"])

def test_recommendation_vs_execution_separation(reasoning_setup):
    synthesizer, engine = reasoning_setup
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-001",
        opened_at="2016-12-04 19:55:28",
        trigger_type="customer_report",
        trigger_text="Unauthorized purchase",
        flagged_txn_id=3514030,
        card_id="C12382-K1",
        customer_id="C12382",
        risk_score=0.61
    )
    nba = engine.recommend_action(ctx)
    assert nba.action == PolicyAction.BLOCK_CARD
    assert nba.execution_status == "recommended"  # Never auto-executed!
    assert nba.approval_required is True

def test_reassessment_with_additional_evidence(reasoning_setup):
    synthesizer, engine = reasoning_setup
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-004",
        opened_at="2016-12-29 01:53:54",
        trigger_type="analyst_request",
        trigger_text="Review requested",
        flagged_txn_id=3583227,
        card_id="C08106-K1",
        customer_id="C08106",
        risk_score=0.34
    )
    
    # Initial Assessment: Suspicious / Uncertain
    init = engine.assess(ctx)
    assert init.fraud_assessment == FraudAssessmentOutcome.SUSPICIOUS_BUT_UNCERTAIN

    # Supply Customer Confirmation Evidence
    reassessed = engine.reassess_with_additional_evidence(
        ctx,
        additional_evidence={"customer_response": "confirmed"}
    )
    assert reassessed.fraud_assessment == FraudAssessmentOutcome.LIKELY_BENIGN
    assert reassessed.next_best_action.action == PolicyAction.CLOSE_NO_FRAUD
    assert reassessed.stop_decision.should_stop is True

def test_explanation_engine_structure(reasoning_setup):
    synthesizer, engine = reasoning_setup
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-010",
        opened_at="2016-12-02 15:18:27",
        trigger_type="risk_score",
        trigger_text="Model 0.90",
        flagged_txn_id=3506725,
        card_id="C10434-K1",
        customer_id="C10434",
        risk_score=0.90
    )
    assessment = engine.assess(ctx)
    exp = assessment.explanation
    assert len(exp.why_suspicious) > 0
    assert len(exp.why_not_certain) > 0
    assert len(exp.why_request_more_evidence) > 0
    assert len(exp.why_action) > 0
    assert len(exp.why_stop) > 0
