import pytest
import pandas as pd
from src.rag.corpus import GraphRAGCorpus, OFFICIAL_POLICY_RULES, OFFICIAL_REGULATORY_REFERENCES
from src.rag.retriever import GraphRAGRetriever, BM25Index
from src.rag.graph_adapter import GraphEvidenceAdapter
from src.rag.synthesis import InvestigationContextSynthesizer
from src.tigergraph.sample_client import SampleGraphClient
from src.tigergraph.tools import TigerGraphInvestigationTools
from src.models.context import InvestigationContext, HistoricalCaseMatch, PolicyRuleMatch

@pytest.fixture
def corpus(raw_data_dir):
    return GraphRAGCorpus(data_dir=raw_data_dir)

@pytest.fixture
def retriever(corpus):
    return GraphRAGRetriever(corpus=corpus)

@pytest.fixture
def synthesizer(sample_data_dir, retriever):
    sample_client = SampleGraphClient(sample_data_dir)
    tools = TigerGraphInvestigationTools(tg_client=sample_client)
    return InvestigationContextSynthesizer(retriever=retriever, tools=tools)

def test_corpus_loading_and_inventory(corpus):
    inventory = corpus.get_inventory()
    assert "closed_cases" in inventory
    assert inventory["closed_cases"]["total_records"] == 5565
    assert inventory["closed_cases"]["confirmed_fraud_records"] > 0
    assert inventory["closed_cases"]["cleared_records"] > 0
    assert len(corpus.policy_rules) == 10
    assert len(corpus.regulatory_references) == 5

def test_bm25_indexing():
    docs = [
        {"id": "doc1", "text": "card testing micro authorization burst"},
        {"id": "doc2", "text": "account takeover credential theft online"},
        {"id": "doc3", "text": "travel verified customer confirmed legitimate"},
    ]
    index = BM25Index(documents=docs, text_fields=["text"], id_field="id")
    results = index.score("card testing")
    assert len(results) > 0
    top_doc_idx, top_score = results[0]
    assert docs[top_doc_idx]["id"] == "doc1"
    assert top_score > 0.0

def test_historical_case_retrieval_confirmed_fraud(retriever):
    cases = retriever.retrieve_historical_cases(
        query_text="unauthorized card not present fraud",
        customer_id="C12382",
        outcome="confirmed_fraud",
        top_k=3
    )
    assert len(cases) > 0
    assert all(c.outcome == "confirmed_fraud" for c in cases)
    assert cases[0].customer_id == "C12382"
    assert cases[0].relevance_score > 5.0
    assert len(cases[0].similarity_reasons) > 0

def test_historical_case_retrieval_cleared_cases(retriever):
    # Retrieve cleared cases
    cases = retriever.retrieve_historical_cases(
        query_text="travel confirmed legitimate billing region",
        outcome="cleared",
        top_k=5
    )
    assert len(cases) > 0
    assert all(c.outcome == "cleared" for c in cases)
    assert any("travel" in c.analyst_notes.lower() or "cleared" in c.analyst_notes.lower() for c in cases)

def test_policy_rule_retrieval(retriever):
    # Query for card testing
    policies = retriever.retrieve_applicable_policies(
        query_text="card_testing micro authorizations",
        detected_patterns=["card_testing"],
        has_shared_devices=False,
        exposure_usd=150.0,
        model_risk_score=0.85
    )
    rule_ids = [p.rule_id for p in policies]
    assert "R5" in rule_ids
    r5 = next(p for p in policies if p.rule_id == "R5")
    assert "BLOCK_CARD" in r5.recommended_actions
    assert len(r5.triggering_evidence) > 0

def test_policy_rule_shared_devices(retriever):
    policies = retriever.retrieve_applicable_policies(
        query_text="shared device multi card syndicate",
        has_shared_devices=True,
        exposure_usd=800.0,
        model_risk_score=0.90
    )
    rule_ids = [p.rule_id for p in policies]
    assert "R6" in rule_ids
    assert "R8" in rule_ids

def test_regulatory_reference_retrieval(retriever):
    regs = retriever.retrieve_regulatory_references(
        query_text="suspicious activity report mandatory filing",
        exposure_usd=2500.0,
        is_online=True
    )
    reg_ids = [r.regulation_id for r in regs]
    assert any("FINCEN" in rid for rid in reg_ids)
    assert any("REG-E" in rid for rid in reg_ids)

def test_graph_evidence_adapter():
    adapter = GraphEvidenceAdapter()
    adapted = adapter.extract_retrieval_query(
        tx=None,
        cust_hist=None,
        card_hist=None,
        shared_devices=None,
        velocity=None,
        regional=None,
        connected_cards=None,
        detected_patterns=None
    )
    assert "query_text" in adapted
    assert "graph_evidence_bullets" in adapted

def test_investigation_context_synthesis(synthesizer):
    # Synthesize for benchmark case HHG-001 (Customer C12382, Txn 3514030)
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-001",
        opened_at="2016-12-04 19:55:28",
        trigger_type="customer_report",
        trigger_text="Cardholder reported unauthorized transaction in unfamiliar city.",
        flagged_txn_id=3514030,
        card_id="C12382-K1",
        customer_id="C12382",
        risk_score=0.61
    )

    assert isinstance(ctx, InvestigationContext)
    assert ctx.case_id == "HHG-001"
    assert ctx.customer_id == "C12382"
    assert len(ctx.graph_evidence_summary) > 0
    assert len(ctx.historical_cases_confirmed_fraud) > 0
    assert len(ctx.applicable_policies) > 0
    assert len(ctx.regulatory_references) > 0
    assert len(ctx.supporting_evidence) > 0
    assert len(ctx.source_attributions) > 0

    # Verify provenance
    for attr in ctx.source_attributions:
        assert attr.source_type in ["graph", "closed_case", "policy", "regulation"]
        assert len(attr.source_id) > 0
        assert attr.relevance_score > 0.0

def test_contradictory_evidence_handling(synthesizer):
    # Synthesize for a case with benign indicators
    ctx = synthesizer.build_context_for_case(
        case_id="HHG-004",
        opened_at="2016-12-29 01:53:54",
        trigger_type="analyst_request",
        trigger_text="Analyst requested secondary review.",
        flagged_txn_id=3583227,
        card_id="C08106-K1",
        customer_id="C08106",
        risk_score=0.34
    )

    assert isinstance(ctx, InvestigationContext)
    assert len(ctx.contradictory_evidence) > 0
    # Customer C08106 has cleared case CC-0696 in memory
    assert len(ctx.historical_cases_cleared) > 0
    assert any("cleared" in ce.evidence.lower() or "baseline" in ce.evidence.lower() for ce in ctx.contradictory_evidence)

def test_empty_retrieval_graceful_handling(retriever):
    cases = retriever.retrieve_historical_cases(
        query_text="nonexistent_gibberish_term_xyz_12345",
        top_k=3
    )
    assert isinstance(cases, list)
    assert len(cases) == 0

def test_deterministic_ranking(retriever):
    cases1 = retriever.retrieve_historical_cases(query_text="card_testing burst", customer_id="C12382", top_k=5)
    cases2 = retriever.retrieve_historical_cases(query_text="card_testing burst", customer_id="C12382", top_k=5)
    
    assert [c.case_id for c in cases1] == [c.case_id for c in cases2]
    assert [c.relevance_score for c in cases1] == [c.relevance_score for c in cases2]
