import pytest
from unittest.mock import MagicMock, patch
from src.core.config import Settings
from src.tigergraph.client import TigerGraphClient
from src.tigergraph.graph_loader import TigerGraphDataLoader
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.mcp.server import TigerGraphMCPServer
from src.memory.graph_writeback import CaseGraphWritebackEngine
from src.models.case_memory import CaseMemoryRecord, CaseLifecycleStatus

def test_tigergraph_client_cloud_init():
    """Test TigerGraphClient initialization with Savanna cloud URL and gsqlSecret."""
    client = TigerGraphClient(
        host="https://hhgoa-fraud-workspace.i.tgcloud.io",
        graphname="hhgoa-fraud-db",
        username="tigergraph",
        password="test_password",
        secret="test_secret_12345",
    )
    assert client.host == "https://hhgoa-fraud-workspace.i.tgcloud.io"
    assert client.graphname == "hhgoa-fraud-db"
    assert client.username == "tigergraph"
    assert client.secret == "test_secret_12345"

@patch("pyTigerGraph.TigerGraphConnection")
def test_tigergraph_client_connection_creation(mock_tg_conn_class):
    mock_instance = MagicMock()
    mock_instance.getToken.return_value = "mocked_jwt_token_abc"
    mock_instance.ping.return_value = "pong"
    mock_tg_conn_class.return_value = mock_instance

    client = TigerGraphClient(
        host="https://hhgoa-fraud-workspace.i.tgcloud.io",
        graphname="hhgoa-fraud-db",
        username="tigergraph",
        password="test_password",
        secret="test_secret_value",
    )
    
    conn = client.get_connection()
    assert conn is mock_instance
    mock_tg_conn_class.assert_called_once_with(
        host="https://hhgoa-fraud-workspace.i.tgcloud.io",
        graphname="hhgoa-fraud-db",
        username="tigergraph",
        password="test_password",
        gsqlSecret="test_secret_value",
        apiToken="",
        tgCloud=True,
    )
    mock_instance.getToken.assert_called_once_with("test_secret_value")
    assert client.api_token == "mocked_jwt_token_abc"
    assert client.is_connected() is True

@patch("pyTigerGraph.TigerGraphConnection")
def test_tigergraph_data_loader_schema_and_query_deploy(mock_tg_conn_class, tmp_path):
    mock_conn = MagicMock()
    mock_conn.gsql.return_value = "The graph FraudGraph is created."
    mock_tg_conn_class.return_value = mock_conn

    client = TigerGraphClient(host="https://test.i.tgcloud.io", secret="dummy_secret")
    loader = TigerGraphDataLoader(tg_client=client)

    # Test schema loading
    dummy_schema = tmp_path / "test_schema.gsql"
    dummy_schema.write_text("CREATE GRAPH TestGraph()", encoding="utf-8")
    res = loader.load_schema(dummy_schema)
    assert res["success"] is True
    assert "created" in res["result"]

    # Test query installation
    dummy_queries = tmp_path / "test_queries.gsql"
    dummy_queries.write_text("CREATE QUERY test_q() FOR GRAPH TestGraph { PRINT 1; } INSTALL QUERY test_q", encoding="utf-8")
    q_res = loader.install_queries(dummy_queries)
    assert q_res["success"] is True

def test_tigergraph_tools_live_routing():
    mock_live_client = MagicMock(spec=TigerGraphClient)
    mock_live_client.run_installed_query.return_value = [{
        "Start": [{"attributes": {"amount": 50.0, "ts_str": "2024-01-01T12:00:00", "channel": "online", "risk_score": 0.85, "product_cd": "W", "addr1": "123", "addr2": "87.0"}}],
        "CardOwner": [{"attributes": {"card_id": "C001-K1", "issuer_code": 1000, "card_network": "visa", "card_type": "credit"}}],
        "CustomerOwner": [{"attributes": {"customer_id": "C001"}}],
        "DeviceUsed": [{"attributes": {"profile_id": "DEV-001"}}],
        "EmailUsed": [{"attributes": {"domain": "gmail.com"}}],
    }]
    
    tools = TigerGraphInvestigationTools(tg_client=mock_live_client)
    assert tools.is_live() is True
    
    tx = tools.get_transaction("1001")
    assert tx is not None
    assert tx.txn_id == "1001"
    assert tx.amount == 50.0
    assert tx.customer_id == "C001"
    assert tx.card_id == "C001-K1"
    mock_live_client.run_installed_query.assert_called_once_with("get_transaction", {"txn": "1001"})

def test_mcp_server_live_backend_status():
    mock_live_client = MagicMock(spec=TigerGraphClient)
    tools = TigerGraphInvestigationTools(tg_client=mock_live_client)
    server = TigerGraphMCPServer(investigation_tools=tools)
    
    status = server.get_server_status()
    assert status["backend"] == "tigergraph_live"
    assert status["is_live_tigergraph"] is True

