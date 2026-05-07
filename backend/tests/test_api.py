def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_list_and_summary_flow(client):
    upload = client.post(
        "/api/upload",
        files={"file": ("notes.pdf", b"Alpha topic. Beta topic. Gamma topic.", "application/pdf")},
    )
    assert upload.status_code == 201
    payload = upload.json()
    document_id = payload["document"]["id"]
    assert payload["chunks_indexed"] >= 1

    documents = client.get("/api/documents")
    assert documents.status_code == 200
    assert len(documents.json()) == 1

    summary = client.get(f"/api/documents/{document_id}/summary")
    assert summary.status_code == 200
    assert "Alpha topic" in summary.json()["summary"]


def test_upload_rejects_invalid_and_empty_file(client):
    invalid = client.post(
        "/api/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert invalid.status_code == 400
    assert "Unsupported file type" in invalid.json()["detail"]

    empty = client.post(
        "/api/upload",
        files={"file": ("blank.pdf", b"", "application/pdf")},
    )
    assert empty.status_code == 400
    assert "empty" in empty.json()["detail"].lower()


def test_upload_rejects_too_large_when_limit_is_low(client):
    from app.config import get_settings

    settings = get_settings()
    previous = settings.max_upload_size_mb
    settings.max_upload_size_mb = 0
    try:
        response = client.post(
            "/api/upload",
            files={"file": ("oversized.pdf", b"tiny-but-over-limit", "application/pdf")},
        )
    finally:
        settings.max_upload_size_mb = previous

    assert response.status_code == 413


def test_chat_and_timestamps_for_media_file(client):
    upload = client.post(
        "/api/upload",
        files={"file": ("meeting.mp3", b"binary", "audio/mpeg")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["document"]["id"]

    chat = client.post(
        "/api/chat",
        json={"question": "What is this file about?", "document_ids": [document_id], "top_k": 3},
    )
    assert chat.status_code == 200
    body = chat.json()
    assert body["answer"]
    assert len(body["citations"]) >= 1

    timestamps = client.get(f"/api/documents/{document_id}/timestamps", params={"topic": "transcript"})
    assert timestamps.status_code == 200
    assert len(timestamps.json()) >= 1

    media = client.get(f"/api/documents/{document_id}/media")
    assert media.status_code == 200
    assert media.headers["content-type"].startswith("audio/")


def test_not_found_and_empty_branches(client):
    missing_summary = client.get("/api/documents/missing-id/summary")
    assert missing_summary.status_code == 404

    missing_timestamps = client.get("/api/documents/missing-id/timestamps", params={"topic": "x"})
    assert missing_timestamps.status_code == 404

    missing_media = client.get("/api/documents/missing-id/media")
    assert missing_media.status_code == 404

    chat_no_docs = client.post("/api/chat", json={"question": "hello", "document_ids": []})
    assert chat_no_docs.status_code == 200
    assert "Upload a file first" in chat_no_docs.json()["answer"]


def test_timestamps_returns_empty_when_document_has_no_chunks(client):
    from app.db import SessionLocal
    from app.models import Document

    db = SessionLocal()
    doc = Document(
        filename="orphan.pdf",
        mime_type="application/pdf",
        file_type="pdf",
        stored_path="backend/data/uploads/orphan.pdf",
        summary="none",
        transcript="",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    doc_id = doc.id
    db.close()

    response = client.get(f"/api/documents/{doc_id}/timestamps", params={"topic": "anything"})
    assert response.status_code == 200
    assert response.json() == []

    non_media = client.get(f"/api/documents/{doc_id}/media")
    assert non_media.status_code == 400


def test_chat_stream_returns_sse(client):
    client.post(
        "/api/upload",
        files={"file": ("deck.pdf", b"Streaming response test content.", "application/pdf")},
    )
    response = client.post(
        "/api/chat/stream",
        json={"question": "Summarize this", "document_ids": [], "top_k": 2},
    )
    assert response.status_code == 200
    text = response.text
    assert "data: " in text
    assert "[DONE]" in text
