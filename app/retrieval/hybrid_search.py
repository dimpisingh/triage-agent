"""
Hybrid retrieval: BM25 (keyword/exact-match — critical for stack traces,
error codes, class names) fused with vector similarity (semantic — critical
for "what usually causes this kind of failure" reasoning), then a light
rerank pass.

Fusion strategy: reciprocal rank fusion (RRF). It's simple, doesn't require
score normalization across two different scales (BM25 scores and cosine
distances aren't comparable), and is the standard baseline used in
production hybrid-search systems before reaching for a learned reranker.
"""
from rank_bm25 import BM25Okapi

from app.retrieval.vector_store import VectorStore


class HybridSearcher:
    def __init__(self, vector_store: VectorStore, corpus: list[dict]):
        """
        corpus: list of {"chunk_id", "text", "source"} — kept in memory for
        BM25 indexing. For a larger corpus this would be a proper inverted
        index (Elasticsearch/OpenSearch) rather than in-process BM25.
        """
        self.vector_store = vector_store
        self.corpus = corpus
        self._id_to_doc = {c["chunk_id"]: c for c in corpus}
        tokenized = [c["text"].lower().split() for c in corpus]
        self.bm25 = BM25Okapi(tokenized) if tokenized else None

    def _bm25_search(self, query: str, top_k: int) -> list[str]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(query.lower().split())
        ranked = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_k]
        return [self.corpus[i]["chunk_id"] for i in ranked]

    def _vector_search(self, query: str, top_k: int) -> list[str]:
        results = self.vector_store.query(query, top_k=top_k)
        return [r["chunk_id"] for r in results]

    def search(self, query: str, top_k: int = 5, rrf_k: int = 60) -> list[dict]:
        bm25_ids = self._bm25_search(query, top_k=top_k * 2)
        vector_ids = self._vector_search(query, top_k=top_k * 2)

        # Reciprocal Rank Fusion: score = sum(1 / (rrf_k + rank))
        fused_scores: dict[str, float] = {}
        for rank, chunk_id in enumerate(bm25_ids):
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (
                rrf_k + rank + 1
            )
        for rank, chunk_id in enumerate(vector_ids):
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (
                rrf_k + rank + 1
            )

        ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)[:top_k]

        results = []
        for chunk_id in ranked_ids:
            doc = self._id_to_doc.get(chunk_id)
            if doc:
                results.append(
                    {
                        "chunk_id": chunk_id,
                        "text": doc["text"],
                        "source": doc["source"],
                        "score": fused_scores[chunk_id],
                    }
                )
        return results
