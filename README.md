# ASKFUSION AI

ASKFUSION AI is a full-stack document and multimedia Q&A platform built for the SDE-1 assignment requirements.

It supports:
- PDF, audio, and video uploads
- AI-style question answering grounded in uploaded content
- Content summarization
- Topic-to-timestamp extraction for audio/video
- One-click playback jump to relevant timestamps
- Streaming chat responses (SSE)
- Dockerized local stack with PostgreSQL + Redis
- CI with automated test coverage gate (95%+)

## Stack
- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL (Docker Compose), SQLite fallback for local/test
- AI integrations: OpenAI (chat, embeddings, transcription) with resilient local fallbacks
- Frontend: React + TypeScript + Vite
- Infra: Docker, Docker Compose, GitHub Actions

## Repository Layout
```
.
├─ backend/
│  ├─ app/
│  ├─ tests/
│  ├─ Dockerfile
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  ├─ Dockerfile
│  └─ package.json
├─ .github/workflows/ci.yml
└─ docker-compose.yml
```

## Quick Start (Docker Compose)
1. (Optional) Set your API key:
   - Windows PowerShell: `$env:OPENAI_API_KEY="your_key"` (or `$env:ASKFUSION_OPENAI_API_KEY="your_key"`)
   - macOS/Linux: `export OPENAI_API_KEY="your_key"` (or `export ASKFUSION_OPENAI_API_KEY="your_key"`)
2. Run:
   - `docker compose up --build`
3. Open:
   - Frontend: `http://localhost:5173`
   - Backend API docs: `http://localhost:8000/docs`

## Local Development

### Backend
1. `python -m pip install -r backend/requirements.txt`
2. Optional env vars:
   - `ASKFUSION_OPENAI_API_KEY` (or `OPENAI_API_KEY`)
   - `ASKFUSION_DATABASE_URL`
3. Run API:
   - `uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend`

### Frontend
1. `cd frontend`
2. `npm install`  
   If PowerShell blocks scripts (`npm.ps1 cannot be loaded`), use `npm.cmd install`.
3. `npm run dev`  
   If needed on restricted PowerShell, use `npm.cmd run dev`.

Set `VITE_API_BASE_URL` if needed (defaults to `http://localhost:8000`).

## API Endpoints
- `GET /health`
- `POST /api/upload`
- `GET /api/documents`
- `GET /api/documents/{document_id}/summary`
- `GET /api/documents/{document_id}/timestamps?topic=...`
- `GET /api/documents/{document_id}/media`
- `POST /api/chat`
- `POST /api/chat/stream` (SSE)

## Testing
Run backend tests with coverage gate:

```bash
cd backend
python -m pytest
```

Configured gate: **95% minimum coverage** (`pytest-cov`).

## Assignment Requirement Mapping
- Full-stack web app: Implemented (FastAPI + React)
- PDF/audio/video upload: Implemented
- LLM-powered Q&A: Implemented with OpenAI + local fallback
- Transcription (Whisper/OpenAI ASR path): Implemented with OpenAI + fallback
- Text + metadata persistence: Implemented (RDBMS-compatible, PostgreSQL-ready)
- Summary generation: Implemented
- Topic timestamps + playback jump: Implemented
- Dockerfile + Docker Compose: Implemented
- CI/CD via GitHub Actions: Implemented
- Automated testing with 95%+: Implemented
