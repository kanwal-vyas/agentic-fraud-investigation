import pytest
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.analysis.pattern_detector import FraudPatternDetector
from src.core.constants import FraudPattern

@pytest.fixture
def investigation_tools(sample_data_dir):
    from src.tigergraph.sample_client import SampleGraphClient
    client = SampleGraphClient(sample_data_dir)
    return TigerGraphInvestigationTools(tg_client=client)

def test_get_transaction(investigation_tools):
    tx = investigation_tools.get_transaction("3514030")
    assert tx is not None
    assert tx.txn_id == "3514030"
    assert tx.customer_id == "C12382"
    assert tx.card_id == "C12382-K1"
    assert tx.amount == 77.07
    assert tx.channel == "in_person"
    assert tx.risk_score == 0.61

def test_get_customer_history(investigation_tools):
    hist = investigation_tools.get_customer_history("C12382", limit=50)
    assert hist.customer_id == "C12382"
    assert hist.transaction_count > 0
    assert "C12382-K1" in hist.cards_used
    assert hist.total_spend_usd > 0.0

def test_get_card_history(investigation_tools):
    card_hist = investigation_tools.get_card_history("C12382-K1", limit=50)
    assert card_hist.card_id == "C12382-K1"
    assert card_hist.total_txns > 0
    assert card_hist.card_network in ["visa", "mastercard", "discover", "american express", "unknown"]

def test_get_transaction_neighborhood(investigation_tools):
    neigh = investigation_tools.get_transaction_neighborhood("3514030")
    assert neigh.center_txn_id == "3514030"
    assert len(neigh.nodes) >= 3  # Txn, Card, Customer
    assert len(neigh.edges) >= 2  # PERFORMED_TXN, OWNS_CARD

def test_find_shared_devices(investigation_tools):
    # Find a transaction with a non-empty profile
    tx = investigation_tools.get_transaction("3478782")
    if tx and tx.profile_id and "Unknown" not in tx.profile_id:
        dev_ev = investigation_tools.find_shared_devices(tx.profile_id)
        assert dev_ev.profile_id == tx.profile_id
        assert len(dev_ev.connected_cards) > 0

def test_detect_velocity(investigation_tools):
    vel = investigation_tools.detect_velocity("C12382-K1")
    assert vel.entity_id == "C12382-K1"
    assert vel.txn_count > 0
    assert vel.total_amount_usd > 0.0

def test_detect_card_testing(investigation_tools):
    testing = investigation_tools.detect_card_testing("C12382-K1")
    assert testing.card_id == "C12382-K1"
    assert isinstance(testing.is_testing_detected, bool)

def test_detect_regional_anomaly(investigation_tools):
    reg = investigation_tools.detect_regional_anomaly("3514030")
    assert reg.txn_id == "3514030"
    assert isinstance(reg.is_anomaly, bool)

def test_get_historical_cases(investigation_tools):
    cases = investigation_tools.get_historical_cases(customer_id="C12382", top_k=3)
    assert isinstance(cases, list)

def test_find_connected_cards(investigation_tools):
    conn = investigation_tools.find_connected_cards("C12382-K1")
    assert conn.card_id == "C12382-K1"
    assert isinstance(conn.connected_cards, list)

def test_pattern_detector(investigation_tools):
    detector = FraudPatternDetector(investigation_tools)
    results = detector.detect_patterns("3514030")
    assert len(results) > 0
    top = results[0]
    assert isinstance(top.pattern, FraudPattern)
    assert 0.0 <= top.heuristic_confidence <= 1.0
    assert len(top.claims) > 0
