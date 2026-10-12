import io
import os
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Security, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
import requests
import faiss
from urllib.parse import quote
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
from app.storage.manager import StorageManager

import numpy as np


security = HTTPBearer(auto_error=False)
app = FastAPI(title="RepoIR: Privacy-First AI Search Gateway")

@app.on_event("startup")
async def startup_event():
    print("[*] Pre-warming AI components...")
    # Initialize the singleton instance and limit torch threads safely within the app context
    from app.ai.embeddings.text_embedder import TextEmbedder
    _initial_embedder = TextEmbedder()
    print("[+] Core AI Ready.")

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

class FileShare(BaseModel):
    object_id: str
    recipient_email: str

class UserSearchResult(BaseModel):
    user_id: str
    email: str

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
    if ext in (".mp4", ".mov", ".mkv", ".avi", ".m4v"):
        return "video"
    if ext in (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"):
        return "audio"
    return "document" # Fallback for unknown documents

# --- Background Workers ---

def background_worker(user_id: str, job_id: str, source: any, source_type: str, original_name: str, extension: str = None):
    db = DBStore(user_id=user_id)
    try:
        db.update_job_status(job_id, "processing")
        engine = IngestionPipeline(user_id=user_id)
        result = engine.ingest(source, source_type, extension, original_name)
        if result.get("skipped"):
            db.update_job_status(job_id, "skipped", result.get("message"))
        else:
            db.update_job_status(job_id, "completed")
    except Exception as e:
        db.update_job_status(job_id, "failed", str(e))

def cloud_background_worker(user_id: str, job_id: str, stream: io.BytesIO, source_type: str, filename: str, ext: str, password: Optional[str] = None):
    db = DBStore(user_id=user_id)
    try:
        db.update_job_status(job_id, "scanning")
        engine = IngestionPipeline(user_id=user_id)
        object_id = f"cloud_{uuid.uuid4().hex[:8]}" 

        print(f"DEBUG UPLOAD: Starting original-file upload for {filename}")
        result = engine.ingest(stream, source_type, ext, filename, object_id=object_id, skip_local_storage=True)

        if result.get("skipped"):
            msg = result.get("message", "No speech detected — file not saved or indexed.")
            print(f"[INFO] cloud_background_worker: {msg}")
            db.update_job_status(job_id, "skipped", msg)
            return
        
        db.update_job_status(job_id, "uploading")
        # Google Drive tokens are encrypted with the server-derived vault key
        # (see gdrive_callback → _derive_vault_key), not the raw form password.
        # Dropbox/OneDrive tokens live in the DB and don't need this key at all,
        # but passing it is harmless for them.
        vault_key = _derive_vault_key(user_id)
        adapter = StorageManager.get_adapter(user_id=user_id, user_password=vault_key)
        if not adapter:
            raise Exception("No connected cloud storage provider found for user.")

        # Determine which provider we are using (stored per-file for later routing)
        conn_info = StorageManager.get_connection(user_id)
        provider_name = conn_info.get("provider") if conn_info else None

        stream.seek(0)
        file_id = adapter.upload(stream, filename)
        print(f"DEBUG UPLOAD: File uploaded via {provider_name}! ID: {file_id}")

        thumbnail_url = None
        icon_url = None

        # Google Drive: fetch native thumbnail/icon links
        if hasattr(adapter, "service") and getattr(adapter, "service", None):
            try:
                meta = adapter.service.files().get(
                    fileId=file_id,
                    fields="thumbnailLink, iconLink"
                ).execute()
                thumbnail_url = meta.get("thumbnailLink")
                if thumbnail_url and "=s" in thumbnail_url:
                    thumbnail_url = thumbnail_url.split("=s")[0] + "=s800"
                icon_url = meta.get("iconLink")
            except Exception as e:
                print(f"Drive thumbnail notice: {e}")

        # OneDrive: fetch thumbnail via MS Graph
        elif provider_name == "onedrive" and file_id:
            try:
                import requests as _req
                od_headers = adapter._get_headers(content_type=None)
                coll_resp = _req.get(
                    f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/thumbnails",
                    headers=od_headers, timeout=10
                )
                if coll_resp.status_code == 200:
                    sets = coll_resp.json().get("value", [])
                    if sets and sets[0].get("large"):
                        thumbnail_url = sets[0]["large"].get("url")
            except Exception as e:
                print(f"OneDrive thumbnail notice: {e}")

        # Dropbox: fetch thumbnail via get_temporary_link (images only)
        elif provider_name == "dropbox" and file_id:
            try:
                import requests as _req
                IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
                if os.path.splitext(filename)[1].lower() in IMAGE_EXTS:
                    tmp_resp = _req.post(
                        "https://api.dropboxapi.com/2/files/get_temporary_link",
                        headers={"Authorization": f"Bearer {adapter.access_token}", "Content-Type": "application/json"},
                        json={"path": file_id},
                        timeout=10
                    )
                    if tmp_resp.status_code == 200:
                        thumbnail_url = tmp_resp.json().get("link")
            except Exception as e:
                print(f"Dropbox thumbnail notice: {e}")

        # --- Compute web_url: the direct cloud-provider link to view the file ---
        web_url = None
        if provider_name == "google_drive" and file_id:
            web_url = f"https://drive.google.com/file/d/{file_id}/view"
        elif provider_name == "dropbox" and file_id:
            # Dropbox preview URL pattern matching exact user path
            fname = os.path.basename(file_id)
            web_url = f"https://www.dropbox.com/preview/Apps/RepoIR_Vault/RepoIR_Vault/{fname}?role=personal"
        elif provider_name == "onedrive" and file_id:
            # Prefer webUrl cached from upload response, fallback to Graph API fetch
            web_url = getattr(adapter, "_last_upload_web_url", None)
            if not web_url and hasattr(adapter, "get_file_web_url"):
                web_url = adapter.get_file_web_url(file_id)

        db.update_object_cloud_info(
            object_id,
            file_path=file_id,
            thumbnail_url=thumbnail_url,
            icon_url=icon_url,
            provider=provider_name,
            web_url=web_url
        )

        db.log_activity(user_id, "INGEST", f"Stored {filename} in Cloud Vault (Original)")
        db.update_job_status(job_id, "completed")
        print(f"DEBUG UPLOAD: COMPLETED for {filename}")
    except Exception as e:
        print(f"[ERROR] DEBUG UPLOAD FAILED: {str(e)}")
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
        print(f"[WARNING] SambaNova LLM Error: {e}")
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


def reconstruct_faiss_vector(index, vector_id: int) -> np.ndarray:
    """Reconstruct a vector from either a native index or an ID-mapped index."""
    try:
        return index.reconstruct(int(vector_id))
    except (RuntimeError, NotImplementedError):
        base_index = getattr(index, "index", None)
        id_map = getattr(index, "id_map", None)
        if base_index is None or id_map is None:
            raise
        mapped_ids = faiss.vector_to_array(id_map)
        positions = np.flatnonzero(mapped_ids == int(vector_id))
        if len(positions) == 0:
            raise KeyError(f"FAISS vector ID {vector_id} was not found")
        return base_index.reconstruct(int(positions[0]))

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
    vault_password: Optional[str] = None  # Auto-derived if not provided

class StorageConnectPayload(BaseModel):
    provider: str
    provider_account_id: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[str] = None
    scope: Optional[str] = None

@app.get("/v1/storage/providers")
@app.get("/storage/providers")
def get_storage_providers():
    return {"providers": StorageManager.get_available_providers()}

@app.get("/v1/storage/status")
@app.get("/storage/status")
def get_storage_status(user_id: str = Depends(get_current_user)):
    return StorageManager.get_connection_status(user_id)

@app.post("/v1/storage/connect")
@app.post("/storage/connect")
def connect_storage(payload: StorageConnectPayload, user_id: str = Depends(get_current_user)):
    return StorageManager.connect_storage(
        user_id=user_id,
        provider=payload.provider,
        provider_account_id=payload.provider_account_id,
        access_token=payload.access_token,
        refresh_token=payload.refresh_token,
        token_expires_at=payload.token_expires_at,
        scope=payload.scope
    )

@app.delete("/v1/storage/disconnect")
@app.delete("/storage/disconnect")
def disconnect_storage(provider: Optional[str] = None, user_id: str = Depends(get_current_user)):
    StorageManager.disconnect_storage(user_id, provider=provider)
    return {"status": "disconnected", "provider": provider or "all"}

@app.get("/v1/storage/dropbox/connect")
@app.get("/storage/dropbox/connect")
def dropbox_connect(redirect_uri: Optional[str] = None, user_id: str = Depends(get_current_user)):
    state = AuthManager.create_oauth_state(user_id=user_id, provider="dropbox")
    client_id = os.getenv("DROPBOX_APP_KEY") or "MOCK_DROPBOX_APP_KEY"
    cb_uri = redirect_uri or os.getenv("DROPBOX_REDIRECT_URI") or "http://localhost:8000/v1/storage/dropbox/callback"
    oauth_url = f"https://www.dropbox.com/oauth2/authorize?client_id={quote(client_id)}&redirect_uri={quote(cb_uri)}&response_type=code&token_access_type=offline&state={quote(state)}"
    return {"status": "ok", "auth_url": oauth_url, "state": state}

@app.get("/v1/storage/dropbox/callback")
@app.get("/storage/dropbox/callback")
def dropbox_callback(code: str, state: str, redirect_uri: Optional[str] = None, error: Optional[str] = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Dropbox OAuth denied: {error}")

    user_id = AuthManager.verify_and_consume_oauth_state(state=state, expected_provider="dropbox")

    client_id = os.getenv("DROPBOX_APP_KEY")
    client_secret = os.getenv("DROPBOX_APP_SECRET")
    cb_uri = redirect_uri or os.getenv("DROPBOX_REDIRECT_URI") or "http://localhost:8000/v1/storage/dropbox/callback"

    if client_id and client_secret and "MOCK" not in client_id:
        try:
            token_resp = requests.post(
                "https://api.dropboxapi.com/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": cb_uri
                },
                timeout=15
            )
            if token_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Dropbox token exchange failed.")
            
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            account_id = token_data.get("account_id")

            if not account_id and access_token:
                acc_resp = requests.post(
                    "https://api.dropboxapi.com/2/users/get_current_account",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=15
                )
                if acc_resp.status_code == 200:
                    account_id = acc_resp.json().get("account_id")

            if not account_id:
                account_id = f"dbid_{user_id[:8]}"
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Dropbox OAuth communication error: {str(e)}")
    else:
        access_token = f"mock_dbx_access_{code}"
        refresh_token = f"mock_dbx_refresh_{code}"
        account_id = f"dbid_{code}"

    res = StorageManager.connect_storage(
        user_id=user_id,
        provider="dropbox",
        provider_account_id=account_id,
        access_token=access_token,
        refresh_token=refresh_token
    )
    return res

@app.get("/v1/storage/onedrive/connect")
@app.get("/storage/onedrive/connect")
def onedrive_connect(redirect_uri: Optional[str] = None, user_id: str = Depends(get_current_user)):
    state = AuthManager.create_oauth_state(user_id=user_id, provider="onedrive")
    client_id = os.getenv("MICROSOFT_CLIENT_ID") or os.getenv("ONEDRIVE_CLIENT_ID") or "MOCK_MICROSOFT_CLIENT_ID"
    cb_uri = redirect_uri or os.getenv("ONEDRIVE_REDIRECT_URI") or os.getenv("MICROSOFT_REDIRECT_URI") or "http://localhost:8000/v1/storage/onedrive/callback"
    scopes = quote("files.readwrite offline_access user.read")
    oauth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id={quote(client_id)}&response_type=code&redirect_uri={quote(cb_uri)}&scope={scopes}&state={quote(state)}"
    return {"status": "ok", "auth_url": oauth_url, "state": state}

@app.get("/v1/storage/onedrive/callback")
@app.get("/storage/onedrive/callback")
def onedrive_callback(code: str, state: str, redirect_uri: Optional[str] = None, error: Optional[str] = None):
    if error:
        raise HTTPException(status_code=400, detail=f"OneDrive OAuth denied: {error}")
    user_id = AuthManager.verify_and_consume_oauth_state(state=state, expected_provider="onedrive")
    client_id = os.getenv("MICROSOFT_CLIENT_ID") or os.getenv("ONEDRIVE_CLIENT_ID")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET") or os.getenv("ONEDRIVE_CLIENT_SECRET")
    cb_uri = redirect_uri or os.getenv("ONEDRIVE_REDIRECT_URI") or os.getenv("MICROSOFT_REDIRECT_URI") or "http://localhost:8000/v1/storage/onedrive/callback"

    if client_id and client_secret and "MOCK" not in client_id:
        try:
            token_resp = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": cb_uri,
                    # scope is NOT sent for authorization_code grant — MS derives it from the code
                },
                timeout=15
            )
            if token_resp.status_code != 200:
                err_body = token_resp.json() if token_resp.headers.get("Content-Type", "").startswith("application/json") else token_resp.text
                print(f"[ERROR] OneDrive token exchange HTTP {token_resp.status_code}: {err_body}")
                ms_error = err_body.get("error_description") or err_body.get("error") if isinstance(err_body, dict) else str(err_body)
                raise HTTPException(status_code=400, detail=f"OneDrive token exchange failed: {ms_error}")
            data = token_resp.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            me_resp = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15
            )
            account_id = me_resp.json().get("id") if me_resp.status_code == 200 else f"ms_{user_id[:8]}"
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OneDrive OAuth error: {str(e)}")
    else:
        access_token = f"mock_onedrive_access_{code}"
        refresh_token = f"mock_onedrive_refresh_{code}"
        account_id = f"ms_{code}"

    res = StorageManager.connect_storage(
        user_id=user_id,
        provider="onedrive",
        provider_account_id=account_id,
        access_token=access_token,
        refresh_token=refresh_token
    )
    return res

