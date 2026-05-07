from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Chunk, Document
from app.services.embeddings import EmbeddingService
from app.services.text_processing import chunk_text, create_timed_chunks, summarize_text
from app.services.transcription import TranscriptionService


class IngestionService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()
        self.transcription_service = TranscriptionService()

    def detect_file_type(self, filename: str, mime_type: str) -> str:
        suffix = Path(filename).suffix.lower()
        if mime_type == "application/pdf" or suffix == ".pdf":
            return "pdf"
        if mime_type.startswith("audio/") or suffix in {".mp3", ".wav", ".m4a", ".aac"}:
            return "audio"
        if mime_type.startswith("video/") or suffix in {".mp4", ".mov", ".mkv", ".webm"}:
            return "video"
        raise ValueError("Unsupported file type. Please upload PDF, audio, or video files.")

    def store_upload(self, filename: str, data: bytes) -> Path:
        safe_name = Path(filename).name or "upload.bin"
        doc_dir = self.settings.uploads_dir / str(uuid4())
        doc_dir.mkdir(parents=True, exist_ok=True)
        path = doc_dir / safe_name
        path.write_bytes(data)
        return path

    def ingest_file(
        self,
        db: Session,
        *,
        stored_path: Path,
        filename: str,
        mime_type: str,
        file_type: str,
    ) -> tuple[Document, int]:
        text = self.extract_text(stored_path, file_type)
        summary = summarize_text(text)

        if file_type in {"audio", "video"}:
            chunks = create_timed_chunks(text)
        else:
            chunks = chunk_text(text, chunk_size=self.settings.chunk_size, overlap=self.settings.chunk_overlap)

        embeddings = self.embedding_service.embed_many([chunk.text for chunk in chunks]) if chunks else []

        document = Document(
            filename=filename,
            mime_type=mime_type,
            file_type=file_type,
            stored_path=str(stored_path),
            summary=summary,
            transcript=text,
        )
        db.add(document)
        db.flush()

        for idx, chunk in enumerate(chunks):
            db.add(
                Chunk(
                    document_id=document.id,
                    chunk_index=idx,
                    text=chunk.text,
                    embedding=embeddings[idx],
                    start_sec=chunk.start_sec,
                    end_sec=chunk.end_sec,
                )
            )

        db.commit()
        db.refresh(document)
        return document, len(chunks)

    def extract_text(self, file_path: Path, file_type: str) -> str:
        if file_type == "pdf":
            return self._extract_pdf(file_path)
        if file_type in {"audio", "video"}:
            return self.transcription_service.transcribe(file_path)
        return ""

    @staticmethod
    def _extract_pdf(file_path: Path) -> str:
        try:
            reader = PdfReader(str(file_path))
            return "\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
        except Exception:
            # Allows graceful handling for malformed files in local/demo environments.
            return file_path.read_text(encoding="utf-8", errors="ignore")

