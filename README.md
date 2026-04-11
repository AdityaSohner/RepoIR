# RepoIR: Privacy-First AI Search Gateway

An advanced, privacy-first AI search engine designed to index and retrieve information from a variety of personal data sources (documents, images, URLs) while maintaining a secure "Cloud Vault" on Google Drive.

> [!NOTE]
> For a deep dive into the backend architecture, endpoints, and the ingestion pipeline, see the [RepoIR Technical Study](file:///c:/Users/adity/Desktop/RepoIR/.gemini/antigravity/artifacts/RepoIR_Technical_Study.md).

---

## 🚀 Core Features

- **Multimodal Ingestion**: Supports PDFs, DOCX, TXT, Excel, JPG, PNG, URLs, and raw text snippets.
- **AI-Powered Vision**: Uses vision models to describe image content, making "a photo of a sunset" searchable by concept.
- **Encrypted Cloud Vault**: Securely stores original files in a dedicated Google Drive folder (`RepoIR_Vault`), accessible via a user-defined password.
- **Two-Stage Semantic Search**: 
  - **Stage 1**: Hybrid retrieval merging BM25 (keyword) and FAISS (semantic) results via Reciprocal Rank Fusion (RRF).
  - **Stage 2**: LLM-based relevance filtering using SambaNova-hosted Llama 3.1 8B.
- **Real-Time Analytics**: Visual dashboard for tracking storage usage, category distributions, and recent activity logs.
- **Privacy First**: Vector chunking and metadata indexing happen locally-first or within your private instance.

---

## 🛠️ Tech Stack

| Component | technologies |
| :--- | :--- |
| **Backend** | Python, FastAPI, AsyncIO |
| **Search Engine** | FAISS (Vector), SQLite FTS5 (Keyword) |
| **AI Models** | `all-MiniLM-L6-v2` (Embeddings), Llama 3.1 8B (Re-ranking) |
| **Integrations** | Google Drive API (OAuth 2.0), SambaNova API |
| **Frontend** | React, TypeScript, Vite, Tailwind CSS |

---

## 🏗️ Ingestion Pipeline Flow

1. **Extraction**: Raw text is pulled from documents, images (via OCR), or URLs.
2. **Vision Analysis**: Images are "captioned" by AI to provide searchable metadata.
3. **Normalization**: Text is cleaned and formatted into semantic blocks.
4. **Chunking**: Text is split into 300-token chunks with context-preserving overlap.
5. **Embedding**: Chunks are converted into 768-dim vectors.
6. **Indexing**: Metadata is stored in SQLite, while vectors are indexed in FAISS for fast similarity search.

---

## 📥 Getting Started (Local Development)

### 1) Clone and setup
```bash
git clone https://github.com/AdityaSohner/RepoIR.git
cd RepoIR
python -m venv env
source env/bin/activate  # Mac/Linux
# .\\env\\Scripts\\Activate.ps1 # Windows
pip install -r requirements.txt
```

### 2) Configuration
Create a `.env` file based on `.env.template`:
- `SAMBANOVA_API_KEY`: For LLM re-ranking.
- `GOOGLE_CLIENT_ID` & `SECRET`: For Drive integration.
- `JWT_SECRET_KEY`: For session management.

### 3) Start the Engine
```bash
python app_server.py
```
Default endpoint: `http://localhost:8000`

---

## 🐳 Docker Deployment

To run RepoIR in a containerized environment:
```bash
docker build -t repoir-gateway .
docker run --rm -p 8000:8000 --env-file .env repoir-gateway
```

---

## 📄 License
This project is proprietary. All rights reserved.
che-2.0).