class OAuthLoginPayload(BaseModel):
    provider: str
    code: str
    redirect_uri: str

@app.post("/v1/auth/oauth-login")
def oauth_login(payload: OAuthLoginPayload):
    provider = payload.provider.lower()
    if provider == "dropbox":
        client_id = os.getenv("DROPBOX_APP_KEY")
        client_secret = os.getenv("DROPBOX_APP_SECRET")
        if client_id and client_secret and "MOCK" not in client_id:
            token_resp = requests.post(
                "https://api.dropboxapi.com/oauth2/token",
                data={
                    "code": payload.code,
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": payload.redirect_uri
                },
                timeout=15
            )
            if token_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Dropbox OAuth failed")
            data = token_resp.json()
            account_id = data.get("account_id")
            email = data.get("email")
            user_id = AuthManager.get_or_link_oauth_user("dropbox", account_id, email=email)
        else:
            mock_id = f"dbx_mock_{payload.code}"
            user_id = AuthManager.get_or_link_oauth_user("dropbox", mock_id, email=f"{mock_id}@dropbox.local")
            
    elif provider in ("microsoft", "onedrive"):
        client_id = os.getenv("MICROSOFT_CLIENT_ID") or os.getenv("ONEDRIVE_CLIENT_ID")
        client_secret = os.getenv("MICROSOFT_CLIENT_SECRET") or os.getenv("ONEDRIVE_CLIENT_SECRET")
        if client_id and client_secret and "MOCK" not in client_id:
            token_resp = requests.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": payload.code,
                    "grant_type": "authorization_code",
                    "redirect_uri": payload.redirect_uri
                },
                timeout=15
            )
            if token_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Microsoft OAuth failed")
            data = token_resp.json()
            access_token = data.get("access_token")
            me_resp = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15
            )
            me_data = me_resp.json() if me_resp.status_code == 200 else {}
            ms_id = me_data.get("id") or f"ms_{payload.code}"
            email = me_data.get("mail") or me_data.get("userPrincipalName")
            user_id = AuthManager.get_or_link_oauth_user("microsoft", ms_id, email=email, name=me_data.get("displayName"))
        else:
            mock_id = f"ms_mock_{payload.code}"
            user_id = AuthManager.get_or_link_oauth_user("microsoft", mock_id, email=f"{mock_id}@microsoft.local")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {provider}")

    token = AuthManager.create_access_token(user_id)
    return {"status": "success", "user_id": user_id, "token": token}

