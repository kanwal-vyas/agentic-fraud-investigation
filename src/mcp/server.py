import json
from typing import Dict, Any, List, Optional
from src.mcp.schemas import MCP_INVESTIGATION_TOOLS, MCPToolDefinition
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.tigergraph.client import TigerGraphClient

class TigerGraphMCPServer:
    """
    Model Context Protocol (MCP) server for TigerGraph Agentic Fraud Investigation tools.
    Exposes read-only graph investigation capabilities to the AI agent with strict typing,
    compact evidence synthesis, and structured error handling.
    """
    def __init__(self, investigation_tools: Optional[TigerGraphInvestigationTools] = None):
        self.tools = investigation_tools or TigerGraphInvestigationTools()

    def get_server_status(self) -> Dict[str, Any]:
        """Returns the active backend and server health status."""
        backend_type = "tigergraph_live" if self.tools.is_live() else "offline_sample"
        return {
            "status": "online",
            "backend": backend_type,
            "is_live_tigergraph": self.tools.is_live(),
            "tools_registered": len(MCP_INVESTIGATION_TOOLS),
            "tool_names": [t.name for t in MCP_INVESTIGATION_TOOLS],
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns the definitions of all available investigation tools."""
        return [tool.model_dump() for tool in MCP_INVESTIGATION_TOOLS]

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes an MCP investigation tool call and returns compact, agent-friendly evidence.
        """
        args = arguments or {}
        backend_type = "tigergraph_live" if self.tools.is_live() else "offline_sample"

        handler_name = f"handle_{name}"
        handler = getattr(self, handler_name, None)
        if not handler:
            return {
                "tool": name,
                "status": "error",
                "backend": backend_type,
                "error": f"Unknown tool '{name}'. Available tools: {[t.name for t in MCP_INVESTIGATION_TOOLS]}",
                "subject": {},
                "evidence": [],
                "metrics": {},
                "limitations": []
            }

        try:
            return handler(args, backend_type)
        except Exception as e:
            return {
                "tool": name,
                "status": "error",
                "backend": backend_type,
                "error": f"Tool execution failed: {str(e)}",
                "subject": args,
                "evidence": [],
                "metrics": {},
                "limitations": ["Unexpected server exception occurred during execution."]
            }

    # -------------------------------------------------------------
    # Tool Handlers
    # -------------------------------------------------------------

    def handle_get_transaction(self, args: Dict[str, Any], backend: str) -> Dict[str, Any]:
        txn_id = str(args.get("txn_id", "")).strip()
        if not txn_id:
            return {
                "tool": "get_transaction",
                "status": "error",
                "backend": backend,
                "error": "Missing required argument 'txn_id'",
                "subject": {},
                "evidence": [],
                "metrics": {},
                "limitations": []
            }

        tx = self.tools.get_transaction(txn_id)
        if not tx:
            return {
                "tool": "get_transaction",
                "status": "not_found",
                "backend": backend,
                "subject": {"txn_id": txn_id},
                "evidence": [f"Transaction ID {txn_id} does not exist in graph."],
                "metrics": {},
                "limitations": ["Entity not found in graph database."]
            }

        evidence = [
            f"Transaction {tx.txn_id} for ${tx.amount:.2f} occurred at {tx.ts} via channel '{tx.channel}' under product code '{tx.product_cd}'",
            f"Associated with customer {tx.customer_id} on card {tx.card_id} ({tx.card_network} {tx.card_type})",
            f"Input model risk score: {tx.risk_score:.2f} (Note: model signal only, not a confirmed verdict)",
        ]
        if tx.addr1:
            evidence.append(f"Billed in region code {tx.addr1} (country code: {tx.addr2})")
        if tx.profile_id and "Unknown" not in tx.profile_id:
            evidence.append(f"Executed from online device profile: {tx.profile_id}")
        if tx.email_domain:
            evidence.append(f"Purchaser email domain: {tx.email_domain}")

        return {
            "tool": "get_transaction",
            "status": "success",
            "backend": backend,
            "subject": {
                "txn_id": tx.txn_id,
                "customer_id": tx.customer_id,
                "card_id": tx.card_id,
                "amount_usd": tx.amount,
                "ts": tx.ts,
                "channel": tx.channel,
                "model_risk_score": tx.risk_score,
                "addr1": tx.addr1,
                "profile_id": tx.profile_id,
            },
            "evidence": evidence,
            "metrics": {
                "amount_usd": tx.amount,
                "model_risk_score": tx.risk_score,
            },
            "limitations": [
                "model_risk_score is a model prediction signal and must be corroborated with graph evidence."
            ]
        }

    def handle_get_customer_history(self, args: Dict[str, Any], backend: str) -> Dict[str, Any]:
        cust_id = str(args.get("customer_id", "")).strip()
        if not cust_id:
            return {
                "tool": "get_customer_history",
                "status": "error",
                "backend": backend,
                "error": "Missing required argument 'customer_id'",
                "subject": {},
                "evidence": [],
                "metrics": {},
                "limitations": []
            }

        limit = int(args.get("limit", 50))
        hist = self.tools.get_customer_history(cust_id, limit=limit)

        evidence = [
            f"Customer {cust_id} has {hist.transaction_count} total historical transactions in record",
            f"Total historical spend: ${hist.total_spend_usd:.2f} (Average transaction: ${hist.avg_amount_usd:.2f})",
            f"Active cards held: {', '.join(hist.cards_used) if hist.cards_used else 'none'}",
        ]
        if hist.devices_used:
            evidence.append(f"Recognized device profiles used: {len(hist.devices_used)} distinct profiles")

        # Compact summary of recent transactions
        recent_summary = [
            f"Txn {t.txn_id}: ${t.amount:.2f} ({t.ts}, {t.channel}, score {t.risk_score:.2f})"
            for t in hist.recent_transactions[:5]
        ]

        return {
            "tool": "get_customer_history",
            "status": "success",
            "backend": backend,
            "subject": {
                "customer_id": cust_id,
                "cards_held": hist.cards_used,
            },
            "evidence": evidence,
            "metrics": {
                "total_transactions": hist.transaction_count,
                "total_spend_usd": hist.total_spend_usd,
                "avg_amount_usd": hist.avg_amount_usd,
                "recent_sample": recent_summary,
            },
            "limitations": [f"Recent transaction list capped at top {min(5, len(hist.recent_transactions))} sample."]
        }

    def handle_get_card_history(self, args: Dict[str, Any], backend: str) -> Dict[str, Any]:
        card_id = str(args.get("card_id", "")).strip()
        if not card_id:
            return {
                "tool": "get_card_history",
                "status": "error",
                "backend": backend,
                "error": "Missing required argument 'card_id'",
                "subject": {},
                "evidence": [],
                "metrics": {},
                "limitations": []
            }

        limit = int(args.get("limit", 50))
        hist = self.tools.get_card_history(card_id, limit=limit)

        evidence = [
            f"Card {card_id} ({hist.card_network} {hist.card_type}, issuer {hist.issuer_code}) belongs to customer {hist.customer_id}",
            f"Recorded {hist.total_txns} transactions totaling ${hist.total_amount_usd:.2f}",
            f"Card spending baseline: average ${hist.avg_amount_usd:.2f}, maximum single purchase ${hist.max_amount_usd:.2f}",
        ]

        recent_sample = [
            f"Txn {t.txn_id}: ${t.amount:.2f} ({t.ts}, {t.channel}, score {t.risk_score:.2f})"
            for t in hist.transactions[:5]
        ]

        return {
            "tool": "get_card_history",
            "status": "success",
            "backend": backend,
            "subject": {
                "card_id": card_id,
                "customer_id": hist.customer_id,
                "network": hist.card_network,
                "type": hist.card_type,
            },
            "evidence": evidence,
            "metrics": {
                "total_transactions": hist.total_txns,
                "total_volume_usd": hist.total_amount_usd,
                "avg_amount_usd": hist.avg_amount_usd,
                "max_amount_usd": hist.max_amount_usd,
                "recent_transactions_sample": recent_sample,
            },
            "limitations": []
        }

    def handle_get_transaction_neighborhood(self, args: Dict[str, Any], backend: str) -> Dict[str, Any]:
        txn_id = str(args.get("txn_id", "")).strip()
        if not txn_id:
            return {
                "tool": "get_transaction_neighborhood",
                "status": "error",
                "backend": backend,
                "error": "Missing required argument 'txn_id'",
                "subject": {},
                "evidence": [],
                "metrics": {},
                "limitations": []
            }

        hops = int(args.get("max_hops", 2))
        neigh = self.tools.get_transaction_neighborhood(txn_id, max_hops=hops)

        node_types = {}
        for n in neigh.nodes:
            node_types[n.type] = node_types.get(n.type, 0) + 1

        evidence = [
            f"Ego-network centered on transaction {txn_id} contains {len(neigh.nodes)} vertices and {len(neigh.edges)} connecting edges",
            f"Connected vertex breakdown: {', '.join(f'{k}: {v}' for k, v in node_types.items())}",
        ]

        return {
            "tool": "get_transaction_neighborhood",
            "status": "success",
            "backend": backend,
            "subject": {"txn_id": txn_id, "max_hops": hops},
            "evidence": evidence,
            "metrics": {
                "total_nodes": len(neigh.nodes),
                "total_edges": len(neigh.edges),
                "node_types": node_types,
            },
            "limitations": ["Sub-graph capped to 2-hop radius to maintain compact context."]
        }

    def handle_find_shared_devices(self, args: Dict[str, Any], backend: str) -> Dict[str, Any]:
        profile_id = str(args.get("profile_id", "")).strip()
        if not profile_id:
            return {
                "tool": "find_shared_devices",
                "status": "error",
                "backend": backend,
                "error": "Missing required argument 'profile_id'",
                "subject": {},
                "evidence": [],
                "metrics": {},
                "limitations": []
            }

        dev_ev = self.tools.find_shared_devices(profile_id)
        evidence = []
        if dev_ev.is_shared:
            evidence.append(f"Device profile '{profile_id}' is shared across {len(dev_ev.connected_cards)} distinct cards and {len(dev_ev.connected_customers)} customers")
            evidence.append(f"Linked card IDs: {', '.join(dev_ev.connected_cards)}")
            evidence.append(f"Total transaction count observed from this device profile: {dev_ev.total_txns_on_device}")
        else:
            evidence.append(f"Device profile '{profile_id}' is unique to 1 card and has not been observed on other customer accounts")

        return {
            "tool": "find_shared_devices",
            "status": "success",
            "backend": backend,
            "subject": {
                "profile_id": profile_id,
                "is_shared": dev_ev.is_shared,
            },
            "evidence": evidence,
            "metrics": {
                "connected_cards_count": len(dev_ev.connected_cards),
                "connected_customers_count": len(dev_ev.connected_customers),
                "total_txns_on_device": dev_ev.total_txns_on_device,
                "connected_cards": dev_ev.connected_cards,
            },
            "limitations": [
                "Shared device indicates common hardware footprint or network proxy; requires policy evaluation under Rule R6."
            ]
        }

    def handle_detect_card_testing(self, args: Dict[str, Any], backend: str) -> Dict[str, Any]:
        card_id = str(args.get("card_id", "")).strip()
        if not card_id:
            return {
                "tool": "detect_card_testing",
                "status": "error",
                "backend": backend,
                "error": "Missing required argument 'card_id'",
                "subject": {},
                "evidence": [],
                "metrics": {},
                "limitations": []
            }

        window_hours = int(args.get("window_hours", 24))
        testing_ev = self.tools.detect_card_testing(card_id, window_hours=window_hours)

        evidence = []
        if testing_ev.is_testing_detected:
            evidence.append(f"Card testing sequence detected on {card_id}: {testing_ev.micro_auth_count} online micro-authorizations (≤ $5.00) followed by larger purchases")
            evidence.append(f"Heuristic confidence: {testing_ev.heuristic_confidence:.2f}")
            for m in testing_ev.micro_auth_transactions[:3]:
                evidence.append(f"  Micro-auth {m.txn_id}: ${m.amount:.2f} ({m.ts})")
        else:
            evidence.append(f"No card testing sequence detected on {card_id} (Micro-auth count: {testing_ev.micro_auth_count})")

        return {
            "tool": "detect_card_testing",
            "status": "success",
            "backend": backend,
            "subject": {
                "card_id": card_id,
                "testing_detected": testing_ev.is_testing_detected,
            },
            "evidence": evidence,
            "metrics": {
                "is_testing_detected": testing_ev.is_testing_detected,
                "micro_auth_count": testing_ev.micro_auth_count,
                "rapid_sequence_count": testing_ev.rapid_sequence_count,
                "heuristic_confidence": testing_ev.heuristic_confidence,
            },
            "limitations": [
                "Heuristic confidence represents statistical pattern match and is NOT an automated fraud verdict. Follow Policy Rule R5."
            ]
        }

    def handle_detect_velocity(self, args: Dict[str, Any], backend: str) -> Dict[str, Any]:
        card_id = str(args.get("card_id", "")).strip()
        if not card_id:
            return {
                "tool": "detect_velocity",
                "status": "error",
                "backend": backend,
                "error": "Missing required argument 'card_id'",
                "subject": {},
                "evidence": [],
                "metrics": {},
                "limitations": []
            }

        window_hours = float(args.get("window_hours", 48.0))
        vel = self.tools.detect_velocity(card_id, window_hours=window_hours)

        evidence = [
            f"Observed {vel.txn_count} transactions totaling ${vel.total_amount_usd:.2f} on card {card_id}",
            f"Average amount: ${vel.avg_amount_usd:.2f}, Maximum amount: ${vel.max_amount_usd:.2f}",
            f"Velocity spike status: {'ACTIVE SPIKE' if vel.is_velocity_spike else 'NORMAL VELOCITY'}",
        ]

        return {
            "tool": "detect_velocity",
            "status": "success",
            "backend": backend,
            "subject": {
                "card_id": card_id,
                "is_velocity_spike": vel.is_velocity_spike,
            },
            "evidence": evidence,
            "metrics": {
                "txn_count": vel.txn_count,
                "total_amount_usd": vel.total_amount_usd,
                "avg_amount_usd": vel.avg_amount_usd,
                "max_amount_usd": vel.max_amount_usd,
            },
            "limitations": []
        }

    def handle_detect_regional_anomaly(self, args: Dict[str, Any], backend: str) -> Dict[str, Any]:
        txn_id = str(args.get("txn_id", "")).strip()
        if not txn_id:
            return {
                "tool": "detect_regional_anomaly",
                "status": "error",
                "backend": backend,
                "error": "Missing required argument 'txn_id'",
                "subject": {},
                "evidence": [],
                "metrics": {},
                "limitations": []
            }

        reg = self.tools.detect_regional_anomaly(txn_id)
        evidence = []
        if reg.is_anomaly:
            evidence.append(f"In-person transaction {txn_id} occurred in remote billing region {reg.current_addr1}")
            evidence.append(f"Cardholder historical baseline established in home region {reg.historical_home_addr1} ({reg.prior_home_txns_count} prior transactions)")
            evidence.append(f"Heuristic confidence: {reg.heuristic_confidence:.2f}")
        else:
            evidence.append(f"Transaction region {reg.current_addr1} matches historical baseline region {reg.historical_home_addr1}")

        return {
            "tool": "detect_regional_anomaly",
            "status": "success",
            "backend": backend,
            "subject": {
                "txn_id": txn_id,
                "card_id": reg.card_id,
                "current_addr1": reg.current_addr1,
                "home_addr1": reg.historical_home_addr1,
                "is_anomaly": reg.is_anomaly,
            },
            "evidence": evidence,
            "metrics": {
                "is_anomaly": reg.is_anomaly,
                "prior_home_txns": reg.prior_home_txns_count,
                "heuristic_confidence": reg.heuristic_confidence,
            },
            "limitations": [
                "Several consecutive days in one remote region may indicate legitimate travel rather than compromise (Rule R4 / R7)."
            ]
        }

    def handle_get_historical_cases(self, args: Dict[str, Any], backend: str) -> Dict[str, Any]:
        cust_id = args.get("customer_id")
        card_id = args.get("card_id")
        pattern = args.get("pattern")
        top_k = int(args.get("top_k", 5))

        cases = self.tools.get_historical_cases(customer_id=cust_id, card_id=card_id, pattern=pattern, top_k=top_k)

        evidence = []
        if cases:
            evidence.append(f"Found {len(cases)} relevant closed investigations from bank case memory:")
            for c in cases:
                evidence.append(
                    f"Case {c.case_id} ({c.outcome.upper()}, {c.pattern}, Exposure: ${c.exposure_usd:.2f}): {c.analyst_notes[:120]}..."
                )
        else:
            evidence.append("No previous closed investigations found for these query criteria.")

        return {
            "tool": "get_historical_cases",
            "status": "success",
            "backend": backend,
            "subject": {
                "customer_id": cust_id,
                "card_id": card_id,
                "pattern": pattern,
            },
            "evidence": evidence,
            "metrics": {
                "cases_retrieved_count": len(cases),
                "case_ids": [c.case_id for c in cases],
                "cases": [c.model_dump() for c in cases],
            },
            "limitations": [
                "Historical cases provide investigative precedent and context; they must inform but not blindly dictate current decisions."
            ]
        }

    def handle_find_connected_cards(self, args: Dict[str, Any], backend: str) -> Dict[str, Any]:
        card_id = str(args.get("card_id", "")).strip()
        if not card_id:
            return {
                "tool": "find_connected_cards",
                "status": "error",
                "backend": backend,
                "error": "Missing required argument 'card_id'",
                "subject": {},
                "evidence": [],
                "metrics": {},
                "limitations": []
            }

        conn = self.tools.find_connected_cards(card_id)

        evidence = []
        if conn.connected_cards:
            evidence.append(f"Discovered {len(conn.connected_cards)} connected cards linked to target card {card_id}:")
            for sc, reason in conn.connection_reasons.items():
                evidence.append(f"  - Card {sc}: {reason}")
        else:
            evidence.append(f"No secondary cards or shared-device syndicates found for card {card_id}.")

        return {
            "tool": "find_connected_cards",
            "status": "success",
            "backend": backend,
            "subject": {
                "primary_card_id": card_id,
                "connected_cards_count": len(conn.connected_cards),
            },
            "evidence": evidence,
            "metrics": {
                "connected_cards": conn.connected_cards,
                "connection_reasons": conn.connection_reasons,
                "shared_device_profiles": conn.shared_device_profiles,
            },
            "limitations": [
                "Connected cards should be reviewed for monitoring under Policy Rule R6."
            ]
        }
