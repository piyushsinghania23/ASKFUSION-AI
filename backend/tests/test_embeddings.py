from app.services.embeddings import EmbeddingService, cosine_similarity


def test_cosine_similarity_basics():
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_hash_embedding_deterministic():
    vector_a = EmbeddingService._hash_embedding("Alpha beta alpha")
    vector_b = EmbeddingService._hash_embedding("Alpha beta alpha")
    vector_c = EmbeddingService._hash_embedding("Completely different")
    assert vector_a == vector_b
    assert vector_a != vector_c
    assert len(vector_a) == 96


def test_embed_many_fallback_without_openai():
    service = EmbeddingService()
    vectors = service.embed_many(["hello world", "hello there"])
    assert len(vectors) == 2
    assert len(vectors[0]) == len(vectors[1]) == 96

