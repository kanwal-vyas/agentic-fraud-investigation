import re
import math
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from src.rag.corpus import GraphRAGCorpus
from src.models.context import (
    HistoricalCaseMatch,
    PolicyRuleMatch,
    RegulatoryReferenceMatch,
    SourceProvenance
)

def tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenization and lowercase normalization."""
    if not text:
        return []
    return re.findall(r'\b[a-zA-Z0-9_\-]+\b', str(text).lower())

class BM25Index:
    """
    Lightweight, deterministic BM25 index implemented in pure Python.
    No external dependencies required, guaranteeing fast, reproducible offline search.
    """
    def __init__(self, documents: List[Dict[str, Any]], text_fields: List[str], id_field: str, k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.id_field = id_field
        self.k1 = k1
        self.b = b
        self.doc_len = []
        self.doc_tokens = []
        self.doc_ids = []
        self.df = {}  # Term -> document frequency
        self.num_docs = len(documents)

        # Index documents
        total_len = 0
        for doc in documents:
            combined_text = " ".join(str(doc.get(f, "")) for f in text_fields)
            tokens = tokenize(combined_text)
            self.doc_tokens.append(tokens)
            self.doc_ids.append(doc[id_field])
            doc_l = len(tokens)
            self.doc_len.append(doc_l)
            total_len += doc_l

            unique_terms = set(tokens)
            for t in unique_terms:
                self.df[t] = self.df.get(t, 0) + 1

        self.avgdl = (total_len / self.num_docs) if self.num_docs > 0 else 1.0

        # Precalculate IDF
        self.idf = {}
        for t, freq in self.df.items():
            self.idf[t] = math.log(1.0 + (self.num_docs - freq + 0.5) / (freq + 0.5))

    def score(self, query: str) -> List[Tuple[int, float]]:
        q_tokens = tokenize(query)
        scores = [0.0] * self.num_docs

        for q in q_tokens:
            if q not in self.idf:
                continue
            q_idf = self.idf[q]
            for doc_idx, tokens in enumerate(self.doc_tokens):
                tf = tokens.count(q)
                if tf == 0:
                    continue
                num = tf * (self.k1 + 1.0)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (self.doc_len[doc_idx] / self.avgdl))
                scores[doc_idx] += q_idf * (num / denom)

        # Pair with indices
        scored_pairs = [(i, scores[i]) for i in range(self.num_docs) if scores[i] > 0.0]
        scored_pairs.sort(key=lambda x: x[1], reverse=True)
        return scored_pairs

class GraphRAGRetriever:
    """
    Hybrid retriever for GraphRAG investigation context.
    Provides deterministic BM25 search + exact metadata filters over:
    - 5,565 Historical Closed Cases (both confirmed fraud and cleared cases)
    - 10 Official Policy Rules (R1 - R10)
    - 5 Regulatory Compliance References
    """
    def __init__(self, corpus: Optional[GraphRAGCorpus] = None):
        self.corpus = corpus or GraphRAGCorpus()
        
        # Prepare closed cases records
        self.closed_cases_list = self.corpus.closed_cases_df.to_dict(orient="records")
        self.cases_index = BM25Index(
            documents=self.closed_cases_list,
            text_fields=["customer_id", "card_id", "pattern", "actions_taken", "analyst_notes", "outcome"],
            id_field="case_id"
        )

        # Policy rules index
        self.policy_index = BM25Index(
            documents=self.corpus.policy_rules,
            text_fields=["rule_id", "name", "condition", "description", "keywords"],
            id_field="rule_id"
        )

        # Regulatory references index
        self.reg_index = BM25Index(
            documents=self.corpus.regulatory_references,
            text_fields=["regulation_id", "title", "section", "excerpt", "mandate_summary", "keywords"],
            id_field="regulation_id"
        )

    # -------------------------------------------------------------
    # 1. Historical Case Retrieval
    # -------------------------------------------------------------

    def retrieve_historical_cases(
        self,
        query_text: str,
        customer_id: Optional[str] = None,
        card_id: Optional[str] = None,
        pattern: Optional[str] = None,
        outcome: Optional[str] = None,
        top_k: int = 5
    ) -> List[HistoricalCaseMatch]:
        """
        Retrieves relevant historical cases using hybrid BM25 + metadata boosts.
        Ensures both confirmed fraud and cleared precedent can be discovered.
        """
        scored_indices = self.cases_index.score(query_text)
        scores_by_idx = dict(scored_indices)

        matches: List[HistoricalCaseMatch] = []

        # Iterate through candidates with boosting
        for idx, doc in enumerate(self.closed_cases_list):
            base_score = scores_by_idx.get(idx, 0.0)
            reasons = []

            # Exact customer match boost
            if customer_id and doc["customer_id"] == customer_id:
                base_score += 5.0
                reasons.append(f"Same customer {customer_id}")

            # Exact card match boost
            if card_id and doc["card_id"] == card_id:
                base_score += 4.0
                reasons.append(f"Same card {card_id}")

            # Exact pattern match boost
            if pattern and doc["pattern"] == pattern:
                base_score += 3.0
                reasons.append(f"Matching pattern '{pattern}'")

            # Filter by outcome if requested
            if outcome and doc["outcome"] != outcome:
                continue

            if base_score > 0.0:
                if not reasons:
                    reasons.append("Lexical BM25 similarity on case notes and characteristics")

                matches.append(
                    HistoricalCaseMatch(
                        case_id=doc["case_id"],
                        customer_id=doc["customer_id"],
                        card_id=doc["card_id"],
                        outcome=doc["outcome"],
                        pattern=doc["pattern"],
                        exposure_usd=float(doc["exposure_usd"]),
                        relevance_score=round(base_score, 3),
                        similarity_reasons=reasons,
                        actions_taken=str(doc.get("actions_taken", "")),
                        analyst_notes=str(doc.get("analyst_notes", ""))
                    )
                )

        matches.sort(key=lambda x: x.relevance_score, reverse=True)
        return matches[:top_k]

    # -------------------------------------------------------------
    # 2. Policy Rule Retrieval
    # -------------------------------------------------------------

    def retrieve_applicable_policies(
        self,
        query_text: str,
        detected_patterns: Optional[List[str]] = None,
        has_shared_devices: bool = False,
        exposure_usd: float = 0.0,
        model_risk_score: float = 0.0,
        top_k: int = 5
    ) -> List[PolicyRuleMatch]:
        """
        Retrieves applicable bank policy rules (R1 - R10) based on graph evidence signals.
        """
        scored = self.policy_index.score(query_text)
        scores_by_id = {self.corpus.policy_rules[idx]["rule_id"]: score for idx, score in scored}

        scored_policy_matches = []
        patterns = [str(p).lower() for p in (detected_patterns or [])]

        for rule in self.corpus.policy_rules:
            rid = rule["rule_id"]
            score = scores_by_id.get(rid, 0.0)
            trigger_ev = []

            # Specific graph-driven triggers
            if rid == "R1" and (model_risk_score < 0.70 or "weak_signal" in query_text):
                score += 4.0
                trigger_ev.append(f"Model risk score {model_risk_score:.2f} requires verification before blocking.")

            if rid == "R5" and "card_testing" in patterns:
                score += 5.0
                trigger_ev.append("Card testing sequence detected on card (micro-authorizations burst).")

            if rid == "R6" and has_shared_devices:
                score += 6.0
                trigger_ev.append("Device profile shared across multiple customer accounts.")

            if rid == "R8" and exposure_usd > 500.0:
                score += 3.5
                trigger_ev.append(f"Total exposure (${exposure_usd:.2f}) exceeds $500 threshold requiring escalation.")

            if rid == "R7" and "recurring" in query_text:
                score += 3.0
                trigger_ev.append("Historical baseline established in home region or recurring merchant.")

            if score > 0.0:
                if not trigger_ev:
                    trigger_ev.append(f"Matched rule criteria on investigative context: {rule['name']}")

                scored_policy_matches.append(
                    (
                        score,
                        PolicyRuleMatch(
                            rule_id=rid,
                            name=rule["name"],
                            description=rule["description"],
                            triggering_evidence=trigger_ev,
                            applicable_condition=rule["condition"],
                            recommended_actions=rule["actions"],
                            approval_level=rule["approval"],
                            source_ref="Bank Fraud Policy Manual (Rules R1-R10)"
                        )
                    )
                )

        scored_policy_matches.sort(key=lambda x: x[0], reverse=True)
        return [match for _, match in scored_policy_matches[:top_k]]

    # -------------------------------------------------------------
    # 3. Regulatory Reference Retrieval
    # -------------------------------------------------------------

    def retrieve_regulatory_references(
        self,
        query_text: str,
        exposure_usd: float = 0.0,
        is_online: bool = True,
        top_k: int = 3
    ) -> List[RegulatoryReferenceMatch]:
        """
        Retrieves regulatory compliance standards (FinCEN SAR, Reg E, PCI Zero Liability, NIST).
        """
        scored = self.reg_index.score(query_text)
        scores_by_id = {self.corpus.regulatory_references[idx]["regulation_id"]: score for idx, score in scored}

        scored_reg_matches = []
        q_lower = query_text.lower()

        for reg in self.corpus.regulatory_references:
            rid = reg["regulation_id"]
            score = scores_by_id.get(rid, 0.0)

            # Rule-based applicability triggers
            if "FINCEN" in rid and (exposure_usd >= 1000.0 or "sar" in q_lower or "report" in q_lower):
                score += 4.0

            if "REG-E" in rid and (is_online or "customer_report" in q_lower or "unauthorized" in q_lower or "dispute" in q_lower):
                score += 3.5

            if "PCI" in rid and (is_online or "fraud" in q_lower or "out_of_region" in q_lower):
                score += 3.0

            if "NIST" in rid and ("step up" in q_lower or "verify" in q_lower or "customer_report" in q_lower):
                score += 3.0

            if "FFIEC" in rid and ("shared" in q_lower or "velocity" in q_lower or "undocumented" in q_lower or "anomaly" in q_lower):
                score += 3.5

            if score > 0.0:
                scored_reg_matches.append(
                    (
                        score,
                        RegulatoryReferenceMatch(
                            regulation_id=rid,
                            title=reg["title"],
                            section=reg["section"],
                            excerpt=reg["excerpt"],
                            applicability=f"Applicable to investigation when exposure is ${exposure_usd:.2f} (Channel: {'Online' if is_online else 'In-Person'})",
                            mandate_summary=reg["mandate_summary"]
                        )
                    )
                )

        scored_reg_matches.sort(key=lambda x: x[0], reverse=True)
        return [match for _, match in scored_reg_matches[:top_k]]
