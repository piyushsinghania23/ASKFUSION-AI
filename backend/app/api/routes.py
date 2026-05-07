from collections.abc import Iterable

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Chunk, Document
from app.schemas import ChatRequest, ChatResponse, DocumentOut, TimestampResult, UploadResponse
from app.services.embeddings import EmbeddingService
from app.services.ingestion import IngestionService
from app.services.llm import LLMService
from app.services.retrieval import extract_timestamps, rank_chunks


router = APIRouter(prefix="/api", tags=["askfusion"])


def get_ingestion_service() -> IngestionService:
    return IngestionService()


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


def get_llm_service() -> LLMService:
    return LLMService()


def _get_chunks(db: Session, document_ids: list[str]) -> list[Chunk]:
    query = select(Chunk)
    if document_ids:
        query = query.where(Chunk.document_id.in_(document_ids))
    return list(db.scalars(query).all())


def _serialize_citations(hits: Iterable, db: Session) -> list[str]:
    doc_ids = {hit.chunk.document_id for hit in hits}
    if not doc_ids:
        return []
    docs = db.scalars(select(Document).where(Document.id.in_(doc_ids))).all()
    names = {doc.id: doc.filename for doc in docs}
    return [
        f"{names.get(hit.chunk.document_id, hit.chunk.document_id)} [chunk {hit.chunk.chunk_index}]"
        for hit in hits
    ]


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> UploadResponse:
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large.")

    mime_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload.bin"

    try:
        file_type = ingestion.detect_file_type(filename, mime_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored_path = ingestion.store_upload(filename, data)
    document, chunks_indexed = ingestion.ingest_file(
        db,
        stored_path=stored_path,
        filename=filename,
        mime_type=mime_type,
        file_type=file_type,
    )

    return UploadResponse(document=DocumentOut.model_validate(document), chunks_indexed=chunks_indexed)


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentOut]:
    documents = db.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return [DocumentOut.model_validate(doc) for doc in documents]


@router.get("/documents/{document_id}/summary")
def get_summary(document_id: str, db: Session = Depends(get_db)) -> dict:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"document_id": document_id, "summary": doc.summary}


@router.get("/documents/{document_id}/media")
def get_media(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.file_type not in {"audio", "video"}:
        raise HTTPException(status_code=400, detail="Requested document is not media.")
    return FileResponse(path=doc.stored_path, media_type=doc.mime_type, filename=doc.filename)


@router.get("/documents/{document_id}/timestamps", response_model=list[TimestampResult])
def get_timestamps(
    document_id: str,
    topic: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> list[TimestampResult]:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = list(db.scalars(select(Chunk).where(Chunk.document_id == document_id)).all())
    if not chunks:
        return []

    topic_embedding = embedding_service.embed_text(topic)
    return extract_timestamps(topic_embedding, chunks, top_k=5)


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> ChatResponse:
    chunks = _get_chunks(db, payload.document_ids)
    if not chunks:
        return ChatResponse(
            answer="No indexed content found yet. Upload a file first.",
            citations=[],
            timestamps=[],
        )

    question_embedding = embedding_service.embed_text(payload.question)
    hits = rank_chunks(question_embedding, chunks, top_k=payload.top_k)
    context = [hit.chunk.text for hit in hits]
    answer = llm_service.generate_answer(payload.question, context)
    timestamps = extract_timestamps(question_embedding, [hit.chunk for hit in hits], top_k=2)
    citations = _serialize_citations(hits, db)
    return ChatResponse(answer=answer, citations=citations, timestamps=timestamps)


@router.post("/chat/stream")
def stream_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> StreamingResponse:
    chunks = _get_chunks(db, payload.document_ids)
    question_embedding = embedding_service.embed_text(payload.question)
    hits = rank_chunks(question_embedding, chunks, top_k=payload.top_k) if chunks else []
    context = [hit.chunk.text for hit in hits]

    def event_stream():
        for token in llm_service.stream_answer(payload.question, context):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
