import hashlib
import math
import re
from collections import Counter

from app.config import get_settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - import guard for constrained environments
    OpenAI = None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        if self.settings.enable_openai and self.settings.openai_api_key and OpenAI is not None:
            self._client = OpenAI(api_key=self.settings.openai_api_key)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if self._client is None:
            return [self._hash_embedding(text) for text in texts]
        try:
            response = self._client.embeddings.create(
                model=self.settings.embedding_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception:
            return [self._hash_embedding(text) for text in texts]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    @staticmethod
    def _hash_embedding(text: str, dimensions: int = 96) -> list[float]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return [0.0] * dimensions

        frequencies = Counter(tokens)
        vector = [0.0] * dimensions

        for token, weight in frequencies.items():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            idx = int.from_bytes(digest[:4], byteorder="little") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[idx] += sign * float(weight)

        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude == 0:
            return vector
        return [v / magnitude for v in vector]

