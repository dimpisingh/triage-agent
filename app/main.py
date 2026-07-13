from fastapi import FastAPI

from app.agent.graph import build_triage_graph
from app.models.schemas import (
    BuildFailureEvent,
    Diagnosis,
    DiagnoseResponse,
    RetrievedChunk,
)
from app.retrieval.hybrid_search import HybridSearcher
from app.retrieval.vector_store import VectorStore

app = FastAPI(title="Triage Agent")

vector_store = VectorStore()
# In-memory corpus mirror for BM25 — see hybrid_search.py docstring for why.
# Populated via /ingest; kept simple for the demo.
_corpus: list[dict] = []
searcher = HybridSearcher(vector_store, _corpus)
graph = build_triage_graph(searcher)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest(source: str, text: str):
    from app.ingestion.chunker import chunk_document

    chunks = chunk_document(text, source=source)
    vector_store.add_chunks(chunks)
    for c in chunks:
        _corpus.append({"chunk_id": c.chunk_id, "text": c.text, "source": c.source})
    # rebuild BM25 index with the new corpus
    global searcher, graph
    searcher = HybridSearcher(vector_store, _corpus)
    graph = build_triage_graph(searcher)
    return {"ingested_chunks": len(chunks)}


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose_failure(event: BuildFailureEvent):
    result_state = graph.invoke(
        {
            "eventId": event.eventId,
            "failureType": event.failureType,
            "rawLogExcerpt": event.rawLogExcerpt,
            "affectedModule": event.affectedModule or "unknown",
        }
    )

    diagnosis = Diagnosis(
        root_cause=result_state.get("root_cause", ""),
        proposed_fix=result_state.get("proposed_fix"),
        confidence=result_state.get("confidence", 0.0),
        citations=result_state.get("citations", []),
        escalated=result_state.get("escalated", False),
        escalation_reason=result_state.get("escalation_reason"),
    )

    chunks = [
        RetrievedChunk(**c) for c in result_state.get("retrieved_chunks", [])
    ]

    return DiagnoseResponse(
        eventId=event.eventId, diagnosis=diagnosis, retrieved_chunks=chunks
    )
