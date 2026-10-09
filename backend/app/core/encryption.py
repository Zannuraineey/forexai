import base64
import hashlib
import logging
import re
from typing import Optional, List, Dict
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

logger = logging.getLogger(__name__)

# Common API key signature patterns to sanitize from exception strings & logs
API_KEY_REGEX = re.compile(r'(?:gsk_[a-zA-Z0-9_-]{20,}|sk-[a-zA-Z0-9_-]{20,}|xai-[a-zA-Z0-9_-]{20,}|AQ\.[a-zA-Z0-9_-]{20,})')

class SecretEncryptionService:
    """
    Handles secure encryption and decryption of external AI provider API keys.
    Uses Fernet (AES-128-CBC with HMAC-SHA256 authenticated encryption).
    Master key is deterministically derived from environment configuration,
    ensuring stability across application restarts and zero key loss.
    """
    _fernet: Optional[Fernet] = None
    _active_key_digest: Optional[str] = None

    @classmethod
    def _derive_fernet_key(cls, seed: str) -> bytes:
        """Derives a standard 32-byte URL-safe base64 Fernet key using SHA-256."""
        key_bytes = hashlib.sha256(seed.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(key_bytes)

    @classmethod
    def validate_master_key_configured(cls) -> None:
        """
        Validates that a master key is properly configured.
        In production, raises RuntimeError if ENCRYPTION_MASTER_KEY is missing or insecure.
        """
        master_key = getattr(settings, "ENCRYPTION_MASTER_KEY", "").strip()
        if settings.ENVIRONMENT == "production":
            if not master_key or len(master_key) < 16:
                raise RuntimeError(
                    "FATAL SECURITY FAILURE: ENCRYPTION_MASTER_KEY must be configured "
                    "with at least 16 characters in production environment."
                )

    @classmethod
    def _get_fernet(cls) -> Fernet:
        # Check if environment requires validation
        cls.validate_master_key_configured()

        master_key = getattr(settings, "ENCRYPTION_MASTER_KEY", "").strip()
        if not master_key:
            # Deterministic development/test fallback (stable across restarts)
            master_key = getattr(settings, "SECRET_KEY", "forexai_deterministic_dev_master_seed_v1")

        current_digest = hashlib.sha256(master_key.encode("utf-8")).hexdigest()
        if cls._fernet is None or cls._active_key_digest != current_digest:
            fernet_key = cls._derive_fernet_key(master_key)
            cls._fernet = Fernet(fernet_key)
            cls._active_key_digest = current_digest

        return cls._fernet

    @classmethod
    def encrypt_secret(cls, plaintext: str) -> str:
        """
        Encrypts a plaintext secret into an authenticated base64 ciphertext string.
        Refuses to encrypt if production lacks a valid master key.
        """
        if not plaintext:
            return ""
        cls.validate_master_key_configured()
        fernet = cls._get_fernet()
        return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    @classmethod
    def decrypt_secret(cls, ciphertext: str) -> str:
        """
        Decrypts an authenticated ciphertext string back to plaintext.
        Handles tampered/corrupted data safely via InvalidToken without crashing.
        """
        if not ciphertext:
            return ""
        try:
            fernet = cls._get_fernet()
            return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            logger.warning("Decryption failed: Token is invalid, corrupted, or tampered with.")
            return ""
        except Exception as e:
            logger.warning("Decryption failed: %s", cls.sanitize_message(str(e)))
            return ""

    @classmethod
    def rotate_secret(cls, ciphertext: str, old_master_key: str, new_master_key: str) -> str:
        """
        Rotates an encrypted record from an old master key to a new master key.
        Used during administrative key rotation procedures.
        """
        if not ciphertext or not old_master_key or not new_master_key:
            raise ValueError("All parameters (ciphertext, old_master_key, new_master_key) are required.")
        
        old_fernet = Fernet(cls._derive_fernet_key(old_master_key))
        new_fernet = Fernet(cls._derive_fernet_key(new_master_key))

        plaintext_bytes = old_fernet.decrypt(ciphertext.encode("utf-8"))
        return new_fernet.encrypt(plaintext_bytes).decode("utf-8")

    @classmethod
    def mask_secret(cls, plaintext: str) -> str:
        """Returns a safe preview mask without revealing the sensitive secret."""
        if not plaintext:
            return ""
        if len(plaintext) <= 8:
            return "••••••••"
        return f"{plaintext[:4]}••••••••{plaintext[-4:]}"

    @classmethod
    def sanitize_message(cls, message: str) -> str:
        """
        Sanitizes raw API keys and Bearer tokens from exception messages or log output.
        """
        if not message:
            return ""
        return API_KEY_REGEX.sub("[REDACTED_API_KEY]", message)
