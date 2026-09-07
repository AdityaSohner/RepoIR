import io
import os
import json
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.storage.providers.base import StorageProvider
from app.storage.encryption_manager import EncryptionManager
from app.storage.gdrive_store import GDriveManager, SCOPES

class GoogleDriveAdapter(StorageProvider):
    """
    Adapter implementation for Google Drive.
    Wraps GDriveManager while adhering to the StorageProvider interface.
    """

    def __init__(self, user_id: str = "default", user_password: Optional[str] = None):
        self.user_id = user_id
        self.user_password = user_password
        self.gdrive = GDriveManager(user_id=user_id, user_password=user_password)

    @property
    def service(self):
        return self.gdrive.service

    def upload(self, file_stream: io.BytesIO, filename: str, folder_id: Optional[str] = None, mime_type: str = 'application/octet-stream') -> str:
        if not folder_id:
            folder_id = self.gdrive.get_or_create_vault("RepoIR_Vault")
        return self.gdrive.upload_to_vault(file_stream, filename, folder_id, mime_type=mime_type)

    def download(self, file_id: str) -> Optional[io.BytesIO]:
        return self.gdrive.download_file(file_id)

    def delete(self, file_id: str) -> bool:
        if not self.service:
            raise Exception("Google Drive service not connected.")
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            print(f"GDrive Delete Error: {e}")
            return False

    def move_to_trash(self, file_id: str) -> bool:
        if not self.service:
            raise Exception("Google Drive service not connected.")
        try:
            self.service.files().update(fileId=file_id, body={'trashed': True}).execute()
            return True
        except Exception as e:
            print(f"GDrive Trash Error: {e}")
            return False

    def restore(self, file_id: str) -> bool:
        if not self.service:
            raise Exception("Google Drive service not connected.")
        try:
            self.service.files().update(fileId=file_id, body={'trashed': False}).execute()
            return True
        except Exception as e:
            print(f"GDrive Restore Error: {e}")
            return False

    def list_files(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        q = query or "mimeType != 'application/vnd.google-apps.folder'"
        return self.gdrive.list_files(query=q)

    def get_metadata(self, file_id: str) -> Dict[str, Any]:
        return self.gdrive.get_file_metadata(file_id)

    # Drive-specific helper delegations
    def get_or_create_vault(self, folder_name: str = "RepoIR_Vault") -> str:
        return self.gdrive.get_or_create_vault(folder_name)

    def upload_to_vault(self, file_stream: io.BytesIO, filename: str, folder_id: str, mime_type: str = 'application/octet-stream') -> str:
        return self.gdrive.upload_to_vault(file_stream, filename, folder_id, mime_type=mime_type)

    def build_service_from_code(self, code: str, redirect_uri: str):
        return self.gdrive.build_service_from_code(code, redirect_uri)

    def get_changes(self, last_token=None, vault_id=None):
        return self.gdrive.get_changes(last_token=last_token, vault_id=vault_id)
