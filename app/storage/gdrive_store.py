import io
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from app.storage.encryption_manager import EncryptionManager
from app.config import DATA_DIR
import json

# ── Setup ─────────────────────────────────────────────────────────────────────
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GDriveManager:
    """
    Handles the "Bridge" between Google Drive and RepoIR.
    Focuses on RAM-only file streaming.
    """

    def __init__(self, user_id: str = "default", user_password: str = None):
        self.user_id = user_id
        self.user_password = user_password
        self.user_dir = DATA_DIR / "users" / user_id
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.token_path = str(self.user_dir / "token.json.enc")
        
        # Load from .env
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        self.service = self._authenticate()

    def _authenticate(self):
        if not os.path.exists(self.token_path):
            print(f"DEBUG: No token file found for user {self.user_id} at {self.token_path}")
            return None
            
        try:
            with open(self.token_path, 'rb') as f:
                encrypted_data = f.read()

            print(f"DEBUG: Data loaded from {self.token_path}, size={len(encrypted_data)}. Decrypting...")

            keys_to_try = []
            if self.user_password:
                keys_to_try.append(self.user_password)
            if self.user_id not in keys_to_try:
                keys_to_try.append(self.user_id)

            decrypted_data = None
            for key in keys_to_try:
                try:
                    encryptor = EncryptionManager(key_or_user_id=key)
                    decrypted_data = encryptor.decrypt_stream(encrypted_data)
                    break
                except Exception:
                    continue

            if not decrypted_data:
                print(f"[INFO] Stale or mismatched encryption key for token file of user {self.user_id} — removing token file to allow re-auth.")
                try:
                    os.remove(self.token_path)
                except OSError:
                    pass
                return None

            token_data = json.loads(decrypted_data.decode())
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            
            if creds and creds.expired and creds.refresh_token:
                print("DEBUG: Refreshing GDrive credentials")
                creds.refresh(Request())
                self.save_credentials(creds)
                
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            err_str = str(e).lower()
            err_type = type(e).__name__.lower()
            if 'invalidtoken' in err_type or 'invalid' in err_str or 'signature' in err_str or 'token' in err_str:
                print(f"[INFO] Stale/mismatched token for user {self.user_id} — removing to allow re-auth.")
                try:
                    os.remove(self.token_path)
                except OSError:
                    pass
            else:
                import traceback
                print(f"GDrive Auth Error for user {self.user_id}: {str(e)}")
                traceback.print_exc()
            return None

    def save_credentials(self, creds):
        """Encrypts and saves the GDrive credentials safely using server-managed encryption key."""
        encryptor = EncryptionManager(key_or_user_id=self.user_password or self.user_id)
        token_json = creds.to_json()
        encrypted_token = encryptor.encrypt_stream(token_json.encode())
        
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
        with open(self.token_path, 'wb') as f:
            f.write(encrypted_token)
        print(f"SUCCESS: Token encrypted and saved to {self.token_path}")


    def build_service_from_code(self, code: str, redirect_uri: str):
        """Exchanges an auth code from frontend for a real token."""
        if not self.client_id or not self.client_secret or "YOUR_GOOGLE" in self.client_secret:
            raise Exception("Google Client ID or Secret NOT CONFIGURED in .env. Please add them.")

        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        
        # We use InstalledAppFlow but with manual config
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        creds = flow.credentials
        self.save_credentials(creds)
        self.service = build('drive', 'v3', credentials=creds)
        return self.service


    def get_file_content(self, file_id: str) -> io.BytesIO:
        """
        Downloads a file from GDrive directly into a RAM buffer.
        Zero disk usage = Total Privacy.
        """
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        fh.seek(0) # Reset pointer to start of file
        return fh 

    def list_files(self, query="mimeType != 'application/vnd.google-apps.folder'"):
        """Lists files on user's drive to identify what needs indexing."""
        if not self.service: return []
        results = self.service.files().list(q=query, pageSize=100, fields="files(id, name, mimeType)").execute()
        return results.get('files', [])

    def get_file_metadata(self, file_id: str):
        """Gets metadata including thumbnail if available."""
        if not self.service: return {}
        try:
            return self.service.files().get(
                fileId=file_id, 
                fields="id, name, mimeType, thumbnailLink, webViewLink, size"
            ).execute()
        except Exception as e:
            print(f"GDrive Metadata Error: {e}")
            return {}

    def download_file(self, file_id: str) -> io.BytesIO:
        """Downloads a file and returns the stream."""
        if not self.service: return None
        return self.get_file_content(file_id)

    def get_or_create_vault(self, folder_name="RepoIR_Vault"):
        """Ensures the reserved RepoIR folder exists and returns its ID."""
        if not self.service:
            raise Exception("GDrive Service Not Connected")
            
        try:
            query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']
            
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')
        except Exception as e:
            print(f"Vault Error: {e}")
            raise

    def upload_to_vault(self, file_stream, filename, folder_id, mime_type='application/octet-stream'):
        """Uploads a RAM stream directly to the Google Drive Vault."""
        if not self.service:
            raise Exception("GDrive Service Not Connected")
            
        try:
            file_stream.seek(0)
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            media = MediaIoBaseUpload(file_stream, mimetype=mime_type, resumable=True)
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return file.get('id')
        except Exception as e:
            print(f"Upload Error: {e}")
            raise

    def get_or_create_thumbnails_folder(self, vault_id: str) -> str:
        """Ensures a 'thumbnails' subfolder exists inside the vault and returns its ID."""
        if not self.service:
            raise Exception("GDrive Service Not Connected")
        try:
            query = f"name = 'thumbnails' and mimeType = 'application/vnd.google-apps.folder' and '{vault_id}' in parents and trashed = false"
            results = self.service.files().list(q=query, fields="files(id)").execute()
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']
            # Create it
            folder = self.service.files().create(
                body={'name': 'thumbnails', 'mimeType': 'application/vnd.google-apps.folder', 'parents': [vault_id]},
                fields='id'
            ).execute()
            return folder.get('id')
        except Exception as e:
            print(f"Thumbnails Folder Error: {e}")
            raise

    def upload_thumbnail(self, image_bytes: bytes, filename: str, thumbnails_folder_id: str) -> str:
        """Uploads an unencrypted JPEG thumbnail to the thumbnails folder. Returns the file ID."""
        if not self.service:
            raise Exception("GDrive Service Not Connected")
        try:
            stream = io.BytesIO(image_bytes)
            file_metadata = {'name': filename, 'parents': [thumbnails_folder_id]}
            media = MediaIoBaseUpload(stream, mimetype='image/jpeg', resumable=False)
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id, thumbnailLink, webContentLink').execute()
            # Make it publicly readable so the <img> tag can load it
            self.service.permissions().create(
                fileId=file['id'],
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            return file.get('id')
        except Exception as e:
            print(f"Thumbnail Upload Error: {e}")
            raise

    def get_changes(self, last_token=None, vault_id=None):
        """Fetches only the files that changed and are located in the specified vault_id."""
        if not last_token:
            response = self.service.changes().getStartPageToken().execute()
            return response.get('startPageToken'), []

        changes = []
        page_token = last_token
        while page_token is not None:
            # We must explicitly ask for the 'file(parents)' field to do the filtering
            response = self.service.changes().list(
                pageToken=page_token, 
                spaces='drive',
                fields="nextPageToken, newStartPageToken, changes(fileId, removed, file(parents))"
            ).execute()
            
            for change in response.get('changes'):
                if not change.get('removed'):
                    file_metadata = change.get('file', {})
                    parents = file_metadata.get('parents', [])
                    
                    # Only include if vault_id is one of the parents
                    if vault_id and vault_id in parents:
                        changes.append(change.get('fileId'))
            
            page_token = response.get('nextPageToken')
            last_token = response.get('newStartPageToken')

        return last_token, list(set(changes))

