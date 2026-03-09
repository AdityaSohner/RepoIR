---
title: RepoIR Engine
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# RepoIR: Privacy-First AI Search Engine

RepoIR is a powerful, secure AI search gateway designed for developers and privacy-conscious users. It allows you to ingest files from Google Drive, web URLs, and raw text snippets while maintaining full control over your data.

## 🚀 Quick Start
1. Access the built-in testing panel at `/hub`.
2. Connect your Google Drive using your Vault Secret.
3. Search your files with semantic intelligence.

## 🛠️ Tech Stack
- **Backend**: FastAPI (Python)
- **AI**: SambaNova (Meta-Llama), Sentence-Transformers
- **OCR**: Tesseract
- **Vector DB**: FAISS + SQLite FTS5

## 🔒 Security
- Standard JWT Authentication
- AES-256 Vault Encryption for cloud storage
- Ephemeral, privacy-first processing
