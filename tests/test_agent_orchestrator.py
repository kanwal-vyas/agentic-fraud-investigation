import pytest
from src.models.agent import (
    InvestigationTrigger,
    TriggerType,
    AgentActionType,
    AgentToolCallDecision,
    WorkingInvestigationState
)
from src.agent.provider import MockLLMProvider, LLMProvider
from src.agent.planner import AgentPlanner
from src.agent.orchestrator import AgenticFraudInvestigator
from src.mcp.server import TigerGraphMCPServer
from src.rag.synthesis import InvestigationContextSynthesizer
from src.reasoning.engine import DeterministicReasoningEngine

@pytest.fixture
def mcp_server():
    return TigerGraphMCPServer()

@pytest.fixture
def synthesizer():
    return InvestigationContextSynthesizer()

@pytest.fixture
def reasoning_engine():
    return DeterministicReasoningEngine()

@pytest.fixture
def investigator(mcp_server, synthesizer, reasoning_engine):
    return AgenticFraudInvestigator(
        mcp_server=mcp_server,
        synthesizer=synthesizer,
        reasoning_engine=reasoning_engine,
        max_steps=8
    )

def test_trigger_ingestion_and_types():
    """Verify that all trigger modalities are properly ingested into InvestigationTrigger."""
    trig_risk = InvestigationTrigger(
        case_id="HHG-001",
        trigger_type=TriggerType.RISK_SCORE,
        transaction_id=3514030,
        customer_id="C12382",
        card_id="C12382-K1",
        model_risk_score=0.61,
        trigger_details="Real-time model scored 0.61"
    )
    assert trig_risk.trigger_type == TriggerType.RISK_SCORE
    assert trig_risk.transaction_id == 3514030

    trig_cust = InvestigationTrigger(
        case_id="HHG-003",
        trigger_type=TriggerType.CUSTOMER_REPORT,
        transaction_id=3530164,
        customer_id="C08623",
        card_id="C08623-K2",
        trigger_details="Customer reported unauthorized charge"
    )
    assert trig_cust.trigger_type == TriggerType.CUSTOMER_REPORT

    trig_analyst = InvestigationTrigger(
        case_id="HHG-014",
        trigger_type=TriggerType.ANALYST_REQUEST,
        transaction_id=3478561,
        customer_id="C13487",
        card_id="C13487-K1",
        trigger_details="Analyst requested device review"
    )
    assert trig_analyst.trigger_type == TriggerType.ANALYST_REQUEST


def test_dynamic_tool_selection():
    """Verify that MockLLMProvider dynamically selects appropriate tools based on trigger type."""
    planner = AgentPlanner(MockLLMProvider())

    # State 1: Fresh customer report
    trig_cust = InvestigationTrigger(
        case_id="HHG-003",
        trigger_type=TriggerType.CUSTOMER_REPORT,
        transaction_id=3530164,
        customer_id="C08623",
        card_id="C08623-K2"
    )
    state1 = WorkingInvestigationState(trigger=trig_cust)
    dec1 = planner.decide_next_step(state1)
    assert dec1.action == AgentActionType.CALL_TOOL
    assert dec1.tool == "get_transaction"

    # State 2: Transaction collected, customer report should proceed to card history
    state2 = WorkingInvestigationState(
        trigger=trig_cust,
        tools_called=["get_transaction"],
        collected_evidence=[{
            "tool": "get_transaction",
            "status": "success",
            "subject": {"profile_id": "P_ANDROID_01", "channel": "online"}
        }]
    )
    dec2 = planner.decide_next_step(state2)
    assert dec2.action == AgentActionType.CALL_TOOL
    assert dec2.tool == "get_card_history"


def test_invalid_tool_rejection_and_schema_validation():
    """Verify that AgentPlanner intercepts and rejects unknown or unregistered tools."""
    class MaliciousProvider(LLMProvider):
        def plan_next_action(self, state, available_tools):
            return AgentToolCallDecision(
                action=AgentActionType.CALL_TOOL,
                tool="execute_arbitrary_shell_command",
                arguments={"cmd": "rm -rf /"},
                reason="Unrestricted execution attempt"
            )

    malicious_planner = AgentPlanner(MaliciousProvider())
    trig = InvestigationTrigger(
        case_id="HHG-001",
        trigger_type=TriggerType.RISK_SCORE,
        transaction_id=3514030,
        customer_id="C12382",
        card_id="C12382-K1"
    )
    state = WorkingInvestigationState(trigger=trig)
    dec = malicious_planner.decide_next_step(state)

    # Must be intercepted and defaulted to safe ASSESS action
    assert dec.action == AgentActionType.ASSESS
    assert "Invalid decision intercepted" in dec.reason


def test_duplicate_tool_call_suppression():
    """Verify that AgentPlanner prevents executing the same tool twice."""
    class DuplicateProvider(LLMProvider):
        def plan_next_action(self, state, available_tools):
            return AgentToolCallDecision(
                action=AgentActionType.CALL_TOOL,
                tool="get_transaction",
                arguments={"txn_id": "3514030"},
                reason="Redundant query"
            )

    dup_planner = AgentPlanner(DuplicateProvider())
    trig = InvestigationTrigger(
        case_id="HHG-001",
        trigger_type=TriggerType.RISK_SCORE,
        transaction_id=3514030,
        customer_id="C12382",
        card_id="C12382-K1"
    )
    state = WorkingInvestigationState(
        trigger=trig,
        tools_called=["get_transaction"]
    )
    dec = dup_planner.decide_next_step(state)
    assert dec.action == AgentActionType.ASSESS
    assert "Duplicate tool call suppressed" in dec.reason


