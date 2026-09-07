import io
import os
import json
import requests
from typing import List, Dict, Any, Optional

from fastapi import HTTPException
from app.storage.providers.base import StorageProvider

DROPBOX_API_URL = "https://api.dropboxapi.com/2"
DROPBOX_CONTENT_URL = "https://content.dropboxapi.com/2"
DROPBOX_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"

class DropboxAdapter(StorageProvider):
    """
    Real StorageProvider adapter for Dropbox integration using Dropbox API v2.
    Isolated within app/storage/providers/dropbox.py.
    """

    def __init__(
        self,
        user_id: str = "default",
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None
    ):
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = os.getenv("DROPBOX_APP_KEY")
        self.client_secret = os.getenv("DROPBOX_APP_SECRET")

    def _get_headers(self, content_type: Optional[str] = "application/json") -> Dict[str, str]:
        if not self.access_token:
            self.refresh_access_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def refresh_access_token(self) -> str:
        """
        Refreshes expired access_token using refresh_token and updates storage_connections.
        """
        if not self.refresh_token:
            raise HTTPException(status_code=401, detail="Dropbox credentials missing refresh token. Please reconnect.")

        if not self.client_id or not self.client_secret:
            # Safe error without leaking credentials
            raise HTTPException(status_code=500, detail="Dropbox client credentials not configured on server.")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        try:
            resp = requests.post(DROPBOX_TOKEN_URL, data=payload, timeout=15)
            if resp.status_code != 200:
                print(f"[ERROR] Dropbox token refresh failed for user {self.user_id}")
                raise HTTPException(status_code=401, detail="Dropbox token refresh failed. Please reconnect.")

            data = resp.json()
            new_access_token = data.get("access_token")
            if not new_access_token:
                raise HTTPException(status_code=401, detail="Invalid token refresh response from Dropbox.")

            self.access_token = new_access_token
            # Persist updated access_token safely via StorageManager
            from app.storage.manager import StorageManager
            conn_info = StorageManager.get_connection(self.user_id)
            if conn_info:
                StorageManager.connect_storage(
                    user_id=self.user_id,
                    provider="dropbox",
                    provider_account_id=conn_info["provider_account_id"],
                    access_token=new_access_token,
                    refresh_token=self.refresh_token,
                    scope=conn_info.get("scope")
                )
            return new_access_token
        except HTTPException:
            raise
        except Exception as e:
            print(f"[ERROR] Dropbox refresh exception: {e}")
            raise HTTPException(status_code=500, detail="Unable to refresh Dropbox token.")

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Executes HTTP request, automatically attempting token refresh on 401.
        """
        headers = kwargs.pop("headers", None) or self._get_headers()
        resp = requests.request(method, url, headers=headers, **kwargs)

        if resp.status_code == 401:
            # Token expired — attempt refresh once
            new_token = self.refresh_access_token()
            headers["Authorization"] = f"Bearer {new_token}"
            resp = requests.request(method, url, headers=headers, **kwargs)

        return resp

    def get_or_create_vault(self, folder_name: str = "RepoIR_Vault") -> str:
        vault_path = f"/{folder_name}"
        headers = self._get_headers()
        payload = {"path": vault_path, "autorename": False}
        resp = self._request_with_retry("POST", f"{DROPBOX_API_URL}/files/create_folder_v2", json=payload, headers=headers)
        if resp.status_code in (200, 409): # 200 = created, 409 = already exists
            return vault_path
        return vault_path

    def upload(
        self,
        file_stream: io.BytesIO,
        filename: str,
        folder_id: Optional[str] = None,
        mime_type: str = 'application/octet-stream'
    ) -> str:
        vault_folder = folder_id or self.get_or_create_vault("RepoIR_Vault")
        target_path = f"{vault_folder.rstrip('/')}/{filename.lstrip('/')}"
        
        file_stream.seek(0)
        raw_bytes = file_stream.read()

        arg = {
            "path": target_path,
            "mode": "overwrite",
            "autorename": True,
            "mute": False
        }
        headers = {
            "Authorization": f"Bearer {self.access_token or ''}",
            "Dropbox-API-Arg": json.dumps(arg),
            "Content-Type": "application/octet-stream"
        }

        resp = self._request_with_retry("POST", f"{DROPBOX_CONTENT_URL}/files/upload", data=raw_bytes, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Dropbox file upload failed.")

        data = resp.json()
        # Return path_display (e.g. /Apps/RepoIR_Vault/RepoIR_Vault/file.pdf)
        # Dropbox API accepts paths OR IDs in all subsequent calls (download, delete, etc.)
        return data.get("path_display") or data.get("id") or target_path

    def download(self, file_id: str) -> Optional[io.BytesIO]:
        arg = {"path": file_id}
        headers = {
            "Authorization": f"Bearer {self.access_token or ''}",
            "Dropbox-API-Arg": json.dumps(arg)
        }
        resp = self._request_with_retry("POST", f"{DROPBOX_CONTENT_URL}/files/download", headers=headers)
        if resp.status_code != 200:
            return None
        return io.BytesIO(resp.content)

    def delete(self, file_id: str) -> bool:
        headers = self._get_headers()
        payload = {"path": file_id}
        resp = self._request_with_retry("POST", f"{DROPBOX_API_URL}/files/delete_v2", json=payload, headers=headers)
        return resp.status_code == 200

    def move_to_trash(self, file_id: str) -> bool:
        return self.delete(file_id)

    def restore(self, file_id: str) -> bool:
        headers = self._get_headers()
        payload = {"path": file_id, "rev": "latest"}
        resp = self._request_with_retry("POST", f"{DROPBOX_API_URL}/files/restore", json=payload, headers=headers)
        return resp.status_code == 200

    def list_files(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        headers = self._get_headers()
        vault_path = self.get_or_create_vault("RepoIR_Vault")
        payload = {"path": vault_path, "recursive": False}

        resp = self._request_with_retry("POST", f"{DROPBOX_API_URL}/files/list_folder", json=payload, headers=headers)
        if resp.status_code != 200:
            return []

        entries = resp.json().get("entries", [])
        files = []
        for entry in entries:
            if entry.get(".tag") == "file":
                files.append({
                    "id": entry.get("id"),
                    "name": entry.get("name"),
                    "mimeType": "application/octet-stream",
                    "path": entry.get("path_lower"),
                    "size": entry.get("size")
                })
        return files

    def get_metadata(self, file_id: str) -> Dict[str, Any]:
        headers = self._get_headers()
        payload = {"path": file_id}
        resp = self._request_with_retry("POST", f"{DROPBOX_API_URL}/files/get_metadata", json=payload, headers=headers)
        if resp.status_code != 200:
            return {}
        entry = resp.json()
        return {
            "id": entry.get("id"),
            "name": entry.get("name"),
            "path": entry.get("path_lower"),
            "size": entry.get("size")
        }
