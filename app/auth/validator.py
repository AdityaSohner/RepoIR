import os
from google.oauth2 import id_token
from google.auth.transport import requests

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

def verify_google_token(token: str) -> str:
    """
    Verifies the Google ID Token and returns the unique user ID (sub).
    """
    if not GOOGLE_CLIENT_ID:
        return None
    try:
        # 1. Ask Google if this token is valid for our app
        id_info = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        
        # 2. 'sub' is the unique, permanent ID for this Google account (never changes)
        return id_info['sub'] 
    except ValueError:
        # Token was fake or expired
        return None
