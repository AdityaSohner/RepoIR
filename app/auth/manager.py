
import jwt
import datetime
import sqlite3
import bcrypt
import os
import uuid
from pathlib import Path
from fastapi import HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.config import DATA_DIR

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or "CHANGE_ME_IN_ENV"
ALGORITHM = "HS256"

BASE_DATA_DIR = DATA_DIR
USERS_DB = BASE_DATA_DIR / "users.db"

def get_users_db_connection() -> sqlite3.Connection:
    BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(USERS_DB), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn

def init_users_db():
    conn = get_users_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                name TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS storage_connections (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                provider_account_id TEXT NOT NULL,
                access_token TEXT,
                refresh_token TEXT,
                token_expires_at TIMESTAMP,
                scope TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE(user_id, provider)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_identities (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                provider_user_id TEXT NOT NULL,
                email TEXT,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE(provider, provider_user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS oauth_states (
                state TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Safely migrate existing users table if columns are missing
        user_migrations = [
            "ALTER TABLE users ADD COLUMN name TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE users ADD COLUMN password_hash TEXT",
        ]
        for migration in user_migrations:
            try:
                conn.execute(migration)
                conn.commit()
            except Exception:
                pass
    finally:
        conn.close()

init_users_db()

class AuthManager:
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    @staticmethod
    def create_access_token(user_id: str):
        # Set expiration to 100 years for "forever persistence"
        payload = {
            "sub": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=36500)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload["sub"]
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    @classmethod
    def create_user(cls, email: str, password: str) -> str:
        user_id = str(uuid.uuid4())
        hashed = cls.hash_password(password)
        conn = get_users_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (user_id, email, hashed_password) VALUES (?, ?, ?)",
                (user_id, email, hashed)
            )
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Email already exists")
        finally:
            conn.close()

    @classmethod
    def authenticate_user(cls, email: str, password: str) -> str:
        conn = get_users_db_connection()
        try:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if not row or not cls.verify_password(password, row["hashed_password"]):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            return row["user_id"]
        finally:
            conn.close()

    @classmethod
    def search_users_by_email(cls, query: str, exclude_user_id: str, limit: int = 10) -> list[dict]:
        """Find registered recipients by email without exposing the current user."""
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return []
        conn = get_users_db_connection()
        try:
            rows = conn.execute(
                """
                SELECT user_id, email
                FROM users
                WHERE user_id != ? AND lower(email) LIKE ? AND is_active = 1
                ORDER BY lower(email)
                LIMIT ?
                """,
                (exclude_user_id, f"%{normalized_query}%", limit),
            ).fetchall()
            return [{"user_id": row["user_id"], "email": row["email"]} for row in rows]
        finally:
            conn.close()

    @classmethod
    def get_user_by_email(cls, email: str, exclude_user_id: str = None) -> dict | None:
        conn = get_users_db_connection()
        try:
            query = "SELECT user_id, email FROM users WHERE lower(email) = lower(?) AND is_active = 1"
            params = [email.strip()]
            if exclude_user_id:
                query += " AND user_id != ?"
                params.append(exclude_user_id)
            row = conn.execute(query, params).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @classmethod
    def get_or_link_oauth_user(cls, provider: str, provider_user_id: str, email: str = None, name: str = None, current_user_id: str = None) -> str:
        conn = get_users_db_connection()
        try:
            # 1. Look up existing identity link
            identity = conn.execute(
                "SELECT user_id FROM user_identities WHERE provider = ? AND provider_user_id = ?",
                (provider, provider_user_id)
            ).fetchone()
            
            if identity:
                return identity["user_id"]
                
            # 2. If caller is logged in, link provider to current user
            if current_user_id:
                user_id = current_user_id
            else:
                # 3. Check if user with matching email exists
                row = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone() if email else None
                if row:
                    user_id = row["user_id"]
                else:
                    # 4. Create new user account
                    user_id = str(uuid.uuid4())
                    user_email = email or f"{provider}_{provider_user_id}@repoir.local"
                    hashed = cls.hash_password(str(uuid.uuid4()))
                    conn.execute(
                        "INSERT INTO users (user_id, email, hashed_password, name) VALUES (?, ?, ?, ?)",
                        (user_id, user_email, hashed, name or "")
                    )
                    conn.commit()

            # Insert identity record
            conn.execute(
                """
                INSERT OR REPLACE INTO user_identities (id, user_id, provider, provider_user_id, email, name)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), user_id, provider, provider_user_id, email or "", name or "")
            )
            conn.commit()
            return user_id
        finally:
            conn.close()

    @classmethod
    def verify_google_id_token(cls, token: str) -> dict:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not client_id:
            raise HTTPException(status_code=500, detail="Google Client ID not configured")
        try:
            id_info = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
            return id_info
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Google Auth failed: {str(e)}")

    @classmethod
    def get_or_create_google_user(cls, google_id_info: dict, current_user_id: str = None) -> str:
        google_sub = google_id_info["sub"]
        email = google_id_info.get("email")
        name = google_id_info.get("name", "")
        user_id = cls.get_or_link_oauth_user("google", google_sub, email=email, name=name, current_user_id=current_user_id)
        
        from app.storage.manager import StorageManager
        try:
            StorageManager.connect_storage(
                user_id=user_id,
                provider="google_drive",
                provider_account_id=f"gdrive_{user_id}",
                status="active"
            )
        except Exception as e:
            print(f"Auto-connect GDrive notice: {e}")

        return user_id



    @classmethod
    def create_oauth_state(cls, user_id: str, provider: str, expires_in_seconds: int = 900) -> str:
        import secrets
        state = secrets.token_urlsafe(32)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in_seconds)
        conn = get_users_db_connection()
        try:
            conn.execute(
                "INSERT INTO oauth_states (state, user_id, provider, expires_at, used) VALUES (?, ?, ?, ?, 0)",
                (state, user_id, provider, expires_at.isoformat())
            )
            conn.commit()
            return state
        finally:
            conn.close()

    @classmethod
    def verify_and_consume_oauth_state(cls, state: str, expected_provider: str, expected_user_id: str = None) -> str:
        conn = get_users_db_connection()
        try:
            row = conn.execute("SELECT * FROM oauth_states WHERE state = ?", (state,)).fetchone()
            
            if not row or row["used"] == 1:
                raise HTTPException(status_code=400, detail="Invalid, missing, or already used OAuth state.")

            # Expiry check
            expires_at = datetime.datetime.fromisoformat(row["expires_at"])
            if datetime.datetime.utcnow() > expires_at:
                raise HTTPException(status_code=400, detail="OAuth state has expired.")

            if row["provider"] != expected_provider:
                raise HTTPException(status_code=400, detail="OAuth state provider mismatch.")

            if expected_user_id and row["user_id"] != expected_user_id:
                raise HTTPException(status_code=400, detail="OAuth state does not belong to authenticated user.")

            # Mark consumed
            conn.execute("UPDATE oauth_states SET used = 1 WHERE state = ?", (state,))
            conn.commit()
            return row["user_id"]
        finally:
            conn.close()
