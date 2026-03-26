# RepoIR – Privacy-First AI Search Engine

> An advanced, privacy-first AI search gateway designed for developers and privacy-conscious users. Securely ingest, auto-categorize, and semantically search through a multimodal array of personal data — while maintaining complete ownership and encryption of your data.

---

## Features

### Multi-Modal Data Ingestion & Cloud Syncing

- **Diverse Sources** — Upload PDFs, DOCX, images (JPG/PNG), web URLs, and raw text snippets.
- **Encrypted Google Drive Vault** — OAuth integration creates a secured "Cloud Vault" that auto-syncs files and fetches native high-res thumbnails directly from Google Drive.
- **Asynchronous Processing** — Ingestion workloads (OCR, chunking, vectorization) run on background workers so the API and UI stay fast.
- **OCR Integration** — Tesseract OCR extracts text from images, making visual data fully searchable alongside text.

### Two-Stage Intelligent Semantic Search

| Stage | What Happens |
|-------|-------------|
| **1 — Hybrid Retrieval** | Combines BM25 keyword search (SQLite FTS5) with dense vector search (FAISS + Sentence-Transformers), merged via **Reciprocal Rank Fusion (RRF)**. |
| **2 — Re-Ranking & LLM Filtering** | Applies filename-boosting heuristics and pipes candidates through **SambaNova Meta-Llama 3.1 8B** as a strict relevance filter. Uses **Anchor-Chunk Voting** (cosine similarity weighted toward document start/end) for better context understanding. |

### Privacy & Security

- **Local-First Indexing** — Vector chunking (FAISS) and metadata indexing (SQLite) happen locally and ephemerally.
- **JWT Authentication** — Standard token-based auth with Google OAuth verification.
- **AES-256 Vault Encryption** — Cloud-stored data is encrypted at rest.

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| **Backend** | Python, FastAPI, AsyncIO |
| **Vector & Database** | FAISS (Facebook AI Similarity Search), SQLite with FTS5 |
| **AI / ML** | sentence-transformers (`all-MiniLM-L6-v2`), SambaNova Cloud API (`Meta-Llama-3.1-8B-Instruct`), NumPy |
| **Computer Vision** | Tesseract OCR |
| **Integrations** | Google Drive API (OAuth 2.0) |

---

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (v18+) or [Bun](https://bun.sh/)

### Installation

```bash
# Clone the repository
git clone https://github.com/AdityaSohner/RepoIR.git
cd RepoIR

# Install dependencies
npm install
# or
bun install

# Start the dev server
npm run dev
# or
bun dev
```

The frontend will be available at `http://localhost:5173` (default Vite port).

> **Note:** The frontend connects to the live RepoIR backend hosted on Hugging Face Spaces. No local backend setup is required to run the UI.

---

## Project Structure

```
├── public/              # Static assets
├── src/
│   ├── components/      # React components (UI + feature)
│   │   └── ui/          # shadcn/ui primitives
│   ├── contexts/        # React context providers (Auth, App state)
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # API service layer & utilities
│   ├── pages/           # Route-level page components
│   └── test/            # Test setup & specs
├── backend.txt          # Backend API documentation
└── vite.config.ts       # Vite configuration
```

---

## License

This project is proprietary. All rights reserved.
