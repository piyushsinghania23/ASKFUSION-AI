from collections.abc import Generator

from app.config import get_settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - import guard for constrained environments
    OpenAI = None


def build_context_snippet(chunks: list[str], max_chars: int = 5000) -> str:
    merged = "\n\n".join(chunks)
    return merged[:max_chars]


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        if self.settings.enable_openai and self.settings.openai_api_key and OpenAI is not None:
            self._client = OpenAI(api_key=self.settings.openai_api_key)

    def generate_answer(self, question: str, context_chunks: list[str]) -> str:
        if self._client is None:
            return self._fallback_answer(question, context_chunks)
        try:
            return self._openai_answer(question, context_chunks)
        except Exception:
            return self._fallback_answer(question, context_chunks)

    def stream_answer(self, question: str, context_chunks: list[str]) -> Generator[str, None, None]:
        if self._client is None:
            yield from self._fallback_stream(question, context_chunks)
            return
        try:
            context = build_context_snippet(context_chunks)
            stream = self._client.chat.completions.create(
                model=self.settings.chat_model,
                stream=True,
                messages=[
                    {
                        "role": "system",
                        "content": "You answer questions using only the provided context and mention uncertainty clearly.",
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion:\n{question}",
                    },
                ],
            )
            for event in stream:
                if not event.choices:
                    continue
                delta = event.choices[0].delta
                text = getattr(delta, "content", None)
                if text:
                    yield text
        except Exception:
            yield from self._fallback_stream(question, context_chunks)

    def _openai_answer(self, question: str, context_chunks: list[str]) -> str:
        context = build_context_snippet(context_chunks)
        response = self._client.chat.completions.create(
            model=self.settings.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are ASKFUSION AI. Answer with concise factual details from the context.",
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion:\n{question}",
                },
            ],
        )
        message = response.choices[0].message.content
        return message or self._fallback_answer(question, context_chunks)

    @staticmethod
    def _fallback_answer(question: str, context_chunks: list[str]) -> str:
        if not context_chunks:
            return (
                "I could not find enough context in the uploaded files to answer that yet. "
                "Upload more content or ask a narrower question."
            )
        strongest = context_chunks[0]
        trimmed = strongest[:500]
        return (
            f"Based on the indexed content, the most relevant section says:\n\n{trimmed}\n\n"
            f"Question interpreted as: {question}"
        )

    def _fallback_stream(self, question: str, context_chunks: list[str]) -> Generator[str, None, None]:
        answer = self._fallback_answer(question, context_chunks)
        for token in answer.split(" "):
            yield token + " "

