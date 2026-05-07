import shutil
from pathlib import Path
from types import SimpleNamespace

from app.db import _engine_kwargs
from app.services.embeddings import EmbeddingService
from app.services.ingestion import IngestionService
from app.services.llm import LLMService, build_context_snippet
from app.services.transcription import TranscriptionService


class _FakeEmbeddings:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def create(self, **_kwargs):
        if self.should_fail:
            raise RuntimeError("embedding failure")
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2]), SimpleNamespace(embedding=[0.3, 0.4])])


class _FakeChatCompletions:
    def __init__(self, mode: str):
        self.mode = mode

    def create(self, **kwargs):
        if kwargs.get("stream"):
            if self.mode == "stream_error":
                raise RuntimeError("stream broken")
            return [
                SimpleNamespace(choices=[]),
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="hello"))]),
            ]

        if self.mode == "raise":
            raise RuntimeError("chat broken")

        content = "" if self.mode == "empty" else "OpenAI says hi"
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class _FakeTranscriptions:
    def __init__(self, mode: str):
        self.mode = mode

    def create(self, **_kwargs):
        if self.mode == "raise":
            raise RuntimeError("transcription broken")
        text = "" if self.mode == "empty" else "Transcribed speech text"
        return SimpleNamespace(text=text)


def test_engine_kwargs_non_sqlite_branch():
    assert _engine_kwargs("postgresql://user:pass@localhost/db") == {}


def test_embedding_openai_and_fallback_branches():
    service = EmbeddingService()
    service._client = SimpleNamespace(embeddings=_FakeEmbeddings(should_fail=False))
    assert service.embed_many(["a", "b"]) == [[0.1, 0.2], [0.3, 0.4]]
    assert service.embed_text("a") == [0.1, 0.2]

    service._client = SimpleNamespace(embeddings=_FakeEmbeddings(should_fail=True))
    vectors = service.embed_many(["hello"])
    assert len(vectors[0]) == 96

    zeros = EmbeddingService._hash_embedding("!!!")
    assert zeros == [0.0] * 96


def test_llm_openai_and_fallback_branches():
    service = LLMService()

    service._client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeChatCompletions("normal")))
    assert service.generate_answer("q", ["context"]) == "OpenAI says hi"

    service._client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeChatCompletions("empty")))
    answer_empty = service.generate_answer("q", ["context"])
    assert "most relevant section" in answer_empty

    service._client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeChatCompletions("raise")))
    answer_error = service.generate_answer("q", ["context"])
    assert "most relevant section" in answer_error

    snippet = build_context_snippet(["abc", "def"], max_chars=4)
    assert snippet == "abc\n"


def test_llm_stream_openai_and_error_paths():
    service = LLMService()
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeChatCompletions("normal")))
    streamed = "".join(service.stream_answer("q", ["context"]))
    assert "hello" in streamed

    service._client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeChatCompletions("stream_error")))
    fallback_stream = "".join(service.stream_answer("q", ["context"]))
    assert "Question interpreted as:" in fallback_stream


def _local_tmp_dir() -> Path:
    path = Path("backend/tests/.tmp")
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_transcription_openai_paths():
    tmp_dir = _local_tmp_dir()
    media = tmp_dir / "team_sync.mp3"
    media.write_bytes(b"binary")

    service = TranscriptionService()
    service._client = SimpleNamespace(audio=SimpleNamespace(transcriptions=_FakeTranscriptions("normal")))
    assert service.transcribe(media) == "Transcribed speech text"

    service._client = SimpleNamespace(audio=SimpleNamespace(transcriptions=_FakeTranscriptions("empty")))
    assert "Fallback transcript" in service.transcribe(media)

    service._client = SimpleNamespace(audio=SimpleNamespace(transcriptions=_FakeTranscriptions("raise")))
    assert "Fallback transcript" in service.transcribe(media)
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_ingestion_extract_unknown_type():
    tmp_dir = _local_tmp_dir()
    path = tmp_dir / "file.bin"
    path.write_text("text")
    service = IngestionService()
    assert service.extract_text(path, "unknown") == ""

    fallback_pdf = tmp_dir / "fake.pdf"
    fallback_pdf.write_text("plain text not a real pdf")
    assert "plain text" in service.extract_text(fallback_pdf, "pdf")
    shutil.rmtree(tmp_dir, ignore_errors=True)
