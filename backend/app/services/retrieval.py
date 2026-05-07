from dataclasses import dataclass

from app.models import Chunk
from app.schemas import TimestampResult
from app.services.embeddings import cosine_similarity


@dataclass(slots=True)
class RetrievalHit:
    chunk: Chunk
    score: float


def rank_chunks(question_embedding: list[float], chunks: list[Chunk], top_k: int = 4) -> list[RetrievalHit]:
    hits = [
        RetrievalHit(chunk=chunk, score=cosine_similarity(question_embedding, chunk.embedding))
        for chunk in chunks
    ]
    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[:top_k]


def extract_timestamps(topic_embedding: list[float], chunks: list[Chunk], top_k: int = 3) -> list[TimestampResult]:
    candidates = []
    for chunk in chunks:
        if chunk.start_sec is None or chunk.end_sec is None:
            continue
        score = cosine_similarity(topic_embedding, chunk.embedding)
        candidates.append((score, chunk))
    candidates.sort(key=lambda row: row[0], reverse=True)

    results: list[TimestampResult] = []
    for _, chunk in candidates[:top_k]:
        results.append(
            TimestampResult(
                document_id=chunk.document_id,
                start_sec=float(chunk.start_sec),
                end_sec=float(chunk.end_sec),
                preview=chunk.text[:180],
            )
        )
    return results

