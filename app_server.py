import io
import os
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Security, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from dotenv import load_dotenv

# Load environment variables at the very beginning
load_dotenv()
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from typing import List, Optional

from app.ai.pipeline.ingestion_pipeline import IngestionPipeline
from app.ai.pipeline.search_pipeline import SearchPipeline
from app.storage.db_store import DBStore
from app.storage.gdrive_store import GDriveManager
from app.storage.encryption_manager import EncryptionManager
from app.storage.faiss_store import FAISSStore
from app.ai.embeddings.text_embedder import TextEmbedder
from app.auth.manager import AuthManager

import numpy as np


security = HTTPBearer(auto_error=False)
app = FastAPI(title="RepoIR: Privacy-First AI Search Gateway")

@app.on_event("startup")
async def startup_event():
    print("⏳ Pre-warming AI components...")
    # Initialize the singleton instance and limit torch threads safely within the app context
    from app.ai.embeddings.text_embedder import TextEmbedder
    _initial_embedder = TextEmbedder()
    print("✅ Core AI Ready.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 5

class UserAuth(BaseModel):
    email: str
    password: str

class FileUpdate(BaseModel):
    name: str

def get_current_user(auth: Optional[HTTPAuthorizationCredentials] = Security(security), token: Optional[str] = None):
    token_val = auth.credentials if auth else token
    if not token_val:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return AuthManager.decode_token(token_val)

def get_source_type(filename: str) -> str:
    """Standardized classification of file types based on extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".txt", ".md"):
        return "text"
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
        return "image"
    if ext in (".pdf", ".docx", ".pptx", ".xlsx", ".xls"):
        return "document"
    return "document" # Fallback for unknown documents

# --- Background Workers ---

def background_worker(user_id: str, job_id: str, source: any, source_type: str, original_name: str, extension: str = None):
    db = DBStore(user_id=user_id)
    try:
        db.update_job_status(job_id, "processing")
        engine = IngestionPipeline(user_id=user_id)
        engine.ingest(source, source_type, extension, original_name)
        db.update_job_status(job_id, "completed")
    except Exception as e:
        db.update_job_status(job_id, "failed", str(e))

def cloud_background_worker(user_id: str, job_id: str, stream: io.BytesIO, source_type: str, filename: str, ext: str, password: str):
    db = DBStore(user_id=user_id)
    try:
        db.update_job_status(job_id, "scanning")
        engine = IngestionPipeline(user_id=user_id)
        object_id = f"cloud_{uuid.uuid4().hex[:8]}" 

        print(f"DEBUG UPLOAD: Starting original-file upload for {filename}")
        # Ingest for search indexing (still happens locally/offline)
        engine.ingest(stream, source_type, ext, filename, object_id=object_id, skip_local_storage=True)
        
        db.update_job_status(job_id, "uploading")
        gdrive = GDriveManager(user_id=user_id, user_password=password)
        if not gdrive.service:
            raise Exception("Google Drive not connected.")
            
        vault_id = gdrive.get_or_create_vault("RepoIR_Vault")
        
        # Upload original raw bytes (Drive will generate thumbnails for us!)
        stream.seek(0)
        file_id = gdrive.upload_to_vault(stream, filename, vault_id)
        print(f"DEBUG UPLOAD: File uploaded! ID: {file_id}")
        
        # Fetch high-res native thumbnails and icons from Drive
        meta = gdrive.service.files().get(
            fileId=file_id, 
            fields="thumbnailLink, iconLink"
        ).execute()
        
        thumbnail_url = meta.get("thumbnailLink")
        # Enhance thumbnail quality if possible (Google defaults to small)
        if thumbnail_url and "=s" in thumbnail_url:
            thumbnail_url = thumbnail_url.split("=s")[0] + "=s800"
            
        icon_url = meta.get("iconLink")

        db.update_object_cloud_info(
            object_id,
            file_path=file_id,
            thumbnail_url=thumbnail_url,
            icon_url=icon_url
        )
        
        db.log_activity(user_id, "INGEST", f"Stored {filename} in Cloud Vault (Original)")
        db.update_job_status(job_id, "completed")
        print(f"DEBUG UPLOAD: COMPLETED for {filename}")
    except Exception as e:
        print(f"❌ DEBUG UPLOAD FAILED: {str(e)}")
        db.update_job_status(job_id, "failed", str(e))

import asyncio

def _call_llm_sync(prompt: str) -> str:
    """Online SambaNova LLM call. Robust for Docker/HF."""
    import requests as req
    api_key = os.getenv("SAMBANOVA_API_KEY")
    if not api_key:
        return "" # Silently skip if no key
    
    try:
        response = req.post(
            "https://api.sambanova.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "Meta-Llama-3.1-8B-Instruct", # Efficient online model
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.1
            },
            timeout=15
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"⚠️ SambaNova LLM Error: {e}")
        return ""

async def call_llm(prompt: str) -> str:
    """Async wrapper - runs the SambaNova call in a thread."""
    return await asyncio.to_thread(_call_llm_sync, prompt)


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Pure numpy cosine similarity. Returns 0.0 on zero vectors."""
    a = np.asarray(vec_a).reshape(-1).astype(np.float32)
    b = np.asarray(vec_b).reshape(-1).astype(np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    dot_product = np.dot(a, b)
    return float(dot_product / (norm_a * norm_b))


def score_file_for_category(
    object_id: str,
    query_vector: np.ndarray,
    db: "DBStore",
    faiss_index,
    log_handle=None,
    similarity_threshold: float = 0.72,
    anchor_weight: float = 3.0,
    body_weight: float = 1.0,
) -> float:
    """
    Score a single file for belonging in a category using weighted anchor-chunk voting.
    """
    rows = db.conn.execute(
        "SELECT c.chunk_index, v.vector_id "
        "FROM chunks c JOIN vectors v ON c.chunk_id = v.chunk_id "
        "WHERE c.object_id = ? ORDER BY c.chunk_index ASC",
        (object_id,)
    ).fetchall()

    if not rows:
        return 0.0

    last_index = rows[-1]["chunk_index"]
    weighted_yes = 0.0
    weighted_total = 0.0

    for row in rows:
        chunk_index = row["chunk_index"]
        vector_id = row["vector_id"]
        is_anchor = chunk_index in (0, 1) or chunk_index == last_index
        weight = anchor_weight if is_anchor else body_weight

        try:
            stored_vec = faiss_index.reconstruct(int(vector_id))
            sim = cosine_similarity(query_vector, stored_vec)

            # Log anchor chunk similarities so we can calibrate the threshold
            if log_handle and is_anchor:
                log_handle.write(f"      [anchor c{chunk_index}] sim={sim:.4f}\n")

            weighted_total += weight
            if sim >= similarity_threshold:
                weighted_yes += weight
        except Exception as e:
            if log_handle:
                log_handle.write(f"      [ERROR] Vector {vector_id} failed: {e}\n")
            continue

    if weighted_total == 0:
        return 0.0

    effective_total = min(weighted_total, anchor_weight * 2.0)
    return weighted_yes / effective_total


# --- Auth Endpoints ---

class GoogleAuth(BaseModel):
    id_token: str

@app.post("/v1/auth/signup")
def signup(payload: UserAuth):
    user_id = AuthManager.create_user(payload.email, payload.password)
    token = AuthManager.create_access_token(user_id)
    return {"status": "success", "user_id": user_id, "token": token}

@app.post("/v1/auth/login")
def login(payload: UserAuth):
    user_id = AuthManager.authenticate_user(payload.email, payload.password)
    token = AuthManager.create_access_token(user_id)
    return {"status": "success", "user_id": user_id, "token": token}

@app.post("/v1/auth/google")
def google_auth(payload: GoogleAuth):
    id_info = AuthManager.verify_google_id_token(payload.id_token)
    user_id = AuthManager.get_or_create_google_user(id_info)
    token = AuthManager.create_access_token(user_id)
    return {"status": "success", "user_id": user_id, "token": token}

class GDriveCallback(BaseModel):
    code: str
    redirect_uri: str
    vault_password: str

@app.post("/v1/auth/gdrive/callback")
def gdrive_callback(payload: GDriveCallback, user_id: str = Depends(get_current_user)):
    gdrive = GDriveManager(user_id=user_id, user_password=payload.vault_password)
    try:
        gdrive.build_service_from_code(payload.code, payload.redirect_uri)
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/v1/config")
def get_config():
    return {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "api_base": f"http://{os.getenv('HOST', '127.0.0.1')}:{os.getenv('PORT', '8000')}"
    }

class VaultVerify(BaseModel):
    password: str

@app.post("/v1/vault/status")
def vault_status(payload: VaultVerify, user_id: str = Depends(get_current_user)):
    gdrive = GDriveManager(user_id=user_id, user_password=payload.password)
    if not os.path.exists(gdrive.token_path):
        return {"status": "not_connected"}
    if not payload.password:
        return {"status": "locked"}
    if gdrive.service:
        return {"status": "valid"}
    return {"status": "invalid"}

@app.get("/v1/vault/thumbnail/{thumb_id}")
async def get_vault_thumbnail(thumb_id: str, user_id: str = Depends(get_current_user)):
    """Proxies thumbnails from Drive to avoid CORS/Cookie blocking."""
    # We use a dummy password to get a service (thumbnails are unencrypted anyway)
    gdrive = GDriveManager(user_id=user_id, user_password="dummy_for_service")
    if not gdrive.service:
        raise HTTPException(status_code=401, detail="Drive not connected")
    
    try:
        from googleapiclient.http import MediaIoBaseDownload
        request = gdrive.service.files().get_media(fileId=thumb_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        return Response(content=fh.getvalue(), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

@app.post("/v1/vault/sync")
def sync_vault(payload: VaultVerify, user_id: str = Depends(get_current_user)):
    """Simplified Sync: Fetches native thumbnails and icons directly from Drive."""
    gdrive = GDriveManager(user_id=user_id, user_password=payload.password)
    if not gdrive.service:
        raise HTTPException(status_code=400, detail="Drive not connected or secret invalid")
    
    try:
        vault_id = gdrive.get_or_create_vault("RepoIR_Vault")

        # --- List main vault files ---
        # Fetch name, iconLink, and thumbnailLink directly
        query = f"'{vault_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
        vault_files = gdrive.service.files().list(
            q=query, 
            fields="files(id, name, iconLink, thumbnailLink)"
        ).execute().get('files', [])
        
        db = DBStore(user_id=user_id)
        local_objects = db.list_all_objects()
        local_gdrive_ids = {obj["file_path"]: obj for obj in local_objects if obj["file_path"]}
        
        sync_count = 0
        for gfile in vault_files:
            file_drive_id = gfile['id']
            # Simplify: skip the 'thumbnails' folder if sync hits it
            if gfile['name'] == 'thumbnails': continue

            cloud_icon = gfile.get('iconLink')
            cloud_thumb = gfile.get('thumbnailLink')
            
            # Enhance thumbnail resolution
            if cloud_thumb and "=s" in cloud_thumb:
                cloud_thumb = cloud_thumb.split("=s")[0] + "=s800"

            if file_drive_id not in local_gdrive_ids:
                # New file in Cloud Vault - add skeleton entry
                filename = gfile['name']
                source_type = get_source_type(filename)
                
                obj_id = f"sync_{uuid.uuid4().hex[:8]}"
                
                db.store_object(
                    obj_id, user_id, filename, source_type, ext,
                    file_path=file_drive_id, chunk_count=0, file_size=0,
                    thumbnail_url=cloud_thumb,
                    icon_url=cloud_icon
                )
                sync_count += 1
            else:
                # Existing file — update links if they changed
                obj = local_gdrive_ids[file_drive_id]
                if obj.get("thumbnail_url") != cloud_thumb or obj.get("icon_url") != cloud_icon:
                    db.update_object_cloud_info(
                        obj["object_id"],
                        file_path=file_drive_id,
                        thumbnail_url=cloud_thumb,
                        icon_url=cloud_icon
                    )
        
        return {"status": "synced", "new_files": sync_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- API Endpoints ---

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    with open("RepoIR_Developer_Hub.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/")
def health_check():
    return {"status": "online", "message": "RepoIR AI Engine Ready"}

@app.get("/hub", response_class=HTMLResponse)
def serve_hub():
    """Serves the Developer Hub testing panel directly from the backend."""
    try:
        with open("RepoIR_Developer_Hub.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<h3>Developer Hub file not found on server.</h3>"

@app.post("/v1/search")
async def search(payload: SearchQuery, user_id: str = Depends(get_current_user)):
    user_search_engine = SearchPipeline(user_id=user_id)
    results = await user_search_engine.search_async(payload.query, top_k=payload.limit)
    return {"results": results}

@app.post("/v1/ingest/local")
async def ingest_local(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    user_id: str = Depends(get_current_user)
):
    job_ids = []
    for file in files:
        job_id = str(uuid.uuid4())
        content = await file.read()
        ext = os.path.splitext(file.filename)[1].lower()
        source_type = get_source_type(file.filename)
        
        background_tasks.add_task(background_worker, user_id, job_id, io.BytesIO(content), source_type, file.filename, ext)
        job_ids.append(job_id)
    return {"status": "accepted", "job_ids": job_ids}

@app.post("/v1/ingest/cloud")
async def ingest_to_cloud_vault(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    password: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    try:
        job_ids = []
        for file in files:
            content = await file.read()
            job_id = str(uuid.uuid4())
            ext = os.path.splitext(file.filename)[1].lower()
            source_type = get_source_type(file.filename)

            background_tasks.add_task(
                cloud_background_worker, 
                user_id, job_id, io.BytesIO(content), 
                source_type, file.filename, ext, password
            )
            job_ids.append(job_id)
        return {"status": "accepted", "job_ids": job_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/ingest/url")
async def ingest_url(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    try:
        job_id = str(uuid.uuid4())
        # The URL itself is passed as the source, IngestionPipeline figures out the scraping natively
        background_tasks.add_task(background_worker, user_id, job_id, url, "url", url, None)
        return {"status": "accepted", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/ingest/text")
async def ingest_text(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    filename: Optional[str] = Form("Pasted_Snippet.txt"),
    password: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user)
):
    try:
        job_id = str(uuid.uuid4())
        content_bytes = io.BytesIO(text.encode('utf-8'))
        
        if password:
            background_tasks.add_task(
                cloud_background_worker, 
                user_id, job_id, content_bytes, 
                "text", filename, ".txt", password
            )
        else:
            background_tasks.add_task(
                background_worker, 
                user_id, job_id, content_bytes, 
                "text", filename, ".txt"
            )
            
        return {"status": "accepted", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/status/{job_id}")
def check_status(job_id: str, user_id: str = Depends(get_current_user)):
    db = DBStore(user_id=user_id)
    status = db.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status

@app.get("/v1/files")
def list_files(category_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    db = DBStore(user_id=user_id)
    return {"files": db.list_all_objects(category_id=category_id)}

@app.delete("/v1/files/{object_id}")
def delete_file(object_id: str, user_id: str = Depends(get_current_user)):
    db = DBStore(user_id=user_id)
    db.delete_object(object_id)
    db.log_activity(user_id, "DELETE", f"Deleted object {object_id}")
    return {"status": "file_deleted", "object_id": object_id}

@app.patch("/v1/files/{object_id}")
def rename_file(object_id: str, payload: FileUpdate, user_id: str = Depends(get_current_user)):
    db = DBStore(user_id=user_id)
    db.rename_object(object_id, payload.name)
    db.log_activity(user_id, "RENAME", f"Renamed to {payload.name}")
    return {"status": "file_renamed", "object_id": object_id, "new_name": payload.name}

@app.get("/v1/analytics/stats")
def get_stats(user_id: str = Depends(get_current_user)):
    db = DBStore(user_id=user_id)
    return db.get_storage_stats()

@app.get("/v1/analytics/activity")
def get_activity(user_id: str = Depends(get_current_user)):
    db = DBStore(user_id=user_id)
    return {"activity": db.get_recent_activity(limit=20)}

@app.get("/v1/files/preview")
async def preview_file(object_id: str, password: str, user_id: str = Depends(get_current_user)):
    db = DBStore(user_id=user_id)
    obj_row = db.conn.execute("SELECT * FROM objects WHERE object_id = ?", (object_id,)).fetchone()
    if not obj_row: raise HTTPException(status_code=404, detail="File not found")
    obj = dict(obj_row)
    file_id = obj["file_path"]
    if not file_id: raise HTTPException(status_code=400, detail="File not in Cloud Vault")
    try:
        gdrive = GDriveManager(user_id=user_id, user_password=password)
        # For original files, we download and stream directly
        file_stream = gdrive.download_file(file_id)
        
        # Determine MIME type
        ext = os.path.splitext(obj["source"])[1].lower()
        mime_types = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", 
            ".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        content_type = mime_types.get(ext, "application/octet-stream")
        
        headers = {"Content-Disposition": f"inline; filename=\"{obj['source']}\""}
        return StreamingResponse(io.BytesIO(file_stream.getvalue()), media_type=content_type, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Previewing Error: {str(e)}")

@app.delete("/v1/user/reset")
def reset_user_data(user_id: str = Depends(get_current_user)):
    """Wipes all indexed content and search history for the user."""
    db = DBStore(user_id=user_id)
    db.purge_user_data()
    return {"status": "success", "message": "All user search data has been purged."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

