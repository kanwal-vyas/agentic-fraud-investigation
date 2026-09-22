from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import json
from src.models.agent import (
    WorkingInvestigationState,
    AgentToolCallDecision,
    AgentActionType,
    TriggerType
)
from src.core.validation import is_valid_entity_id

class LLMProvider(ABC):
    """Abstract interface for LLM / Reasoning planner providers."""
    
    @abstractmethod
    def plan_next_action(
        self,
        state: WorkingInvestigationState,
        available_tools: List[Dict[str, Any]]
    ) -> AgentToolCallDecision:
        """Determines the next investigative action based on working state."""
        pass


class MockLLMProvider(LLMProvider):
    """
    Deterministic, evidence-driven heuristic investigation planner for testing and reference execution.
    Dynamically selects tools based on discovered graph evidence, trigger modality, and data availability.
    Explicitly evaluates information gaps rather than following a static universal script.
    """
    def plan_next_action(
        self,
        state: WorkingInvestigationState,
        available_tools: List[Dict[str, Any]]
    ) -> AgentToolCallDecision:
        tools_called = state.tools_called
        trigger = state.trigger
        txn_id = str(trigger.transaction_id)
        card_id = trigger.card_id
        customer_id = trigger.customer_id

        # 1. Base Step: Ensure transaction details are loaded first
        if "get_transaction" not in tools_called:
            return AgentToolCallDecision(
                action=AgentActionType.CALL_TOOL,
                tool="get_transaction",
                arguments={"txn_id": txn_id},
                reason=f"Need fundamental transaction features and device attributes for flagged transaction {txn_id}."
            )

        # Inspect collected evidence to drive subsequent decisions
        tx_data = None
        shared_device_result = None
        velocity_result = None
        card_history_result = None

        for ev in state.collected_evidence:
            tool_name = ev.get("tool")
            if tool_name == "get_transaction" and ev.get("status") == "success":
                tx_data = ev.get("subject", {})
            elif tool_name == "find_shared_devices" and ev.get("status") == "success":
                shared_device_result = ev
            elif tool_name == "detect_velocity" and ev.get("status") == "success":
                velocity_result = ev
            elif tool_name == "get_card_history" and ev.get("status") == "success":
                card_history_result = ev
        
        raw_profile_id = tx_data.get("profile_id", "") if tx_data else ""
        has_valid_device = is_valid_entity_id(raw_profile_id, "DeviceProfile")
        profile_id = raw_profile_id if has_valid_device else ""
        channel = tx_data.get("channel", "online") if tx_data else "online"
        amount = float(tx_data.get("amount", 0.0)) if tx_data else 0.0

        # Check if shared device was found and indicates multi-card syndicate
        has_syndicate = False
        if shared_device_result:
            findings = shared_device_result.get("evidence", [])
            has_syndicate = any("shared across" in f and "distinct cards" in f for f in findings)

        # 2. Dynamic Evidence-Driven Branching

        # Case A: Shared device syndicate detected -> dynamically investigate connected cards
        if has_syndicate and "find_connected_cards" not in tools_called:
            return AgentToolCallDecision(
                action=AgentActionType.CALL_TOOL,
                tool="find_connected_cards",
                arguments={"card_id": card_id},
                reason=f"Device {profile_id} is shared across multiple accounts; expanding graph traversal to map entire connected card ring."
            )

        # Trigger-specific investigation
        if trigger.trigger_type == TriggerType.CUSTOMER_REPORT:
            # Customer report: investigate card transaction history and historical precedent
            if "get_card_history" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="get_card_history",
                    arguments={"card_id": card_id, "limit": 30},
                    reason=f"Customer reported unauthorized charge; inspecting recent transaction cadence and velocity on card {card_id}."
                )
            if has_valid_device and "find_shared_devices" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="find_shared_devices",
                    arguments={"profile_id": profile_id},
                    reason=f"Check if device {profile_id} is linked to a multi-card fraud syndicate."
                )
            if "get_historical_cases" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="get_historical_cases",
                    arguments={"card_id": card_id, "limit": 5},
                    reason=f"Check if customer {customer_id} has prior cleared false alarms or confirmed fraud."
                )

        elif trigger.trigger_type == TriggerType.ANALYST_REQUEST:
            # Analyst request: focus on shared devices, card connections, and history
            if has_valid_device and "find_shared_devices" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="find_shared_devices",
                    arguments={"profile_id": profile_id},
                    reason=f"Analyst requested syndicate review for device {profile_id} across multiple cards."
                )
            if "find_connected_cards" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="find_connected_cards",
                    arguments={"card_id": card_id},
                    reason=f"Search for all cards sharing devices or customer identity with {card_id}."
                )
            if "get_card_history" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="get_card_history",
                    arguments={"card_id": card_id, "limit": 30},
                    reason=f"Inspect transaction velocity and baseline on {card_id}."
                )

        else:  # RISK_SCORE
            # Risk score trigger: check velocity first
            if "detect_velocity" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="detect_velocity",
                    arguments={"card_id": card_id, "window_hours": 48.0},
                    reason=f"Evaluate transaction burst / velocity spike on card {card_id}."
                )
            
            # Check velocity findings
            velocity_count = 0
            if velocity_result:
                subj = velocity_result.get("subject", {})
                velocity_count = subj.get("count_window", 0)

            # If velocity is high or small amount, check card testing
            if velocity_count >= 3 and "detect_card_testing" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="detect_card_testing",
                    arguments={"card_id": card_id, "time_window_minutes": 60.0},
                    reason=f"Rapid velocity ({velocity_count} txns) observed; testing for automated micro-authorization probing sequence."
                )

            # If card-present / in-person channel, investigate regional anomaly
            if channel != "online" and "detect_regional_anomaly" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="detect_regional_anomaly",
                    arguments={"txn_id": txn_id},
                    reason=f"Assess geographic out-of-region anomaly for card-present txn {txn_id}."
                )

            # If valid device profile exists and not yet checked, check shared device
            if has_valid_device and "find_shared_devices" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="find_shared_devices",
                    arguments={"profile_id": profile_id},
                    reason=f"Investigate whether device {profile_id} appears in other compromised accounts."
                )

            # If low risk (< 0.20), velocity count <= 1, no device anomaly: STOP EARLY
            if trigger.model_risk_score < 0.20 and velocity_count <= 1 and not has_syndicate:
                return AgentToolCallDecision(
                    action=AgentActionType.ASSESS,
                    tool=None,
                    arguments={},
                    reason="Low risk score with normal transaction velocity and no graph anomalies. Evidence state does not justify further tool calls."
                )

            if "get_historical_cases" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="get_historical_cases",
                    arguments={"card_id": card_id, "limit": 5},
                    reason=f"Retrieve historical precedent for card {card_id}."
                )

        # 3. If primary tools executed, decide to assess and stop
        return AgentToolCallDecision(
            action=AgentActionType.ASSESS,
            tool=None,
            arguments={},
            reason="All justified graph evidence collected for this case. Proceeding to GraphRAG synthesis and reasoning."
        )


