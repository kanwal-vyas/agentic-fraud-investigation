import pytest
from pathlib import Path
from scripts.validate_tigergraph import validate_tigergraph_graph
from src.tigergraph.client import TigerGraphClient

def test_tigergraph_graph_validation(sample_data_dir):
    res = validate_tigergraph_graph(sample_data_dir)
    assert res["overall_status"] == "PASS"
    assert res["checks"]["1_customer_to_cards"]["status"] == "PASS"
    assert res["checks"]["2_card_to_transactions"]["status"] == "PASS"
    assert res["checks"]["3_transaction_to_device"]["status"] == "PASS"
    assert res["checks"]["4_shared_devices"]["status"] == "PASS"
    assert res["checks"]["5_closed_case_to_txns"]["status"] == "PASS"
    assert res["checks"]["6_benchmark_flagged_txns"]["status"] == "PASS"
    assert res["checks"]["6_benchmark_flagged_txns"]["resolved_flagged_txns"] == 20

def test_tigergraph_client_instantiation():
    client = TigerGraphClient(host="http://127.0.0.1:9000", graphname="FraudGraph")
    assert client.host == "http://127.0.0.1:9000"
    assert client.graphname == "FraudGraph"
