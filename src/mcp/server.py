import json
from typing import Dict, Any, List, Optional
from src.mcp.schemas import MCP_TOOLS
from src.tigergraph.client import TigerGraphClient

class TigerGraphMCPServer:
    """
    Model Context Protocol (MCP) server adapter for TigerGraph investigation tools.
    Exposes GSQL queries and graph operations as standard tool invocations.
    """
    def __init__(self, tg_client: Optional[TigerGraphClient] = None):
        self.tg_client = tg_client or TigerGraphClient()

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns the list of available MCP tools."""
        return [tool.model_dump() for tool in MCP_TOOLS]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an MCP tool call to the corresponding TigerGraph query handler."""
        handler_name = f"handle_{name}"
        handler = getattr(self, handler_name, None)
        if not handler:
            return {
                "is_error": True,
                "content": f"Unknown tool '{name}'"
            }
        try:
            result = handler(arguments)
            return {
                "is_error": False,
                "content": result
            }
        except Exception as e:
            return {
                "is_error": True,
                "content": f"Tool execution failed: {str(e)}"
            }

    def handle_get_transaction(self, args: Dict[str, Any]) -> Dict[str, Any]:
        txn_id = str(args.get("txn_id"))
        return self.tg_client.run_installed_query("get_transaction_neighborhood", {"txn_id": txn_id})

    def handle_get_card_history(self, args: Dict[str, Any]) -> Dict[str, Any]:
        card_id = str(args.get("card_id"))
        limit = int(args.get("limit", 50))
        return self.tg_client.run_installed_query("get_card_activity_window", {"card_id": card_id, "limit": limit})

    def handle_get_customer_profile(self, args: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = str(args.get("customer_id"))
        return self.tg_client.run_installed_query("get_customer_profile", {"customer_id": customer_id})

    def handle_get_device_connections(self, args: Dict[str, Any]) -> Dict[str, Any]:
        profile_id = str(args.get("profile_id"))
        return self.tg_client.run_installed_query("find_shared_device_ring", {"profile_id": profile_id})

    def handle_find_shared_device_rings(self, args: Dict[str, Any]) -> Dict[str, Any]:
        min_cards = int(args.get("min_cards", 2))
        return self.tg_client.run_installed_query("find_shared_device_rings", {"min_cards": min_cards})

    def handle_find_similar_historical_cases(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = {
            "customer_id": args.get("customer_id", ""),
            "card_id": args.get("card_id", ""),
            "pattern": args.get("pattern", ""),
            "top_k": int(args.get("top_k", 5)),
        }
        return self.tg_client.run_installed_query("find_similar_closed_cases", params)

    def handle_write_case_to_graph(self, args: Dict[str, Any]) -> Dict[str, Any]:
        case_id = str(args["case_id"])
        attributes = {
            "status": args["status"],
            "verdict": args["verdict"],
            "fraud_probability": float(args["fraud_probability"]),
            "pattern": args["pattern"],
            "pattern_description": args.get("pattern_description", ""),
            "exposure_usd": float(args["exposure_usd"]),
            "summary": args["summary"],
            "created_at": args.get("created_at", "NOW"),
        }
        res_v = self.tg_client.upsert_vertex("Case", case_id, attributes)
        
        card_id = args.get("card_id")
        if card_id:
            self.tg_client.upsert_edge("Case", case_id, "ON_CARD", "Card", card_id)
            
        for tid in args.get("affected_txn_ids", []):
            self.tg_client.upsert_edge("Case", case_id, "INVOLVES", "Transaction", str(tid))
            
        return {"status": "success", "graph_case_id": case_id}
