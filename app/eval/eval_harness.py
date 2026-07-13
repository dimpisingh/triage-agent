"""
Eval harness for the triage agent.

Reports the numbers you'd actually quote in an interview:
  - root-cause accuracy (keyword-match against golden labels — a real
    system would use an LLM-as-judge or human review for this instead)
  - citation precision (are cited chunk_ids actually in retrieved_chunks)
  - escalation rate and escalation correctness

Run: python -m app.eval.eval_harness
"""
import json
from pathlib import Path

from app.agent.graph import build_triage_graph
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.vector_store import VectorStore

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"


def load_golden_dataset() -> list[dict]:
    with open(GOLDEN_PATH) as f:
        return json.load(f)


def keyword_match_score(root_cause: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0  # nothing specific expected (e.g. deliberately ambiguous case)
    root_cause_lower = root_cause.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in root_cause_lower)
    return hits / len(expected_keywords)


def run_eval(searcher: HybridSearcher | None = None) -> dict:
    if searcher is None:
        vector_store = VectorStore()
        searcher = HybridSearcher(vector_store, corpus=[])

    graph = build_triage_graph(searcher)
    cases = load_golden_dataset()

    results = []
    for case in cases:
        state = graph.invoke(
            {
                "eventId": case["eventId"],
                "failureType": case["failureType"],
                "rawLogExcerpt": case["rawLogExcerpt"],
                "affectedModule": case.get("affectedModule", "unknown"),
            }
        )

        rc_score = keyword_match_score(
            state.get("root_cause", ""), case.get("expected_root_cause_keywords", [])
        )
        retrieved_ids = {c["chunk_id"] for c in state.get("retrieved_chunks", [])}
        citations = state.get("citations", [])
        citation_precision = (
            sum(1 for c in citations if c in retrieved_ids) / len(citations)
            if citations
            else None
        )
        expected_escalation = case.get("expect_escalation", False)
        escalation_correct = state.get("escalated", False) == expected_escalation

        results.append(
            {
                "eventId": case["eventId"],
                "root_cause_keyword_score": rc_score,
                "confidence": state.get("confidence", 0.0),
                "citation_precision": citation_precision,
                "escalated": state.get("escalated", False),
                "expected_escalation": expected_escalation,
                "escalation_correct": escalation_correct,
            }
        )

    n = len(results)
    summary = {
        "num_cases": n,
        "avg_root_cause_keyword_score": sum(r["root_cause_keyword_score"] for r in results) / n,
        "avg_confidence": sum(r["confidence"] for r in results) / n,
        "escalation_accuracy": sum(r["escalation_correct"] for r in results) / n,
        "escalation_rate": sum(r["escalated"] for r in results) / n,
    }

    return {"summary": summary, "cases": results}


if __name__ == "__main__":
    report = run_eval()
    print(json.dumps(report, indent=2))
