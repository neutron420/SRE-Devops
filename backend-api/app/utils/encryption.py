import base64
import logging
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_cipher():
    key = settings.ENCRYPTION_KEY
    if not key or key == "your_encryption_key_here":
        # Derive a stable 32-byte key from GEMINI_API_KEY if not explicitly set
        import hashlib
        m = hashlib.sha256()
        m.update((settings.GEMINI_API_KEY or "fallback-stable-key").encode())
        # Fernet keys need to be exactly 32 URL-safe base64-encoded bytes
        key = base64.urlsafe_b64encode(m.digest()).decode()
    
    try:
        return Fernet(key.encode())
    except Exception as e:
        logger.error(f"Failed to initialize Fernet cipher. Ensuring key format is correct: {str(e)}")
        # Ultimate fallback key just in case
        import hashlib
        m = hashlib.sha256()
        m.update(b"ultimate-sre-copilot-fallback-key")
        fallback_key = base64.urlsafe_b64encode(m.digest())
        return Fernet(fallback_key)

def encrypt_data(data: str) -> str:
    """
    Encrypts a string (e.g. kubeconfig) using AES-256 (Fernet)
    """
    if not data:
        return ""
    cipher = get_cipher()
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(token: str) -> str:
    """
    Decrypts an AES-256 encrypted string back to plaintext
    """
    if not token:
        return ""
    cipher = get_cipher()
    return cipher.decrypt(token.encode()).decode()
