from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TimestampResult(BaseModel):
    document_id: str
    start_sec: float
    end_sec: float
    preview: str


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    summary: str
    created_at: datetime


class UploadResponse(BaseModel):
    document: DocumentOut
    chunks_indexed: int


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=3000)
    document_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=4, ge=1, le=10)


class ChatResponse(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    timestamps: list[TimestampResult] = Field(default_factory=list)

