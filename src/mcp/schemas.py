from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class MCPToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

MCP_TOOLS: List[MCPToolDefinition] = [
    MCPToolDefinition(
        name="get_transaction",
        description="Retrieve complete attributes, risk score, amount, timestamp, channel, and device links for a transaction ID.",
        parameters={
            "type": "object",
            "properties": {
                "txn_id": {"type": "string", "description": "The transaction ID (e.g. '3514030')"}
            },
            "required": ["txn_id"]
        }
    ),
    MCPToolDefinition(
        name="get_card_history",
        description="Retrieve historical transaction timeline, recent amounts, channels, and velocity for a specific card_id.",
        parameters={
            "type": "object",
            "properties": {
                "card_id": {"type": "string", "description": "The card identifier (e.g. 'C12382-K1')"},
                "limit": {"type": "integer", "description": "Max number of recent transactions to return", "default": 50}
            },
            "required": ["card_id"]
        }
    ),
    MCPToolDefinition(
        name="get_customer_profile",
        description="Retrieve customer metadata, all held cards, and aggregate historical transaction volume.",
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID (e.g. 'C12382')"}
            },
            "required": ["customer_id"]
        }
    ),
    MCPToolDefinition(
        name="get_device_connections",
        description="Retrieve all cards, customers, and transactions sharing the specified DeviceProfile.",
        parameters={
            "type": "object",
            "properties": {
                "profile_id": {"type": "string", "description": "The composite DeviceProfile string identifier"}
            },
            "required": ["profile_id"]
        }
    ),
    MCPToolDefinition(
        name="find_shared_device_rings",
        description="Identify fraud rings and syndicates by finding device profiles used across multiple distinct customers.",
        parameters={
            "type": "object",
            "properties": {
                "min_cards": {"type": "integer", "description": "Minimum number of connected cards to flag as a ring", "default": 2}
            }
        }
    ),
    MCPToolDefinition(
        name="find_similar_historical_cases",
        description="Retrieve past closed investigations from case memory matching a customer, card, device, or fraud pattern.",
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Optional customer ID to check history for"},
                "card_id": {"type": "string", "description": "Optional card ID to check history for"},
                "pattern": {"type": "string", "description": "Optional fraud pattern to match"},
                "top_k": {"type": "integer", "description": "Number of similar cases to retrieve", "default": 5}
            }
        }
    ),
    MCPToolDefinition(
        name="write_case_to_graph",
        description="Persist an internal investigation case vertex and connect edges to subject transactions and cards in TigerGraph.",
        parameters={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case identifier (e.g. 'HHG-001')"},
                "status": {"type": "string", "description": "Case status ('open', 'closed_fraud', 'closed_legitimate', 'escalated')"},
                "verdict": {"type": "string", "description": "Verdict ('fraud', 'legitimate', 'uncertain')"},
                "fraud_probability": {"type": "number", "description": "Calibrated probability 0.0 to 1.0"},
                "pattern": {"type": "string", "description": "Identified fraud pattern"},
                "exposure_usd": {"type": "number", "description": "Total USD exposure"},
                "summary": {"type": "string", "description": "Analyst-readable case summary"},
                "card_id": {"type": "string", "description": "Associated card ID"},
                "affected_txn_ids": {"type": "array", "items": {"type": "string"}, "description": "List of affected transaction IDs"}
            },
            "required": ["case_id", "status", "verdict", "fraud_probability", "pattern", "exposure_usd", "summary", "card_id"]
        }
    )
]
