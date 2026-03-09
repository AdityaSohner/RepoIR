from google.oauth2 import id_token
from google.auth.transport import requests

# Use the Client ID from your credentials.json
GOOGLE_CLIENT_ID = "431198643697-t8iv17kng6cjqdm173tliajok3aukb5b.apps.googleusercontent.com"

def verify_google_token(token: str) -> str:
    """
    Verifies the Google ID Token and returns the unique user ID (sub).
    """
    try:
        # 1. Ask Google if this token is valid for our app
        id_info = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        
        # 2. 'sub' is the unique, permanent ID for this Google account (never changes)
        return id_info['sub'] 
    except ValueError:
        # Token was fake or expired
        return None
