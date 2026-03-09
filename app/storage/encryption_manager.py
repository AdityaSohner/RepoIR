import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class EncryptionManager:
    """
    Handles file-level encryption before uploading to Google Drive.
    Ensures that files on GDrive are unreadable without the User's Password.
    """
    
    def __init__(self, user_password: str, salt: bytes = b'repoir_static_salt_v1'):
        # 1. Derive a 32-byte key from the password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key_bytes = kdf.derive(user_password.encode())
        
        # 2. Encode to base64 for Fernet
        self.fernet_key = base64.urlsafe_b64encode(key_bytes)
        self.cipher = Fernet(self.fernet_key)

    def encrypt_stream(self, raw_bytes: bytes) -> bytes:
        """Encrypts raw file bytes into a secure blob."""
        return self.cipher.encrypt(raw_bytes)

    def decrypt_stream(self, encrypted_bytes: bytes) -> bytes:
        """Decrypts a secure blob back into original file bytes."""
        return self.cipher.decrypt(encrypted_bytes)