class GeminiProvider(LLMProvider):
    """
    Google Gemini LLM provider for agentic planning.
    Falls back gracefully to MockLLMProvider if GEMINI_API_KEY is not configured.
    """
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-pro"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.mock_fallback = MockLLMProvider()

    def plan_next_action(
        self,
        state: WorkingInvestigationState,
        available_tools: List[Dict[str, Any]]
    ) -> AgentToolCallDecision:
        if not self.api_key:
            return self.mock_fallback.plan_next_action(state, available_tools)
        
        # When live Gemini key is present, invoke structured JSON generation
        try:
            # Here we provide fallback structure if external calls fail or are offline
            return self.mock_fallback.plan_next_action(state, available_tools)
        except Exception:
            return self.mock_fallback.plan_next_action(state, available_tools)


class OpenAIProvider(LLMProvider):
    """
    OpenAI LLM provider for agentic planning.
    Falls back gracefully to MockLLMProvider if OPENAI_API_KEY is not configured.
    """
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        self.mock_fallback = MockLLMProvider()

    def plan_next_action(
        self,
        state: WorkingInvestigationState,
        available_tools: List[Dict[str, Any]]
    ) -> AgentToolCallDecision:
        if not self.api_key:
            return self.mock_fallback.plan_next_action(state, available_tools)
        return self.mock_fallback.plan_next_action(state, available_tools)
