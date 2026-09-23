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
