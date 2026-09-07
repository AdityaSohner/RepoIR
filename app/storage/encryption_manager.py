import base64
import hmac
import hashlib
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MASTER_SECRET = os.getenv("VAULT_MASTER_SECRET") or os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or "repoir_default_server_vault_secret_key_v1"

def derive_vault_key(user_id: str) -> str:
    """Derives a deterministic, secure key string for a user using HMAC-SHA256."""
    return hmac.new(MASTER_SECRET.encode('utf-8'), user_id.encode('utf-8'), hashlib.sha256).hexdigest()

class EncryptionManager:
    """
    Handles transparent, server-managed file and token encryption.
    Derives encryption key from system secret and user_id.
    """
    
    def __init__(self, key_or_user_id: str, salt: bytes = b'repoir_static_salt_v1'):
        if len(key_or_user_id) < 32 or '-' in key_or_user_id:
            # Likely a user_id or short string - derive full key
            derived_pass = derive_vault_key(key_or_user_id)
        else:
            derived_pass = key_or_user_id
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key_bytes = kdf.derive(derived_pass.encode())
        self.fernet_key = base64.urlsafe_b64encode(key_bytes)
        self.cipher = Fernet(self.fernet_key)

    def encrypt_stream(self, raw_bytes: bytes) -> bytes:
        """Encrypts raw bytes into a secure blob."""
        return self.cipher.encrypt(raw_bytes)

    def decrypt_stream(self, encrypted_bytes: bytes) -> bytes:
        """Decrypts a secure blob back into original bytes."""
        return self.cipher.decrypt(encrypted_bytes)

