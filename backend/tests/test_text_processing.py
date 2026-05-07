import pytest

from app.services.text_processing import (
    chunk_text,
    create_timed_chunks,
    normalize_whitespace,
    split_sentences,
    summarize_text,
)


def test_normalize_and_split_sentences():
    text = "Hello   world.  This is a test!\nNew line?"
    assert normalize_whitespace(text) == "Hello world. This is a test! New line?"
    assert split_sentences(text) == ["Hello world.", "This is a test!", "New line?"]


def test_chunk_text_with_overlap():
    text = " ".join(f"w{i}" for i in range(20))
    chunks = chunk_text(text, chunk_size=8, overlap=2)
    assert len(chunks) == 3
    assert chunks[0].text.startswith("w0 w1")
    assert "w6 w7" in chunks[0].text
    assert chunks[1].text.startswith("w6 w7")


def test_chunk_text_validations():
    with pytest.raises(ValueError):
        chunk_text("a b c", chunk_size=0, overlap=0)
    with pytest.raises(ValueError):
        chunk_text("a b c", chunk_size=5, overlap=5)
    assert chunk_text("   ") == []


def test_summarize_text_behaviour():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    summary = summarize_text(text, max_sentences=2)
    assert summary.startswith("First sentence. Second sentence.")
    assert summary.endswith("...")


def test_create_timed_chunks():
    transcript = " ".join(["topic"] * 300)
    chunks = create_timed_chunks(transcript, seconds_per_chunk=15.0)
    assert len(chunks) >= 2
    assert chunks[0].start_sec == 0.0
    assert chunks[0].end_sec == 15.0
    assert chunks[1].start_sec == 15.0

