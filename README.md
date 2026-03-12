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

## This Repository

This repo is backend-only.

- Frontend project URL (placeholder): https://your-frontend-url.example
- Live deployed frontend URL (placeholder): https://your-live-frontend.example

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
