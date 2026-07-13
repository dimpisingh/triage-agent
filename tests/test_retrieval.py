from app.ingestion.chunker import chunk_document


def test_chunk_document_splits_on_headers():
    text = "# Section A\ncontent a\n\n# Section B\ncontent b"
    chunks = chunk_document(text, source="test.md")
    assert len(chunks) == 2
    assert "Section A" in chunks[0].text
    assert "Section B" in chunks[1].text


def test_chunk_document_sliding_window_for_long_section():
    long_section = "# Big Section\n" + " ".join(["word"] * 2000)
    chunks = chunk_document(long_section, source="test.md", max_words=800)
    assert len(chunks) > 1
    for c in chunks:
        assert c.metadata["word_count"] <= 900  # allows header overhead


def test_chunk_ids_are_unique():
    text = "# A\nfoo\n\n# B\nbar\n\n# C\nbaz"
    chunks = chunk_document(text, source="test.md")
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
