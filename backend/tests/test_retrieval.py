from app.models import Chunk
from app.services.retrieval import extract_timestamps, rank_chunks


def _chunk(text: str, embedding: list[float], start_sec=None, end_sec=None):
    return Chunk(
        document_id="doc-1",
        chunk_index=0,
        text=text,
        embedding=embedding,
        start_sec=start_sec,
        end_sec=end_sec,
    )


def test_rank_chunks_orders_by_similarity():
    chunks = [
        _chunk("a", [1.0, 0.0]),
        _chunk("b", [0.6, 0.8]),
        _chunk("c", [0.0, 1.0]),
    ]
    hits = rank_chunks([1.0, 0.0], chunks, top_k=2)
    assert len(hits) == 2
    assert hits[0].chunk.text == "a"


def test_extract_timestamps_returns_media_rows_only():
    chunks = [
        _chunk("timed", [1.0, 0.0], start_sec=12.0, end_sec=20.0),
        _chunk("not timed", [1.0, 0.0], start_sec=None, end_sec=None),
    ]
    results = extract_timestamps([1.0, 0.0], chunks, top_k=3)
    assert len(results) == 1
    assert results[0].start_sec == 12.0
    assert "timed" in results[0].preview

