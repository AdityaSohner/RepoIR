
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

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "REPOIR_SUPER_SECRET_KEY") # Use env for production
ALGORITHM = "HS256"

BASE_DATA_DIR = Path("data")
USERS_DB = BASE_DATA_DIR / "users.db"

def init_users_db():
    BASE_DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(USERS_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
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
        import uuid
        user_id = str(uuid.uuid4())
        hashed = cls.hash_password(password)
        conn = sqlite3.connect(str(USERS_DB))
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
        conn = sqlite3.connect(str(USERS_DB))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if not row or not cls.verify_password(password, row["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return row["user_id"]

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
    def get_or_create_google_user(cls, google_id_info: dict) -> str:
        google_sub = google_id_info["sub"]
        email = google_id_info["email"]
        
        conn = sqlite3.connect(str(USERS_DB))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (google_sub,)).fetchone()
        
        if row:
            conn.close()
            return row["user_id"]
        
        # Create a "Shadow User" for Google Auth using their sub ID
        # No random UUID, use the sub so it's sticky after restarts/clears
        hashed = cls.hash_password(str(uuid.uuid4()))
        conn.execute(
            "INSERT INTO users (user_id, email, hashed_password) VALUES (?, ?, ?)",
            (google_sub, email, hashed)
        )
        conn.commit()
        conn.close()
        return google_sub