def test_live_case_writeback_mock():
    mock_live_client = MagicMock(spec=TigerGraphClient)
    mock_live_client.ping.return_value = {"connected": True}
    
    writeback = CaseGraphWritebackEngine(tg_client=mock_live_client)
    assert writeback.is_live_deployment() is True
    
    now_iso = "2024-01-01T12:00:00"
    case = CaseMemoryRecord(
        case_id="CASE-TEST-LIVE-999",
        status=CaseLifecycleStatus.INVESTIGATING,
        fraud_assessment="UNDER_REVIEW",
        confidence=0.75,
        triggering_txn_id=1001,
        trigger_type="test_trigger",
        created_at=now_iso,
        updated_at=now_iso,
        card_id="C001-K1",
        customer_id="C001",
        summary="Test writeback",
        fraud_patterns_identified=["CARD_TESTING"],
        related_entities={"cards": ["C001-K1", "C001-K2"]}
    )
    
    res = writeback.write_case(case)
    assert res["status"] == "success"
    assert res["mode"] == "LIVE"
    
    mock_live_client.upsert_vertex.assert_called_once()
    assert mock_live_client.upsert_edge.call_count >= 2

def test_get_historical_cases_customer_id_only():
    mock_client = MagicMock(spec=TigerGraphClient)
    mock_client.run_installed_query.return_value = [
        {"DirectCases": [{"v_id": "CC-101", "attributes": {"customer_id": "C001", "card_id": "C001-K1", "outcome": "confirmed_fraud", "pattern": "card_testing", "exposure_usd": 150.0, "n_txns": 2, "analyst_notes": "Test case"}}]},
        {"ConnectedCases": []}
    ]
    tools = TigerGraphInvestigationTools(tg_client=mock_client)
    cases = tools.get_historical_cases(customer_id="C001", top_k=5)
    assert len(cases) == 1
    assert cases[0].case_id == "CC-101"
    assert cases[0].customer_id == "C001"
    mock_client.run_installed_query.assert_called_once_with("get_historical_cases", {"cust": ("C001", "Customer"), "top_k": 5})

def test_get_historical_cases_card_id_resolution():
    mock_client = MagicMock(spec=TigerGraphClient)
    # 1. get_card_transaction_history called to resolve card -> customer
    # 2. get_historical_cases called with resolved customer
    def side_effect(query_name, params):
        if query_name == "get_card_transaction_history":
            return [
                {"Start": [{"v_id": "C001-K1", "attributes": {"customer_id": "C001", "issuer_code": 1000, "card_network": "visa", "card_type": "credit"}}]},
                {"Txns": []}
            ]
        elif query_name == "get_historical_cases":
            return [
                {"DirectCases": [{"v_id": "CC-101", "attributes": {"customer_id": "C001", "card_id": "C001-K1", "outcome": "confirmed_fraud", "pattern": "card_testing", "exposure_usd": 150.0, "n_txns": 2, "analyst_notes": "Resolved via card"}}]},
                {"ConnectedCases": []}
            ]
        return []

    mock_client.run_installed_query.side_effect = side_effect
    tools = TigerGraphInvestigationTools(tg_client=mock_client)
    cases = tools.get_historical_cases(card_id="C001-K1", top_k=5)
    assert len(cases) == 1
    assert cases[0].case_id == "CC-101"
    assert cases[0].customer_id == "C001"
    assert mock_client.run_installed_query.call_count == 2

def test_get_historical_cases_both_customer_and_card():
    mock_client = MagicMock(spec=TigerGraphClient)
    mock_client.run_installed_query.return_value = [
        {"DirectCases": [{"v_id": "CC-202", "attributes": {"customer_id": "C002", "card_id": "C002-K1", "outcome": "cleared", "pattern": "none", "exposure_usd": 0.0, "n_txns": 1, "analyst_notes": "Both supplied"}}]},
        {"ConnectedCases": []}
    ]
    tools = TigerGraphInvestigationTools(tg_client=mock_client)
    cases = tools.get_historical_cases(customer_id="C002", card_id="C002-K1", top_k=5)
    assert len(cases) == 1
    assert cases[0].case_id == "CC-202"
    # Should use customer_id directly without needing card history query
    mock_client.run_installed_query.assert_called_once_with("get_historical_cases", {"cust": ("C002", "Customer"), "top_k": 5})

def test_get_historical_cases_unknown_card_id():
    mock_client = MagicMock(spec=TigerGraphClient)
    mock_client.run_installed_query.return_value = [{"Start": []}, {"Txns": []}]
    tools = TigerGraphInvestigationTools(tg_client=mock_client)
    cases = tools.get_historical_cases(card_id="UNKNOWN-CARD", top_k=5)
    assert cases == []

def test_get_historical_cases_sample_parity():
    from src.tigergraph.sample_client import SampleGraphClient
    sample_tools = TigerGraphInvestigationTools(tg_client=SampleGraphClient())
    cases_cust = sample_tools.get_historical_cases(customer_id="C08623", top_k=5)
    cases_card = sample_tools.get_historical_cases(card_id="C08623-K2", top_k=5)
    assert len(cases_cust) > 0
    assert len(cases_card) > 0

