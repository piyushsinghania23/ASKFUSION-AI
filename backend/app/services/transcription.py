from pathlib import Path

from app.config import get_settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - import guard for constrained environments
    OpenAI = None


class TranscriptionService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        if self.settings.enable_openai and self.settings.openai_api_key and OpenAI is not None:
            self._client = OpenAI(api_key=self.settings.openai_api_key)

    def transcribe(self, file_path: Path) -> str:
        if self._client is None:
            return self._fallback_transcript(file_path)

        try:
            with file_path.open("rb") as f:
                transcript = self._client.audio.transcriptions.create(
                    model=self.settings.transcription_model,
                    file=f,
                )
            text = getattr(transcript, "text", "")
            if text:
                return text
            return self._fallback_transcript(file_path)
        except Exception:
            return self._fallback_transcript(file_path)

    @staticmethod
    def _fallback_transcript(file_path: Path) -> str:
        title = file_path.stem.replace("_", " ").strip() or "uploaded media"
        return (
            f"Fallback transcript for {title}. "
            "OpenAI transcription is not configured, so this placeholder transcript was generated locally."
        )