@app.post("/v1/auth/gdrive/callback")
def gdrive_callback(payload: GDriveCallback, user_id: str = Depends(get_current_user)):
    vault_pw = _derive_vault_key(user_id)
    gdrive = GDriveManager(user_id=user_id, user_password=vault_pw)
    try:
        gdrive.build_service_from_code(payload.code, payload.redirect_uri)
        StorageManager.connect_storage(
            user_id=user_id,
            provider="google_drive",
            provider_account_id=f"gdrive_{user_id}",
            status="active"
        )
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.get("/v1/config")
def get_config():
    return {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "api_base": f"http://{os.getenv('HOST', '127.0.0.1')}:{os.getenv('PORT', '8000')}"
    }

import hmac
import hashlib

def _derive_vault_key(user_id: str) -> str:
    """Deterministically derive a vault key from user_id + JWT secret.
    This means users never need to manually enter a vault password."""
    from app.auth.manager import SECRET_KEY
    return hmac.new(
        SECRET_KEY.encode('utf-8'),
        user_id.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

class VaultVerify(BaseModel):
    password: str

@app.get("/v1/vault/auto-key")
def vault_auto_key(user_id: str = Depends(get_current_user)):
    """Returns a deterministic vault key for this user — no manual password needed."""
    return {"vault_key": _derive_vault_key(user_id)}

@app.post("/v1/vault/status")
def vault_status(payload: VaultVerify, user_id: str = Depends(get_current_user)):
    # Also accept 'auto' as a sentinel to use the derived key
    password = payload.password if payload.password != 'auto' else _derive_vault_key(user_id)
    gdrive = GDriveManager(user_id=user_id, user_password=password)
    if not os.path.exists(gdrive.token_path):
        # For non-GDrive providers (Dropbox/OneDrive), storage is still connected
        storage_status = StorageManager.get_connection_status(user_id)
        if storage_status.get('connected'):
            return {"status": "valid"}
        return {"status": "not_connected"}
    if not password:
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
    password = payload.password if payload.password != 'auto' else _derive_vault_key(user_id)
    gdrive = GDriveManager(user_id=user_id, user_password=password)
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
    password: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    """All file uploads now go through the cloud pipeline (Drive-first)."""
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
    """Only return files that have a Drive file_path (Drive-backed objects)."""
    db = DBStore(user_id=user_id)
    all_objects = db.list_all_objects(category_id=category_id)
    drive_objects = [obj for obj in all_objects if obj.get("file_path") or obj.get("type") in ("url", "text")]
    return {"files": drive_objects}

@app.get("/v1/users/search", response_model=List[UserSearchResult])
def search_users(q: str, user_id: str = Depends(get_current_user)):
    return AuthManager.search_users_by_email(q, exclude_user_id=user_id)

@app.post("/v1/files/share")
def share_file(payload: FileShare, user_id: str = Depends(get_current_user)):
    sender_db = DBStore(user_id=user_id)
    source_row = sender_db.conn.execute(
        "SELECT * FROM objects WHERE object_id = ? AND (is_deleted = 0 OR is_deleted IS NULL)",
        (payload.object_id,),
    ).fetchone()
    if not source_row:
        raise HTTPException(status_code=404, detail="File not found")
    source_obj = dict(source_row)

    recipient = AuthManager.get_user_by_email(payload.recipient_email, exclude_user_id=user_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="No registered user found for that email")

    source_provider = source_obj.get("provider")
    if not source_provider:
        # Older cloud uploads may have a file ID but no provider column value.
        # Fall back to the user's connected provider for backward compatibility.
        source_connection = StorageManager.get_connection(user_id)
        source_provider = source_connection.get("provider") if source_connection else None
    if not source_obj.get("file_path") or not source_provider:
        raise HTTPException(status_code=400, detail="Only cloud-backed files can be shared")

    recipient_id = recipient["user_id"]
    recipient_db = DBStore(user_id=recipient_id)
    uploaded_file_id = None
    new_object_id = None
    try:
        source_adapter = StorageManager.get_adapter(user_id=user_id, provider=source_provider)
        file_stream = source_adapter.download(source_obj["file_path"])
        if not file_stream:
            raise HTTPException(status_code=502, detail="Source file could not be downloaded")

        recipient_connection = StorageManager.get_connection(recipient_id)
        if not recipient_connection:
            raise HTTPException(status_code=400, detail="Recipient has no connected cloud storage provider")
        recipient_provider = recipient_connection["provider"]
        recipient_adapter = StorageManager.get_adapter(user_id=recipient_id, provider=recipient_provider)
        file_stream.seek(0)
        uploaded_file_id = recipient_adapter.upload(file_stream, source_obj["source"])

        recipient_web_url = None
        if recipient_provider == "google_drive":
            recipient_web_url = f"https://drive.google.com/file/d/{uploaded_file_id}/view"
        elif recipient_provider == "dropbox":
            filename = os.path.basename(uploaded_file_id or source_obj["source"])
            recipient_web_url = f"https://www.dropbox.com/preview/Apps/RepoIR_Vault/RepoIR_Vault/{filename}?role=personal"
        elif recipient_provider == "onedrive":
            recipient_web_url = getattr(recipient_adapter, "_last_upload_web_url", None)
            if not recipient_web_url and uploaded_file_id and hasattr(recipient_adapter, "get_file_web_url"):
                recipient_web_url = recipient_adapter.get_file_web_url(uploaded_file_id)

        new_object_id = f"shared_{uuid.uuid4().hex[:8]}"
        chunk_rows = sender_db.conn.execute(
            "SELECT chunk_index, chunk_text FROM chunks WHERE object_id = ? ORDER BY chunk_index",
            (payload.object_id,),
        ).fetchall()
        chunk_texts = [row["chunk_text"] for row in chunk_rows]
        recipient_db.store_object(
            new_object_id,
            recipient_id,
            source_obj["source"],
            source_obj["type"],
            source_obj["file_type"],
            uploaded_file_id,
            len(chunk_texts),
            source_obj.get("file_size") or 0,
            thumbnail_url=source_obj.get("thumbnail_url"),
            icon_url=source_obj.get("icon_url"),
        )
        recipient_db.update_object_cloud_info(
            new_object_id,
            uploaded_file_id,
            thumbnail_url=source_obj.get("thumbnail_url"),
            icon_url=source_obj.get("icon_url"),
            provider=recipient_provider,
            web_url=recipient_web_url,
        )
        if chunk_texts:
            recipient_db.store_chunks(new_object_id, chunk_texts)

        source_vector_rows = sender_db.conn.execute(
            """
            SELECT v.vector_id, c.chunk_index
            FROM vectors v
            JOIN chunks c ON c.chunk_id = v.chunk_id
            WHERE c.object_id = ?
            ORDER BY c.chunk_index
            """,
            (payload.object_id,),
        ).fetchall()
        if source_vector_rows:
            source_faiss = FAISSStore(user_id=user_id)
            embeddings = np.vstack([
                reconstruct_faiss_vector(source_faiss.index, int(row["vector_id"]))
                for row in source_vector_rows
            ]).astype("float32")
            recipient_faiss = FAISSStore(user_id=recipient_id)
            start_id = recipient_db.get_next_vector_id()
            recipient_vector_ids = np.arange(start_id, start_id + len(embeddings)).astype("int64")
            recipient_faiss.add(embeddings, ids=recipient_vector_ids)
            recipient_db.store_vectors(
                start_id,
                [f"{new_object_id}_chunk_{row['chunk_index']}" for row in source_vector_rows],
            )

        sender_db.log_activity(user_id, "SHARE", f"Shared {source_obj['source']} with {recipient['email']}")
        recipient_db.log_activity(recipient_id, "SHARE", f"Received {source_obj['source']} from shared file")
        return {"status": "shared", "object_id": new_object_id, "recipient_email": recipient["email"]}
    except HTTPException:
        if new_object_id:
            recipient_db.delete_object(new_object_id)
        if uploaded_file_id:
            try:
                recipient_adapter.delete(uploaded_file_id)
            except Exception:
                pass
        raise
    except Exception as exc:
        if new_object_id:
            recipient_db.delete_object(new_object_id)
        if uploaded_file_id:
            try:
                recipient_adapter.delete(uploaded_file_id)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Sharing failed: {exc}")

@app.delete("/v1/files/{object_id}")
@app.delete("/v1/vault/objects/{object_id}")
def delete_file(object_id: str, password: Optional[str] = None, user_id: str = Depends(get_current_user)):
    """Soft-deletes file in DB (hidden everywhere, embeddings preserved) & erases real file from cloud storage."""
    db = DBStore(user_id=user_id)
    obj_row = db.conn.execute("SELECT * FROM objects WHERE object_id = ?", (object_id,)).fetchone()
    if not obj_row:
        raise HTTPException(status_code=404, detail="File not found")
    obj = dict(obj_row)

    # 1. Soft-delete in DB (is_deleted = 1)
    db.soft_delete_object(object_id)

    # 2. Hard-delete real file from connected cloud storage
    file_path = obj.get("file_path")
    provider = obj.get("provider")
    if file_path:
        try:
            adapter = StorageManager.get_adapter(user_id=user_id, provider=provider, user_password=password)
            if adapter and hasattr(adapter, "delete"):
                adapter.delete(file_path)
                print(f"[INFO] Deleted physical file {file_path} from {provider}")
        except Exception as e:
            print(f"[WARNING] Could not erase file from cloud provider {provider}: {e}")

    # 3. Clean up local copy if present
    if file_path and not file_path.startswith("http") and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    db.log_activity(user_id, "DELETE", f"Soft-deleted object {object_id} and erased from cloud")
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
async def preview_file(object_id: str, password: Optional[str] = None, user_id: str = Depends(get_current_user)):
    db = DBStore(user_id=user_id)
    obj_row = db.conn.execute("SELECT * FROM objects WHERE object_id = ?", (object_id,)).fetchone()
    if not obj_row: raise HTTPException(status_code=404, detail="File not found")
    obj = dict(obj_row)
    file_id = obj["file_path"]
    if not file_id: raise HTTPException(status_code=400, detail="File not in Cloud Vault")

    # Route to the exact provider that stored this file
    provider = obj.get("provider")  # e.g. "google_drive", "dropbox", "onedrive"

    try:
        # Use the server-derived vault key (same key used to encrypt the GDrive token
        # during OAuth). Harmless for Dropbox/OneDrive which use DB-stored tokens.
        vault_key = _derive_vault_key(user_id)
        adapter = StorageManager.get_adapter(user_id=user_id, provider=provider, user_password=vault_key)
        file_stream = adapter.download(file_id)
        if not file_stream:
            raise HTTPException(status_code=404, detail="File content could not be retrieved from cloud storage")
        
        # Determine MIME type
        ext = os.path.splitext(obj["source"])[1].lower()
        mime_types = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", 
            ".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
            ".m4a": "audio/mp4", ".flac": "audio/flac", ".webm": "audio/webm"
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

