import chromadb
from app.config import settings
from app.ingestion.chunker import Chunk


class VectorStore:
    """Thin wrapper around a Chroma collection so the rest of the app never
    talks to Chroma's client API directly — makes it a one-file swap if you
    later move to pgvector or a managed vector DB."""

    def __init__(self):
        self.client = chromadb.HttpClient(
            host=settings.chroma_host, port=settings.chroma_port
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.collection_name
        )

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        self.collection.add(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[{"source": c.source, **c.metadata} for c in chunks],
        )

    def query(self, text: str, top_k: int = 8) -> list[dict]:
        results = self.collection.query(query_texts=[text], n_results=top_k)
        out = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
            out.append(
                {
                    "chunk_id": chunk_id,
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    # Chroma returns distance; convert to a similarity-style score
                    "score": 1.0 / (1.0 + dist),
                }
            )
        return out
