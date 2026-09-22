from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class MCPToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

MCP_INVESTIGATION_TOOLS: List[MCPToolDefinition] = [
    MCPToolDefinition(
        name="get_transaction",
        description=(
            "Retrieve complete attributes, input model risk score, amount, timestamp, channel, and connected entity links "
            "(card, customer, device profile, billing region, email domain) for a specific transaction ID. "
            "Note: model_risk_score is an input signal (0.0 to 1.0) from the detection model, NOT a ground-truth verdict."
        ),
        parameters={
            "type": "object",
            "properties": {
                "txn_id": {
                    "type": "string",
                    "description": "The unique transaction ID string (e.g. '3514030', '3478782')"
                }
            },
            "required": ["txn_id"]
        }
    ),
    MCPToolDefinition(
        name="get_customer_history",
        description=(
            "Retrieve transaction summary and recent activity timeline for a customer ID (e.g. 'C12382'). "
            "Returns total spend, average transaction amount, list of held cards, device profiles used, and recent transactions. "
            "Use this to understand the cardholder's historical spending baseline."
        ),
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer ID string (e.g. 'C12382', 'C11891')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of recent transactions to return (default: 50)",
                    "default": 50
                }
            },
            "required": ["customer_id"]
        }
    ),
    MCPToolDefinition(
        name="get_card_history",
        description=(
            "Retrieve card metadata (network, type, issuer) and historical transaction sequence for a specific card_id (e.g. 'C12382-K1'). "
            "Provides transaction count, total volume, average amount, max amount, and chronological transaction records. "
            "Crucial for establishing card-level normal velocity and baseline amounts."
        ),
        parameters={
            "type": "object",
            "properties": {
                "card_id": {
                    "type": "string",
                    "description": "The card ID string (e.g. 'C12382-K1', 'C09933-K2')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of transactions to return (default: 50)",
                    "default": 50
                }
            },
            "required": ["card_id"]
        }
    ),
    MCPToolDefinition(
        name="get_transaction_neighborhood",
        description=(
            "Traverse the graph ego-network around a transaction up to max_hops (1-hop or 2-hop). "
            "Returns connected nodes (Transaction, Card, Customer, DeviceProfile, BillingRegion, EmailDomain) and edges. "
            "Use this to visualize graph connectivity and extract multi-hop relational context."
        ),
        parameters={
            "type": "object",
            "properties": {
                "txn_id": {
                    "type": "string",
                    "description": "The transaction ID (e.g. '3514030')"
                },
                "max_hops": {
                    "type": "integer",
                    "description": "Graph traversal depth: 1 or 2 (default: 2)",
                    "default": 2
                }
            },
            "required": ["txn_id"]
        }
    ),
    MCPToolDefinition(
        name="find_shared_devices",
        description=(
            "Analyze a composite DeviceProfile string ('DeviceInfo | OS | Browser | Screen') to determine if it is shared "
            "across multiple distinct cards or customers. Returns connected card IDs, customer IDs, and transaction count. "
            "Critical for detecting coordinated fraud syndicates and multi-account compromises (Policy Rule R6)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "profile_id": {
                    "type": "string",
                    "description": "The composite DeviceProfile string identifier"
                }
            },
            "required": ["profile_id"]
        }
    ),
    MCPToolDefinition(
        name="detect_card_testing",
        description=(
            "Analyze a card's timeline for characteristic 'card_testing' patterns: ≥3 online micro-authorizations (≤ $5.00) "
            "in a tight window followed by larger authorizations (≥ $50.00). "
            "Returns whether testing was detected, micro-auth transactions, subsequent large purchases, and heuristic confidence. "
            "Heuristic confidence is an evidence metric, not an automated verdict (Policy Rule R5)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "card_id": {
                    "type": "string",
                    "description": "The card ID to evaluate (e.g. 'C12382-K1')"
                },
                "window_hours": {
                    "type": "integer",
                    "description": "Time window in hours to check for testing bursts (default: 24)",
                    "default": 24
                }
            },
            "required": ["card_id"]
        }
    ),
    MCPToolDefinition(
        name="detect_velocity",
        description=(
            "Assess velocity spikes and rapid transaction clustering on a card. "
            "Computes total transaction count, total spend, average amount, and rapid cluster metrics over a given time window. "
            "Use this to identify sudden spending acceleration indicative of card-not-present bursts."
        ),
        parameters={
            "type": "object",
            "properties": {
                "card_id": {
                    "type": "string",
                    "description": "The card ID to evaluate (e.g. 'C12382-K1')"
                },
                "window_hours": {
                    "type": "number",
                    "description": "Velocity evaluation window in hours (default: 48.0)",
                    "default": 48.0
                }
            },
            "required": ["card_id"]
        }
    ),
    MCPToolDefinition(
        name="detect_regional_anomaly",
        description=(
            "Determine if a transaction's billing region ('addr1') deviates significantly from the cardholder's established home region baseline. "
            "Returns current region, historical home region, prior home transactions count, and heuristic confidence. "
            "Applies primarily to in-person transactions where geographic discordance indicates potential cloning or travel."
        ),
        parameters={
            "type": "object",
            "properties": {
                "txn_id": {
                    "type": "string",
                    "description": "The transaction ID to check for regional discordance"
                }
            },
            "required": ["txn_id"]
        }
    ),
    MCPToolDefinition(
        name="get_historical_cases",
        description=(
            "Query the case memory repository for past resolved investigations (closed July-October 2016) matching a customer, card, or pattern. "
            "Returns past case IDs, outcomes ('confirmed_fraud' or 'cleared'), fraud patterns, exposure, and rich analyst notes. "
            "Grounds agent reasoning in historical bank precedent."
        ),
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Optional customer ID to look up prior investigations for"
                },
                "card_id": {
                    "type": "string",
                    "description": "Optional card ID to look up prior investigations for"
                },
                "pattern": {
                    "type": "string",
                    "description": "Optional fraud pattern to match (e.g. 'card_testing', 'out_of_region_use')"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of matching historical cases to retrieve (default: 5)",
                    "default": 5
                }
            }
        }
    ),
    MCPToolDefinition(
        name="find_connected_cards",
        description=(
            "Discover all cards connected to a target card through shared customer ownership or shared device profiles. "
            "Returns connected card IDs, connection reasons, and shared device profiles. "
            "Essential for placing secondary cards under monitoring (Policy Rule R6)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "card_id": {
                    "type": "string",
                    "description": "The primary card ID to explore connections from"
                }
            },
            "required": ["card_id"]
        }
    )
]
