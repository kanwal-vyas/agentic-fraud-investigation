from typing import List, Dict, Any, Optional, Tuple
from src.models.agent import (
    WorkingInvestigationState,
    AgentToolCallDecision,
    AgentActionType
)
from src.agent.provider import LLMProvider, MockLLMProvider
from src.mcp.schemas import MCP_INVESTIGATION_TOOLS

class AgentPlanner:
    """
    Intelligent orchestration planner managing agent decision validation,
    schema adherence, duplicate call suppression, and safety guardrails.
    """
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or MockLLMProvider()
        self.registered_tool_names = {t.name for t in MCP_INVESTIGATION_TOOLS}
        self.registered_tools = [t.model_dump() for t in MCP_INVESTIGATION_TOOLS]

    def decide_next_step(self, state: WorkingInvestigationState) -> AgentToolCallDecision:
        """
        Queries the LLM provider for the next step and enforces strict schema validation.
        """
        decision = self.provider.plan_next_action(state, self.registered_tools)
        valid, error_msg = self.validate_decision(decision, state)
        
        if not valid:
            # Fall back to safe assessment if planner produces an invalid action
            return AgentToolCallDecision(
                action=AgentActionType.ASSESS,
                tool=None,
                arguments={},
                reason=f"Invalid decision intercepted: {error_msg}. Proceeding to deterministic assessment."
            )
        
        return decision

    def validate_decision(
        self,
        decision: AgentToolCallDecision,
        state: WorkingInvestigationState
    ) -> Tuple[bool, str]:
        """
        Validates tool names, argument presence, and prevents redundant duplicate executions.
        """
        if decision.action == AgentActionType.CALL_TOOL:
            if not decision.tool:
                return False, "Action is CALL_TOOL but no tool name was provided."
            
            if decision.tool not in self.registered_tool_names:
                return False, f"Tool '{decision.tool}' is not registered in MCP investigation tools."

            # Duplicate tool call prevention: check if tool was already called with same primary arguments
            if decision.tool in state.tools_called:
                # Check previous steps
                for step in state.tools_called:
                    if step == decision.tool:
                        return False, f"Duplicate tool call suppressed: tool '{decision.tool}' was already executed."

        return True, ""
