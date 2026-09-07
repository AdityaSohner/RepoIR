# Dropbox Integration — Technical Reference

## Overview

This document covers how Dropbox is integrated into RepoIR as a cloud storage provider, distinct from RepoIR login authentication.

---

## 1. How Dropbox OAuth Works

Dropbox OAuth 2.0 is used **only to authorize storage access** — it never replaces RepoIR's JWT login.

**Flow:**
```
User logs in → JWT identifies user_id → User clicks "Connect Dropbox"
→ Backend checks 1-provider rule (rejects if already connected)
→ Backend generates secure OAuth state tied to user_id (expires in 15 min, single-use)
→ Backend returns Dropbox authorization URL to frontend
→ Frontend opens Dropbox OAuth popup
→ User authorizes → Dropbox redirects to /storage/dropbox/callback?code=...&state=...
→ Backend validates state (expiry, single-use, provider match)
→ Backend exchanges code for access_token + refresh_token via Dropbox Token API
→ Backend calls Dropbox /2/users/get_current_account to get stable account_id
→ Backend encrypts tokens, stores in storage_connections as provider="dropbox"
→ Frontend popup posts message to opener, closes itself
```

---

## 2. How It Differs from RepoIR Auth

| Aspect | RepoIR JWT Auth | Dropbox OAuth |
|---|---|---|
| Purpose | Identifies who the account is | Authorizes cloud storage access |
| Token type | JWT (signed with SECRET_KEY) | OAuth access token + refresh token |
| Stored where | Client sessionStorage | Backend DB (encrypted) |
| Exposed to frontend | Yes (needed for API calls) | **Never** |
| Used as login | Yes | **No** |
| External identity used | Internal `user_id` (UUID) | Dropbox stable `account_id` (dbid:…) |

---

## 3. One-Provider Rule

Enforced at **two levels**:

1. **DB constraint**: `UNIQUE(user_id)` on `storage_connections` — even direct SQL inserts fail.
2. **Application check**: `GET /v1/storage/dropbox/connect` pre-checks before creating OAuth state; callback re-checks after state validation.

A user with Google Drive connected cannot start Dropbox OAuth. The frontend shows "Unavailable" for other providers while one is active.

---

## 4. Where Credentials Are Stored

`data/users.db` → `storage_connections` table:

| Column | Value |
|---|---|
| `user_id` | Internal RepoIR user UUID |
| `provider` | `"dropbox"` |
| `provider_account_id` | Dropbox stable `account_id` (e.g. `dbid:abc123`) |
| `access_token` | **Encrypted** with `EncryptionManager` (Fernet/AES) |
| `refresh_token` | **Encrypted** with `EncryptionManager` |
| `status` | `"active"` / `"error"` |

Tokens are **never** returned in API responses, never logged, never stored plaintext.

---

## 5. Token Refresh

When the access token expires, `DropboxAdapter.refresh_access_token()`:
1. Uses stored `refresh_token` (decrypted at runtime by `StorageManager.get_adapter()`)
2. POSTs to `https://api.dropboxapi.com/oauth2/token` with `grant_type=refresh_token`
3. Encrypts and persists the new `access_token` via `StorageManager.connect_storage()`
4. Returns the new token for the current operation

`_request_with_retry()` auto-invokes refresh on 401 and retries the request once.

On refresh failure: returns HTTP 401 with safe message, **never** exposing token/secret details.

---

## 6. How StorageProvider Isolates Dropbox Logic

```
app_server.py (route)
  → Depends(get_current_user) → user_id (from JWT)
  → StorageManager.get_adapter(user_id)
    → reads storage_connections
    → decrypts tokens
    → returns DropboxAdapter(access_token=..., refresh_token=...)
  → adapter.upload() / .download() / .list_files() / etc.
    → Dropbox API v2 (inside DropboxAdapter only)
```

No Dropbox API calls exist anywhere except inside `app/storage/providers/dropbox.py`. Routes and business logic use `StorageProvider` interface only.

---

## 7. Dropbox App Permissions (App Folder Model)

RepoIR requests access to the **App Folder** (`/Apps/RepoIR/`) only:

- Scope: `files.content.read files.content.write files.metadata.read account_info.read`
- This limits Dropbox access to the `RepoIR_Vault` folder inside `/Apps/RepoIR/`
- Users' other Dropbox files remain private and inaccessible

To switch to full Dropbox access later, update the OAuth scope string in `dropbox_connect()`.

---

## 8. Environment Configuration

Add to your `.env` file:

```env
# Dropbox OAuth App Credentials
# Create at: https://www.dropbox.com/developers/apps
DROPBOX_APP_KEY=your_dropbox_app_key_here
DROPBOX_APP_SECRET=your_dropbox_app_secret_here
DROPBOX_REDIRECT_URI=http://localhost:8000/v1/storage/dropbox/callback
```

**Do not commit real credentials.** Without these, the system falls back to mock mode (for testing).

---

## 9. API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/v1/storage/providers` | None | List available providers |
| GET | `/v1/storage/status` | JWT | Get active connection info (no tokens) |
| GET | `/v1/storage/dropbox/connect` | JWT | Pre-check + generate OAuth URL |
| GET | `/v1/storage/dropbox/callback` | State-validated | Exchange code, store credentials |
| DELETE | `/v1/storage/disconnect` | JWT | Remove active connection |

---

## 10. Running Tests

```powershell
# Run Dropbox integration tests (mocked — no real Dropbox account needed)
env/Scripts/python.exe -m pytest tests/test_dropbox_integration.py -v

# Run all storage tests
env/Scripts/python.exe -m pytest tests/ -v
```

---

## 11. Limitations & TODOs

- **Dropbox webhook/push sync**: Not implemented; `list_files()` is pull-based.
- **Dropbox file sharing**: Not supported; files live in the RepoIR app folder only.
- **Concurrent OAuth race**: Mitigated by DB `UNIQUE(user_id)` constraint but no distributed locking.
- **Dropbox Business/Teams**: Not tested; personal accounts only for now.
