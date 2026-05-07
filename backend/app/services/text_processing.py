import re
from dataclasses import dataclass


@dataclass(slots=True)
class TextChunk:
    text: str
    start_sec: float | None = None
    end_sec: float | None = None


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    normalized = normalize_whitespace(text)
    if not normalized:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", normalized) if s.strip()]


def chunk_text(text: str, chunk_size: int = 140, overlap: int = 24) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in range [0, chunk_size)")

    normalized = normalize_whitespace(text)
    if not normalized:
        return []

    words = normalized.split(" ")
    chunks: list[TextChunk] = []
    index = 0

    while index < len(words):
        end = min(index + chunk_size, len(words))
        content = " ".join(words[index:end]).strip()
        if content:
            chunks.append(TextChunk(text=content))
        if end >= len(words):
            break
        index = end - overlap

    return chunks


def summarize_text(text: str, max_sentences: int = 3) -> str:
    normalized = normalize_whitespace(text)
    if not normalized:
        return ""
    sentences = split_sentences(normalized)
    if sentences:
        summary = " ".join(sentences[:max_sentences])
    else:
        summary = " ".join(normalized.split(" ")[:40])
    if len(summary) < len(normalized):
        return f"{summary.rstrip('.')}..."
    return summary


def create_timed_chunks(transcript: str, seconds_per_chunk: float = 30.0) -> list[TextChunk]:
    chunks = chunk_text(transcript, chunk_size=110, overlap=20)
    timed_chunks: list[TextChunk] = []
    for idx, chunk in enumerate(chunks):
        start = round(idx * seconds_per_chunk, 2)
        end = round(start + seconds_per_chunk, 2)
        timed_chunks.append(TextChunk(text=chunk.text, start_sec=start, end_sec=end))
    return timed_chunks

