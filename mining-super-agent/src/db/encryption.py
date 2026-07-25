"""
Database encryption — column-level encryption for sensitive fields.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256)
with key derivation via HKDF from a master encryption key.

Encrypted fields are transparent to SQLAlchemy queries — they are
encrypted on write and decrypted on read. The database only ever
sees ciphertext.

Usage:
    from src.db.encryption import EncryptedString, EncryptedText, EncryptedJSON

    class MyModel(Base):
        api_key = mapped_column(EncryptedString(512))
        gps_coords = mapped_column(EncryptedText())
        config_data = mapped_column(EncryptedJSON())
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import sys
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import String, Text, TypeDecorator

logger = logging.getLogger(__name__)

# ── Key Management ───────────────────────────────────────────────

_MASTER_KEY: bytes | None = None
_FERNET: Fernet | None = None


def _get_master_key() -> bytes:
    """Get or derive the master encryption key.

    The ENCRYPTION_KEY environment variable must be set. If missing,
    the application REFUSES to start — this is intentional.

    For key rotation, multiple keys can be provided (comma-separated).
    The first key is used for encryption; all keys are tried for decryption.
    """
    global _MASTER_KEY

    if _MASTER_KEY is not None:
        return _MASTER_KEY

    raw_key = os.getenv("ENCRYPTION_KEY", "")
    if not raw_key or raw_key.startswith("CHANGE_ME"):
        print(
            "\n🚨 CRITICAL: ENCRYPTION_KEY is not set or uses placeholder.\n"
            "   Generate with: python -c "
            "\"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
            "   The application CANNOT start without a valid encryption key.\n"
        )
        sys.exit(1)

    # Support comma-separated keys for rotation (first = active, rest = legacy)
    keys = [k.strip() for k in raw_key.split(",") if k.strip()]
    _MASTER_KEY = keys[0].encode() if keys[0].startswith("gAA") else base64.urlsafe_b64decode(keys[0])

    return _MASTER_KEY


def _derive_fernet_key(master_key: bytes, context: str = b"mining-super-agent-db-encryption") -> bytes:
    """Derive a Fernet key from the master key using HKDF.

    This ensures:
    1. The master key is never used directly for encryption
    2. Different contexts can derive different keys
    3. The derived key is exactly 32 bytes (Fernet requirement)
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=context,
    )
    derived = hkdf.derive(master_key)
    return base64.urlsafe_b64encode(derived)


def _get_fernet() -> Fernet:
    """Get the Fernet cipher instance (lazy initialization)."""
    global _FERNET

    if _FERNET is not None:
        return _FERNET

    master_key = _get_master_key()
    derived_key = _derive_fernet_key(master_key)
    _FERNET = Fernet(derived_key)

    return _FERNET


def _get_legacy_fernet_keys() -> list[Fernet]:
    """Get Fernet instances for all legacy keys (for key rotation).

    When ENCRYPTION_KEY contains comma-separated keys, we try all of
    them for decryption (the first is used for encryption).
    """
    raw_key = os.getenv("ENCRYPTION_KEY", "")
    if not raw_key:
        return []

    keys = [k.strip() for k in raw_key.split(",") if k.strip()]
    if len(keys) <= 1:
        return []

    fernet_instances = []
    for key_str in keys[1:]:  # Skip first (active) key
        try:
            if key_str.startswith("gAA"):
                key_bytes = key_str.encode()
            else:
                key_bytes = base64.urlsafe_b64decode(key_str)
            derived = _derive_fernet_key(key_bytes)
            fernet_instances.append(Fernet(derived))
        except Exception as e:
            logger.warning("Failed to derive Fernet from legacy key: %s", e)

    return fernet_instances


# ── Encryption / Decryption Helpers ─────────────────────────────

def encrypt_value(plaintext: str | None) -> str | None:
    """Encrypt a plaintext string. Returns None if input is None."""
    if plaintext is None:
        return None
    fernet = _get_fernet()
    token = fernet.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(ciphertext: str | None) -> str | None:
    """Decrypt a ciphertext string.

    Tries the active key first, then any legacy keys (for key rotation).
    Returns None if input is None.
    """
    if ciphertext is None:
        return None

    # Try active key
    fernet = _get_fernet()
    try:
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        pass

    # Try legacy keys
    for legacy_fernet in _get_legacy_fernet_keys():
        try:
            return legacy_fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            continue

    # All keys failed
    logger.error("Failed to decrypt value — no matching key found")
    raise InvalidToken("Unable to decrypt: no matching encryption key")


def is_encrypted(value: str | None) -> bool:
    """Check if a value looks like a Fernet-encrypted token.

    Fernet tokens are base64-encoded and start with 'gAAAAA'.
    This is a heuristic — not a guarantee.
    """
    if not value:
        return False
    return value.startswith("gAAAAA") and len(value) > 50


# ── SQLAlchemy Custom Types ──────────────────────────────────────

class EncryptedString(TypeDecorator):
    """Encrypted string column type for SQLAlchemy.

    Transparently encrypts on write and decrypts on read.
    The database stores ciphertext; the application sees plaintext.

    Args:
        length: Maximum stored length (ciphertext is ~2x plaintext).
                Default 1024 bytes covers most API keys and tokens.
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 1024, **kwargs):
        super().__init__(length=length, **kwargs)

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        """Encrypt before writing to database."""
        if value is None:
            return None
        # Don't double-encrypt if already encrypted
        if is_encrypted(value):
            return value
        return encrypt_value(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        """Decrypt when reading from database."""
        if value is None:
            return None
        # Only decrypt if it looks encrypted
        if is_encrypted(value):
            return decrypt_value(value)
        return value


class EncryptedText(TypeDecorator):
    """Encrypted text column type for larger fields.

    Same as EncryptedString but uses Text for unlimited length.
    Suitable for GPS coordinates, location data, and longer secrets.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        if is_encrypted(value):
            return value
        return encrypt_value(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        if is_encrypted(value):
            return decrypt_value(value)
        return value


class EncryptedJSON(TypeDecorator):
    """Encrypted JSON column type.

    Stores a JSON-serializable Python object as encrypted ciphertext.
    Useful for sensitive configuration data, API response caches, etc.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any | None, dialect) -> str | None:
        if value is None:
            return None
        json_str = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return encrypt_value(json_str)

    def process_result_value(self, value: str | None, dialect) -> Any | None:
        if value is None:
            return None
        if is_encrypted(value):
            decrypted = decrypt_value(value)
            return json.loads(decrypted)
        # Legacy: might be stored as plain JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value


# ── Startup Validation ───────────────────────────────────────────

def validate_encryption_key() -> bool:
    """Validate that encryption is working correctly.

    Called at application startup. Tests encrypt→decrypt roundtrip
    to ensure the key is valid and the crypto library is working.
    """
    try:
        test_value = "mining-super-agent-encryption-test-2024"
        encrypted = encrypt_value(test_value)
        decrypted = decrypt_value(encrypted)

        if decrypted != test_value:
            logger.error("Encryption roundtrip failed: decrypted value mismatch")
            return False

        if not is_encrypted(encrypted):
            logger.error("Encrypted value doesn't look like Fernet token")
            return False

        logger.info("✅ Encryption key validation passed")
        return True

    except Exception as e:
        logger.error("Encryption key validation failed: %s", e)
        return False
