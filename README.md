# RepoIR Backend

Privacy-first AI search backend for multimodal personal data.

## Project Overview

RepoIR is an advanced AI search gateway designed for developers and privacy-conscious users. This repository contains the backend service that ingests, classifies, indexes, and semantically searches across personal data while preserving user ownership and encryption controls.

Core capabilities:

- Multimodal ingestion for documents, images, URLs, and text snippets.
- Google Drive integration with encrypted vault-style workflows.
- Asynchronous processing for OCR, chunking, embedding, and indexing.
- Hybrid semantic retrieval using BM25 (SQLite FTS5) + vector search (FAISS).
- Two-stage ranking with reciprocal rank fusion and LLM-based relevance filtering.
- Privacy-first architecture with local-first indexing and encrypted storage patterns.

## Deployments

| Service | URL |
|---|---|
| 🖥️ **Frontend** | https://repoir.onrender.com |
| ⚙️ **Backend API** | https://kallii17-repoir.hf.space |

## Architecture Summary

1. Ingestion Layer
- Accepts files (PDF, DOCX), images (JPG/PNG), web links, and raw text.
- Extracts text using OCR and type-specific extractors.
- Normalizes and chunks text for retrieval pipelines.

2. Retrieval Layer
- Keyword retrieval via SQLite FTS5 (BM25).
- Semantic retrieval via FAISS + sentence-transformers embeddings.
- Reciprocal Rank Fusion (RRF) to merge heterogeneous candidate lists.

3. Ranking and Intent Filtering
- Heuristic boosts (for example, filename relevance signals).
- Optional LLM relevance filtering (SambaNova-hosted Llama family model).
- Anchor-chunk-aware scoring to improve contextual fit.

4. Security Layer
- JWT-based user auth.
- Google OAuth token validation.
- Vault encryption workflows for cloud-backed assets.

## Tech Stack

- Backend: Python, FastAPI, AsyncIO
- Search/Storage: FAISS, SQLite (FTS5)
- AI/ML: sentence-transformers (all-MiniLM-L6-v2), NumPy, SambaNova API
- OCR/Vision: Tesseract OCR
- Integrations: Google Drive API (OAuth 2.0)

## Running Locally

### 1) Clone and set up environment

```bash
git clone https://github.com/AdityaSohner/RepoIR.git
cd RepoIR
python -m venv env
source env/bin/activate  # Windows PowerShell: .\\env\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

### 2) Configure environment variables

Create a `.env` file using `.env.template` as reference and set real values:

- `SAMBANOVA_API_KEY`
- `JINA_API_KEY`
- `JWT_SECRET_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

Never commit `.env`, OAuth credentials, tokens, or local databases.

### 3) Start backend

```bash
python main.py
```

Default local endpoint: `http://localhost:8000`

## Docker

Docker support is intentionally kept in this backend repository because it improves reproducibility for deployment and local onboarding.

Build and run:

```bash
docker build -t repoir-backend .
docker run --rm -p 7860:7860 --env-file .env repoir-backend
```

## API Surface (High Level)

- Authentication: signup/login/token issuance and validation
- Ingestion: upload documents/images/URLs/text
- Search: hybrid semantic + keyword retrieval endpoints
- Cloud Vault: Google Drive OAuth and synchronized object operations

Refer to backend route handlers in `app_server.py` for endpoint details.

## API Endpoints

Base URL (local): `http://localhost:8000`

Authentication routes:

- `POST /v1/auth/signup`
- `POST /v1/auth/login`
- `POST /v1/auth/google`
- `POST /v1/auth/gdrive/callback`

Search and ingestion routes:

- `POST /v1/search`
- `POST /v1/ingest/local`
- `POST /v1/ingest/cloud`
- `POST /v1/ingest/url`
- `POST /v1/ingest/text`
- `GET /v1/status/{job_id}`

Files and analytics routes:

- `GET /v1/files`
- `PATCH /v1/files/{object_id}`
- `DELETE /v1/files/{object_id}`
- `GET /v1/files/preview?object_id=...&password=...`
- `GET /v1/analytics/stats`
- `GET /v1/analytics/activity`

Vault and config routes:

- `GET /v1/config`
- `POST /v1/vault/status`
- `POST /v1/vault/sync`
- `GET /v1/vault/thumbnail/{thumb_id}`

Service routes:

- `GET /`
- `GET /hub`
- `GET /dashboard`

Sample requests:

```bash
# 1) Signup
curl -X POST "http://localhost:8000/v1/auth/signup" \
	-H "Content-Type: application/json" \
	-d '{"email":"you@example.com","password":"strong-password"}'
```

```bash
# 2) Login
curl -X POST "http://localhost:8000/v1/auth/login" \
	-H "Content-Type: application/json" \
	-d '{"email":"you@example.com","password":"strong-password"}'
```

```bash
# 3) Semantic search (replace TOKEN)
curl -X POST "http://localhost:8000/v1/search" \
	-H "Authorization: Bearer TOKEN" \
	-H "Content-Type: application/json" \
	-d '{"query":"find my OCR receipts","limit":5}'
```

```bash
# 4) Ingest local file(s)
curl -X POST "http://localhost:8000/v1/ingest/local" \
	-H "Authorization: Bearer TOKEN" \
	-F "files=@./sample.pdf"
```

```bash
# 5) Ingest URL
curl -X POST "http://localhost:8000/v1/ingest/url" \
	-H "Authorization: Bearer TOKEN" \
	-F "url=https://example.com"
```

```bash
# 6) Ingest pasted text
curl -X POST "http://localhost:8000/v1/ingest/text" \
	-H "Authorization: Bearer TOKEN" \
	-F "text=This is a note to index" \
	-F "filename=note.txt"
```

```bash
# 7) Track job status
curl -X GET "http://localhost:8000/v1/status/JOB_ID" \
	-H "Authorization: Bearer TOKEN"
```

```bash
# 8) List indexed files
curl -X GET "http://localhost:8000/v1/files" \
	-H "Authorization: Bearer TOKEN"
```

## Security Notes

- Keep OAuth and API keys only in environment variables.
- Rotate keys immediately if previously exposed.
- Use strong JWT secrets in production.
- Do not commit `credentials.json`, token files, or `data/` contents.

## Project Status

Active backend development with focus on:

- Retrieval relevance quality
- Secure cloud sync workflows
- Production hardening and observability

## License

Add your preferred license here (for example, MIT or Apache-2.0).
