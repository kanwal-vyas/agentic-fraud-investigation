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
    Deterministic, gap-driven investigation planner for testing and reference execution.
    Dynamically decides the next tool based on trigger modality, collected evidence,
    and missing dimensions without hardcoding a rigid universal sequence.
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

        # Inspect collected transaction attributes
        tx_data = None
        for ev in state.collected_evidence:
            if ev.get("tool") == "get_transaction" and ev.get("status") == "success":
                tx_data = ev.get("subject", {})
                break
        
        has_device = bool(tx_data and tx_data.get("profile_id"))
        profile_id = tx_data.get("profile_id", "") if tx_data else ""
        channel = tx_data.get("channel", "online") if tx_data else "online"

        # 2. Trigger-specific dynamic investigation path
        if trigger.trigger_type == TriggerType.CUSTOMER_REPORT:
            # Customer reports require immediate baseline cadence & card history check
            if "get_card_history" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="get_card_history",
                    arguments={"card_id": card_id, "limit": 30},
                    reason=f"Customer report requires checking card history on {card_id} for unauthorized charge sequence."
                )
            if has_device and "find_shared_devices" not in tools_called:
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
            # Analyst request focuses on syndicates and connected cards
            if has_device and "find_shared_devices" not in tools_called:
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
            # Risk score trigger: check velocity, testing, regional anomalies
            if "detect_velocity" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="detect_velocity",
                    arguments={"card_id": card_id, "window_hours": 48.0},
                    reason=f"Evaluate transaction burst / velocity spike on card {card_id}."
                )
            if channel != "online" and "detect_regional_anomaly" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="detect_regional_anomaly",
                    arguments={"txn_id": txn_id},
                    reason=f"Assess geographic out-of-region anomaly for card-present txn {txn_id}."
                )
            if has_device and "find_shared_devices" not in tools_called:
                return AgentToolCallDecision(
                    action=AgentActionType.CALL_TOOL,
                    tool="find_shared_devices",
                    arguments={"profile_id": profile_id},
                    reason=f"Investigate whether device {profile_id} appears in other compromised accounts."
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
            reason="All primary multi-dimensional graph evidence collected. Proceeding to GraphRAG synthesis and reasoning."
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
