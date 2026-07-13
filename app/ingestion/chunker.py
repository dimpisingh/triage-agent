"""
Chunking strategy for runbooks, READMEs, and past-incident postmortems.

Design choice: chunk by semantic section (markdown headers) first, then
fall back to a sliding window for sections that are still too large. Pure
fixed-size chunking splits mid-explanation and hurts grounding quality;
splitting on structure keeps each chunk coherent enough to cite on its own.
"""
import re
import uuid
from dataclasses import dataclass, field


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source: str
    metadata: dict = field(default_factory=dict)


def _split_by_headers(text: str) -> list[str]:
    # Split on markdown-style headers (#, ##, ###) while keeping the header
    # attached to its section.
    pattern = r"(?=^#{1,3}\s)"
    sections = re.split(pattern, text, flags=re.MULTILINE)
    return [s.strip() for s in sections if s.strip()]


def _sliding_window(text: str, window_size: int = 800, overlap: int = 150) -> list[str]:
    words = text.split()
    if len(words) <= window_size:
        return [text]
    chunks = []
    step = window_size - overlap
    for start in range(0, len(words), step):
        window = words[start : start + window_size]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + window_size >= len(words):
            break
    return chunks


def chunk_document(text: str, source: str, max_words: int = 800) -> list[Chunk]:
    """
    Chunk a document into retrieval-sized pieces.

    1. Split by header structure to preserve semantic boundaries.
    2. Any section still over max_words gets a sliding-window split.
    """
    sections = _split_by_headers(text) or [text]
    chunks: list[Chunk] = []

    for section in sections:
        word_count = len(section.split())
        pieces = (
            [section]
            if word_count <= max_words
            else _sliding_window(section, window_size=max_words)
        )
        for piece in pieces:
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4())[:8],
                    text=piece,
                    source=source,
                    metadata={"word_count": len(piece.split())},
                )
            )
    return chunks