def test_working_memory_and_investigation_trace(investigator):
    """Verify that each investigation step is properly recorded in working state with complete trace."""
    trigger = InvestigationTrigger(
        case_id="HHG-003",
        trigger_type=TriggerType.CUSTOMER_REPORT,
        transaction_id=3530164,
        customer_id="C08623",
        card_id="C08623-K2",
        trigger_details="Customer reported charge"
    )
    result = investigator.investigate(trigger)

    assert len(result.investigation_steps) > 0
    step1 = result.investigation_steps[0]
    assert step1.step_number == 1
    assert step1.tool == "get_transaction"
    assert step1.outcome == "success"
    assert len(step1.evidence_ids) > 0
    assert step1.reason != ""
    assert result.total_tool_calls == len(result.investigation_steps)


def test_bounded_loop_termination(mcp_server, synthesizer, reasoning_engine):
    """Verify that the investigation loop never exceeds max_steps."""
    class EndlessProvider(LLMProvider):
        def __init__(self):
            self.tools = ["get_transaction", "get_card_history", "detect_velocity", "find_shared_devices", "get_historical_cases"]
            self.idx = 0
        def plan_next_action(self, state, available_tools):
            tool = self.tools[self.idx % len(self.tools)]
            self.idx += 1
            return AgentToolCallDecision(
                action=AgentActionType.CALL_TOOL,
                tool=tool,
                arguments={"txn_id": "3514030", "card_id": "C12382-K1"},
                reason="Loop test"
            )

    planner = AgentPlanner(EndlessProvider())
    investigator = AgenticFraudInvestigator(
        mcp_server=mcp_server,
        synthesizer=synthesizer,
        reasoning_engine=reasoning_engine,
        planner=planner,
        max_steps=5
    )

    trig = InvestigationTrigger(
        case_id="HHG-001",
        trigger_type=TriggerType.RISK_SCORE,
        transaction_id=3514030,
        customer_id="C12382",
        card_id="C12382-K1"
    )
    res = investigator.investigate(trig)
    assert res.total_steps <= 5


def test_reasoning_checkpoints_progression(investigator):
    """Verify that intermediate checkpoints are captured after each meaningful tool call."""
    trigger = InvestigationTrigger(
        case_id="HHG-005",
        trigger_type=TriggerType.RISK_SCORE,
        transaction_id=3523199,
        customer_id="C02923",
        card_id="C02923-K1",
        model_risk_score=0.54,
        trigger_details="Model risk score 0.54"
    )
    result = investigator.investigate(trigger)
    assert len(result.assessment_history) >= 2
    for checkpoint in result.assessment_history:
        assert checkpoint.case_id == "HHG-005"
        assert checkpoint.confidence >= 0.0
        assert checkpoint.uncertainty.level is not None


def test_reassessment_pipeline(investigator):
    """Verify that supplying simulated customer response updates assessment from uncertain to confirmed state."""
    trigger = InvestigationTrigger(
        case_id="HHG-005",
        trigger_type=TriggerType.RISK_SCORE,
        transaction_id=3523199,
        customer_id="C02923",
        card_id="C02923-K1",
        model_risk_score=0.54,
        trigger_details="Model risk score 0.54"
    )
    # Reassess with customer confirmation
    result = investigator.investigate(
        trigger,
        simulated_evidence_response={"customer_response": "confirmed"}
    )
    assert result.final_assessment.fraud_assessment.value == "likely_benign"
    from src.core.constants import PolicyAction
    assert result.next_best_action.action == PolicyAction.CLOSE_NO_FRAUD


def test_recommendation_vs_execution_separation(investigator):
    """Verify that investigator produces recommendations and never directly executes destructive side effects."""
    trigger = InvestigationTrigger(
        case_id="HHG-003",
        trigger_type=TriggerType.CUSTOMER_REPORT,
        transaction_id=3530164,
        customer_id="C08623",
        card_id="C08623-K2",
        trigger_details="Customer reported unauthorized charge"
    )
    result = investigator.investigate(trigger)
    assert result.execution_status == "recommended"
    assert result.next_best_action.execution_status == "recommended"
    assert result.approval_required is True
    assert result.approval_route.value == "L1"


def test_complete_end_to_end_investigation(investigator):
    """Verify end-to-end investigation output format and explanation integrity."""
    trigger = InvestigationTrigger(
        case_id="HHG-001",
        trigger_type=TriggerType.RISK_SCORE,
        transaction_id=3514030,
        customer_id="C12382",
        card_id="C12382-K1",
        model_risk_score=0.61,
        trigger_details="Real-time model scored 0.61"
    )
    result = investigator.investigate(trigger)

    assert result.case_id == "HHG-001"
    assert len(result.investigation_steps) >= 2
    assert result.final_assessment is not None
    assert len(result.explanation.why_suspicious) > 0
    assert len(result.explanation.why_action) > 0
    assert result.stop_decision.should_stop is not None
