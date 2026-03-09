# RepoIR: Final Frontend-Oriented Development & Deployment Roadmap

This document outlines the final phase of development to move **RepoIR** from a core engine to a production-ready, multi-user web application capable of being deployed on Docker and Hugging Face Spaces.

---

## 🚀 Phase 1: Authentication & User Workspace
*Goal: Move from a single sandbox to a secure, multi-tenant system.*

### Features:
- **User Identity**: Implement `POST /v1/auth/signup` and `POST /v1/auth/login` using JWT (JSON Web Tokens).
- **Secure Encrypted Storage**: Passwords hashed using `bcrypt` or `Argon2`.
- **Tenant Isolation**: Each user gets a dedicated directory in `data/users/{user_id}/` for their specific database, FAISS index, and files.
- **Frontend Readiness**: Add CORS (Cross-Origin Resource Sharing) middleware to allow browser-based React/Next.js apps to connect.

---

## 📂 Phase 2: Advanced File Management
*Goal: Scalable, UI-friendly file interactions.*

### Features:
- **Batch Upload**: Support `multipart/form-data` with multiple files in a single request (`POST /v1/ingest/local`).
- **File Renaming**: `PATCH /v1/files/{object_id}` to update naming without affecting semantic indexing.
- **Robust Deletion**: `DELETE /v1/files/{object_id}` now cleans up all four layers:
    1. SQL Metadata (`objects` table).
    2. Vector Mapping (`vectors` table).
    3. Text Chunks (FTS5).
    4. FAISS Binary Index (requires rebuilding the index if IDs shifted, or marking as deleted).
- **Background Jobs**: Use `FastAPI.BackgroundTasks` or `Celery` to ensure multiple uploads don't freeze the API.

---

## 📊 Phase 3: Analytics & Activity Tracker
*Goal: Provide a rich dashboard experience with metrics and history.*

### Features:
- **Storage Analytics**: `GET /v1/stats/storage`
    - Calculate total size and item count per type: `doc`, `url`, `txt`, `image`.
    - Returns JSON structure for a Pie Chart UI.
- **Activity Log**: `GET /v1/stats/activity`
    - A centralized event stream of "Upload", "Rename", "Delete", and "Categorize" events.
- **Quick Stats**: Dashboard-ready summary (Total Files, Total Categories, Last Sync Time).

---

## 🐳 Phase 4: Production Deployment (Docker & Hugging Face)
*Goal: Portability and one-click deployment.*

### Features:
- **Dockerization**:
    - Multi-stage `Dockerfile` optimizing for Python and C++ dependencies (FAISS, Pytesseract).
    - Lightweight `debian-slim` or `alpine` base image.
- **Environment Management**: Configuration via `.env` files for API keys (Jina, SambaNova) and model names.
- **Hugging Face Spaces**:
    - Integration for persistent storage (Hugging Face Datasets or Model Repos for the vector files).
    - UI integration (Streamlit or Gradio for a demo, or custom React build).
- **CI/CD**: GitHub Actions to auto-build and push images to Hf/DockerHub.

---

## ✅ Final Feature Checklist (Frontend Oriented)

| Category | Feature | Status |
| :--- | :--- | :--- |
| **Auth** | Sign Up & JWT Login | ⏳ Planned |
| **Auth** | User-specific storage isolation | ⏳ Planned |
| **Files** | Multiple concurrent file uploads | ⏳ Planned |
| **Files** | File Renaming (display name) | ✅ Done |
| **Files** | Robust File Deletion | ✅ Done (Architecture) |
| **Stats** | Storage space by type (Doc, URL, etc) | ⏳ Planned |
| **Stats** | Activity Log / History | ⏳ Planned |
| **Deploy** | `Dockerfile` for backend + frontend | ⏳ Planned |
| **Deploy** | Hugging Face Persistent Storage Script | ⏳ Planned |

---

## �️ Implementation Priority
1. **Dockerization (Now)**: Ensures the environment is stable for everyone.
2. **User Identity**: Essential for multi-tenant "Dashboard" testing.
3. **Analytics API**: Provides data for the "Stats" and "Recent Activity" cards on the frontend.
4. **Hugging Face Push**: Final delivery step.
