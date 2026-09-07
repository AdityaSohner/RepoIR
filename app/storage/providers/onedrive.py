import io
import os
import requests
from typing import List, Dict, Any, Optional

from fastapi import HTTPException
from app.storage.providers.base import StorageProvider

MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_GRAPH_URL = "https://graph.microsoft.com/v1.0"

class OneDriveAdapter(StorageProvider):
    """
    StorageProvider implementation for Microsoft OneDrive using Microsoft Graph API v1.0.
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
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID") or os.getenv("ONEDRIVE_CLIENT_ID")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET") or os.getenv("ONEDRIVE_CLIENT_SECRET")

    def _get_headers(self, content_type: Optional[str] = "application/json") -> Dict[str, str]:
        # Refresh if token is missing or looks invalid (a valid MS JWT always has dots)
        if not self.access_token or '.' not in self.access_token:
            self.refresh_access_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def refresh_access_token(self) -> str:
        """
        Refreshes expired access_token using refresh_token.
        """
        if not self.refresh_token:
            raise HTTPException(status_code=401, detail="OneDrive credentials missing refresh token. Please reconnect.")

        if not self.client_id or not self.client_secret:
            raise HTTPException(status_code=500, detail="Microsoft/OneDrive client credentials not configured on server.")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "files.readwrite offline_access user.read"
        }

        try:
            resp = requests.post(MICROSOFT_TOKEN_URL, data=payload, timeout=15)
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Failed to refresh OneDrive token.")
            data = resp.json()
            self.access_token = data.get("access_token")
            if data.get("refresh_token"):
                self.refresh_token = data.get("refresh_token")
            return self.access_token
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"OneDrive token refresh error: {str(e)}")

    def get_or_create_vault(self, folder_name: str = "RepoIR_Vault") -> str:
        """
        Returns the OneDrive item ID of the vault folder, creating it if needed.
        Uses 'fail' conflict behaviour so a 409 means it already exists — we then fetch its ID.
        """
        headers = self._get_headers(content_type="application/json")

        # Try to create the folder
        create_url = f"{MICROSOFT_GRAPH_URL}/me/drive/root/children"
        payload = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail"
        }
        resp = requests.post(create_url, headers=headers, json=payload, timeout=15)

        if resp.status_code in (200, 201):
            return resp.json().get("id")

        # 409 = folder already exists — fetch its id
        if resp.status_code == 409:
            search_url = f"{MICROSOFT_GRAPH_URL}/me/drive/root/children"
            list_resp = requests.get(search_url, headers=headers, timeout=15)
            if list_resp.status_code == 200:
                for item in list_resp.json().get("value", []):
                    if item.get("name") == folder_name and "folder" in item:
                        return item.get("id")

        # Fallback: upload to root if vault creation fails
        print(f"[WARNING] OneDrive: could not get/create vault folder '{folder_name}', uploading to root.")
        return None

    def upload(self, file_stream: io.BytesIO, filename: str, folder_id: Optional[str] = None, mime_type: str = 'application/octet-stream') -> str:
        # Always upload into the RepoIR_Vault folder unless a specific folder_id is given
        target_folder_id = folder_id or self.get_or_create_vault("RepoIR_Vault")

        headers = self._get_headers(content_type="application/octet-stream")
        if target_folder_id:
            path = f"/me/drive/items/{target_folder_id}:/{filename}:/content"
        else:
            path = f"/me/drive/root:/{filename}:/content"

        url = f"{MICROSOFT_GRAPH_URL}{path}"
        file_stream.seek(0)
        resp = requests.put(url, headers=headers, data=file_stream.read(), timeout=30)
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=resp.status_code, detail=f"OneDrive upload failed: {resp.text}")
        item_data = resp.json()
        # Store webUrl alongside the id so we can redirect to it later
        self._last_upload_web_url = item_data.get("webUrl")
        return item_data.get("id")

    def get_file_web_url(self, item_id: str) -> Optional[str]:
        """Fetches the OneDrive web URL for a given item ID via Graph API."""
        try:
            headers = self._get_headers(content_type=None)
            resp = requests.get(
                f"{MICROSOFT_GRAPH_URL}/me/drive/items/{item_id}?select=webUrl",
                headers=headers, timeout=10
            )
            if resp.status_code == 200:
                return resp.json().get("webUrl")
        except Exception as e:
            print(f"OneDrive get_file_web_url error: {e}")
        return None

    def download(self, file_id: str) -> Optional[io.BytesIO]:
        headers = self._get_headers(content_type=None)
        url = f"{MICROSOFT_GRAPH_URL}/me/drive/items/{file_id}/content"
        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        if resp.status_code != 200:
            return None
        buf = io.BytesIO()
        for chunk in resp.iter_content(chunk_size=8192):
            buf.write(chunk)
        buf.seek(0)
        return buf

    def delete(self, file_id: str) -> bool:
        headers = self._get_headers(content_type=None)
        url = f"{MICROSOFT_GRAPH_URL}/me/drive/items/{file_id}"
        resp = requests.delete(url, headers=headers, timeout=15)
        return resp.status_code in (200, 204)

    def move_to_trash(self, file_id: str) -> bool:
        return self.delete(file_id)

    def restore(self, file_id: str) -> bool:
        headers = self._get_headers()
        url = f"{MICROSOFT_GRAPH_URL}/me/drive/items/{file_id}/restore"
        resp = requests.post(url, headers=headers, timeout=15)
        return resp.status_code in (200, 201)

    def list_files(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        headers = self._get_headers()
        url = f"{MICROSOFT_GRAPH_URL}/me/drive/root/children"
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        items = resp.json().get("value", [])
        result = []
        for item in items:
            name = item.get("name", "")
            if query and query.lower() not in name.lower():
                continue
            result.append({
                "id": item.get("id"),
                "name": name,
                "size": item.get("size", 0),
                "mime_type": item.get("file", {}).get("mimeType", "application/octet-stream") if "file" in item else "folder",
                "created_at": item.get("createdDateTime"),
                "updated_at": item.get("lastModifiedDateTime"),
            })
        return result

    def get_metadata(self, file_id: str) -> Dict[str, Any]:
        headers = self._get_headers()
        url = f"{MICROSOFT_GRAPH_URL}/me/drive/items/{file_id}"
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return {}
        item = resp.json()
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "size": item.get("size", 0),
            "mime_type": item.get("file", {}).get("mimeType", "application/octet-stream") if "file" in item else "folder",
            "created_at": item.get("createdDateTime"),
            "updated_at": item.get("lastModifiedDateTime"),
        }
