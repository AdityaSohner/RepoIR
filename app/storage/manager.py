import os
import uuid
import sqlite3
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import HTTPException

from app.auth.manager import USERS_DB, SECRET_KEY, init_users_db
from app.config import DATA_DIR
from app.storage.encryption_manager import EncryptionManager
from app.storage.providers.base import StorageProvider
from app.storage.providers.google_drive import GoogleDriveAdapter
from app.storage.providers.dropbox import DropboxAdapter
from app.storage.providers.onedrive import OneDriveAdapter

SUPPORTED_PROVIDERS = {
    "google_drive": {"name": "Google Drive", "supported": True},
    "dropbox": {"name": "Dropbox", "supported": True},
    "onedrive": {"name": "OneDrive", "supported": True},
}

from app.auth.manager import USERS_DB, SECRET_KEY, init_users_db, get_users_db_connection

def get_db_connection():
    init_users_db()
    return get_users_db_connection()

class StorageManager:
    """
    Central manager for user storage connection lifecycle and adapter resolution.
    Business logic and routes interact with StorageManager, never provider APIs directly.
    """

    @staticmethod
    def _encrypt_token(token: Optional[str]) -> Optional[str]:
        if not token:
            return None
        encryptor = EncryptionManager(key_or_user_id=SECRET_KEY)
        encrypted_bytes = encryptor.encrypt_stream(token.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    @staticmethod
    def _decrypt_token(encrypted_token: Optional[str]) -> Optional[str]:
        if not encrypted_token:
            return None
        try:
            encryptor = EncryptionManager(key_or_user_id=SECRET_KEY)
            decrypted_bytes = encryptor.decrypt_stream(encrypted_token.encode('utf-8'))
            decrypted = decrypted_bytes.decode('utf-8')
            return decrypted
        except Exception as e:
            # Log so we can diagnose key mismatches
            print(f"[ERROR] StorageManager._decrypt_token failed: {e}. Token prefix: '{encrypted_token[:20]}...'")
            # Return None — NOT the encrypted blob. This allows adapters to attempt a token refresh.
            return None

    @classmethod
    def get_available_providers(cls) -> List[Dict[str, Any]]:
        return [
            {"id": p_id, "name": meta["name"], "supported": meta["supported"]}
            for p_id, meta in SUPPORTED_PROVIDERS.items()
        ]

    @classmethod
    def auto_migrate_legacy_gdrive(cls, user_id: str):
        """
        Idempotent compat layer: if token.json.enc exists for user_id,
        creates a storage_connections record if one does not already exist.
        """
        token_path = DATA_DIR / "users" / user_id / "token.json.enc"
        if not token_path.exists():
            return

        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT * FROM storage_connections WHERE user_id = ? AND provider = 'google_drive'",
                (user_id,)
            ).fetchone()
            if not row:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO storage_connections 
                    (id, user_id, provider, provider_account_id, status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), user_id, "google_drive", f"gdrive_{user_id}", "active")
                )
                conn.commit()
        finally:
            conn.close()

    @classmethod
    def get_user_connections(cls, user_id: str) -> List[Dict[str, Any]]:
        cls.auto_migrate_legacy_gdrive(user_id)
        conn = get_db_connection()
        try:
            rows = conn.execute("SELECT * FROM storage_connections WHERE user_id = ?", (user_id,)).fetchall()
            connections = []
            for row in rows:
                res = dict(row)
                res["access_token"] = cls._decrypt_token(res.get("access_token"))
                res["refresh_token"] = cls._decrypt_token(res.get("refresh_token"))
                connections.append(res)
            return connections
        finally:
            conn.close()

    @classmethod
    def get_connection(cls, user_id: str, provider: Optional[str] = None) -> Optional[Dict[str, Any]]:
        connections = cls.get_user_connections(user_id)
        if not connections:
            return None
        if provider:
            for conn in connections:
                if conn["provider"] == provider:
                    return conn
            return None
        return connections[0]

    @classmethod
    def get_connection_status(cls, user_id: str) -> Dict[str, Any]:
        connections = cls.get_user_connections(user_id)
        provider_map = {}
        
        for p_id in SUPPORTED_PROVIDERS.keys():
            conn_info = next((c for c in connections if c["provider"] == p_id), None)
            if conn_info and conn_info["status"] == "active":
                provider_map[p_id] = {
                    "connected": True,
                    "status": "connected",
                    "provider_account_id": conn_info.get("provider_account_id"),
                    "connected_at": conn_info.get("created_at")
                }
            else:
                provider_map[p_id] = {
                    "connected": False,
                    "status": "not_connected",
                    "provider_account_id": None,
                    "connected_at": None
                }

        active_conn = connections[0] if connections else None
        return {
            "connected": any(p["connected"] for p in provider_map.values()),
            "provider": active_conn["provider"] if active_conn else None,
            "status": "connected" if any(p["connected"] for p in provider_map.values()) else "not_connected",
            "providers": provider_map
        }

    @classmethod
    def connect_storage(
        cls,
        user_id: str,
        provider: str,
        provider_account_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[str] = None,
        scope: Optional[str] = None,
        status: str = "active"
    ) -> Dict[str, Any]:
        if provider not in SUPPORTED_PROVIDERS:
            raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider}'")

        conn = get_db_connection()
        conn_id = str(uuid.uuid4())
        enc_access = cls._encrypt_token(access_token)
        enc_refresh = cls._encrypt_token(refresh_token)

        try:
            row = conn.execute(
                "SELECT id FROM storage_connections WHERE user_id = ? AND provider = ?",
                (user_id, provider)
            ).fetchone()

            if row:
                conn.execute(
                    """
                    UPDATE storage_connections SET
                        provider_account_id = ?,
                        access_token = ?,
                        refresh_token = ?,
                        token_expires_at = ?,
                        scope = ?,
                        status = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (provider_account_id, enc_access, enc_refresh, token_expires_at, scope, status, row["id"])
                )
            else:
                conn.execute(
                    """
                    INSERT INTO storage_connections 
                    (id, user_id, provider, provider_account_id, access_token, refresh_token, token_expires_at, scope, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (conn_id, user_id, provider, provider_account_id, enc_access, enc_refresh, token_expires_at, scope, status)
                )
            conn.commit()
            return cls.get_connection_status(user_id)
        except Exception as e:
            err_msg = str(e)
            raise HTTPException(status_code=400, detail=f"Database error: {err_msg}")
        finally:
            conn.close()


    @classmethod
    def disconnect_storage(cls, user_id: str, provider: Optional[str] = None) -> bool:
        conn = get_db_connection()
        try:
            if provider:
                conn.execute("DELETE FROM storage_connections WHERE user_id = ? AND provider = ?", (user_id, provider))
            else:
                conn.execute("DELETE FROM storage_connections WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @classmethod
    def get_adapter(cls, user_id: str, provider: Optional[str] = None, user_password: Optional[str] = None) -> StorageProvider:
        conn_info = cls.get_connection(user_id, provider=provider)
        if not conn_info:
            raise HTTPException(status_code=404, detail=f"No storage provider '{provider or 'connected'}' found for user.")

        target_provider = conn_info["provider"]
        if target_provider == "google_drive":
            return GoogleDriveAdapter(user_id=user_id, user_password=user_password)
        elif target_provider == "dropbox":
            return DropboxAdapter(
                user_id=user_id,
                access_token=conn_info.get("access_token"),
                refresh_token=conn_info.get("refresh_token")
            )
        elif target_provider == "onedrive":
            return OneDriveAdapter(
                user_id=user_id,
                access_token=conn_info.get("access_token"),
                refresh_token=conn_info.get("refresh_token")
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider '{target_provider}'")

