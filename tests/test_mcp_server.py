import pytest
from unittest.mock import MagicMock
from src.mcp.server import TigerGraphMCPServer
from src.mcp.schemas import MCP_INVESTIGATION_TOOLS
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.tigergraph.sample_client import SampleGraphClient
from src.tigergraph.client import TigerGraphClient

@pytest.fixture
def mcp_server(sample_data_dir):
    client = SampleGraphClient(sample_data_dir)
    tools = TigerGraphInvestigationTools(tg_client=client)
    return TigerGraphMCPServer(investigation_tools=tools)

def test_mcp_server_initialization_and_status(mcp_server):
    status = mcp_server.get_server_status()
    assert status["status"] == "online"
    assert status["backend"] == "offline_sample"
    assert status["is_live_tigergraph"] is False
    assert status["tools_registered"] == 10
    assert len(status["tool_names"]) == 10

def test_mcp_list_tools_schemas(mcp_server):
    tools = mcp_server.list_tools()
    assert len(tools) == 10
    names = [t["name"] for t in tools]
    expected = [
        "get_transaction",
        "get_customer_history",
        "get_card_history",
        "get_transaction_neighborhood",
        "find_shared_devices",
        "detect_card_testing",
        "detect_velocity",
        "detect_regional_anomaly",
        "get_historical_cases",
        "find_connected_cards",
    ]
    for exp in expected:
        assert exp in names

def test_mcp_get_transaction(mcp_server):
    res = mcp_server.call_tool("get_transaction", {"txn_id": "3514030"})
    assert res["status"] == "success"
    assert res["backend"] == "offline_sample"
    assert res["subject"]["txn_id"] == "3514030"
    assert res["subject"]["customer_id"] == "C12382"
    assert res["subject"]["amount_usd"] == 77.07
    assert len(res["evidence"]) > 0
    assert "model_risk_score" in res["metrics"]

def test_mcp_get_customer_history(mcp_server):
    res = mcp_server.call_tool("get_customer_history", {"customer_id": "C12382"})
    assert res["status"] == "success"
    assert res["subject"]["customer_id"] == "C12382"
    assert res["metrics"]["total_transactions"] > 0
    assert len(res["evidence"]) > 0

def test_mcp_get_card_history(mcp_server):
    res = mcp_server.call_tool("get_card_history", {"card_id": "C12382-K1"})
    assert res["status"] == "success"
    assert res["subject"]["card_id"] == "C12382-K1"
    assert res["metrics"]["total_transactions"] > 0

def test_mcp_get_transaction_neighborhood(mcp_server):
    res = mcp_server.call_tool("get_transaction_neighborhood", {"txn_id": "3514030", "max_hops": 2})
    assert res["status"] == "success"
    assert res["metrics"]["total_nodes"] >= 3
    assert res["metrics"]["total_edges"] >= 2

def test_mcp_find_shared_devices(mcp_server):
    # Test with sample profile
    res = mcp_server.call_tool("find_shared_devices", {"profile_id": "Windows | Windows 10 | edge 16.0 | 1366x768"})
    assert res["status"] == "success"
    assert "is_shared" in res["subject"]
    assert "connected_cards_count" in res["metrics"]

def test_mcp_detect_card_testing(mcp_server):
    res = mcp_server.call_tool("detect_card_testing", {"card_id": "C12382-K1"})
    assert res["status"] == "success"
    assert "testing_detected" in res["subject"]
    assert "heuristic_confidence" in res["metrics"]

def test_mcp_detect_velocity(mcp_server):
    res = mcp_server.call_tool("detect_velocity", {"card_id": "C12382-K1"})
    assert res["status"] == "success"
    assert "is_velocity_spike" in res["subject"]
    assert res["metrics"]["txn_count"] > 0

def test_mcp_detect_regional_anomaly(mcp_server):
    res = mcp_server.call_tool("detect_regional_anomaly", {"txn_id": "3514030"})
    assert res["status"] == "success"
    assert res["subject"]["is_anomaly"] is True
    assert res["metrics"]["heuristic_confidence"] == 0.85

def test_mcp_get_historical_cases(mcp_server):
    res = mcp_server.call_tool("get_historical_cases", {"customer_id": "C12382"})
    assert res["status"] == "success"
    assert "cases_retrieved_count" in res["metrics"]
    assert len(res["metrics"]["cases"]) > 0

def test_mcp_find_connected_cards(mcp_server):
    res = mcp_server.call_tool("find_connected_cards", {"card_id": "C12382-K1"})
    assert res["status"] == "success"
    assert "connected_cards" in res["metrics"]

def test_mcp_error_handling(mcp_server):
    # 1. Missing argument
    res1 = mcp_server.call_tool("get_transaction", {})
    assert res1["status"] == "error"
    assert "Missing required argument" in res1["error"]

    # 2. Nonexistent entity
    res2 = mcp_server.call_tool("get_transaction", {"txn_id": "999999999"})
    assert res2["status"] == "not_found"

    # 3. Unknown tool
    res3 = mcp_server.call_tool("unknown_tool", {})
    assert res3["status"] == "error"
    assert "Unknown tool" in res3["error"]

def test_mcp_live_mode_routing_mock():
    mock_tg_client = MagicMock(spec=TigerGraphClient)
    tools = TigerGraphInvestigationTools(tg_client=mock_tg_client)
    server = TigerGraphMCPServer(investigation_tools=tools)
    
    status = server.get_server_status()
    assert status["backend"] == "tigergraph_live"
    assert status["is_live_tigergraph"] is True
