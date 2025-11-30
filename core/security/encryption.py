"""Data encryption utilities for sensitive data protection.

Provides:
- Field-level encryption for PII
- Key management with rotation support
- AES-256-GCM encryption
- Secure key derivation
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
import hashlib
import os
import secrets
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EncryptedValue:
    """Encrypted value with metadata."""

    ciphertext: bytes
    nonce: bytes
    tag: bytes
    key_id: str
    encrypted_at: datetime
    algorithm: str = "AES-256-GCM"

    def to_string(self) -> str:
        """Encode to storable string format."""
        data = {
            "c": base64.b64encode(self.ciphertext).decode(),
            "n": base64.b64encode(self.nonce).decode(),
            "t": base64.b64encode(self.tag).decode(),
            "k": self.key_id,
            "a": self.algorithm,
            "ts": self.encrypted_at.isoformat(),
        }
        import json

        return base64.b64encode(json.dumps(data).encode()).decode()

    @classmethod
    def from_string(cls, encoded: str) -> EncryptedValue:
        """Decode from stored string format."""
        import json

        data = json.loads(base64.b64decode(encoded).decode())
        return cls(
            ciphertext=base64.b64decode(data["c"]),
            nonce=base64.b64decode(data["n"]),
            tag=base64.b64decode(data["t"]),
            key_id=data["k"],
            algorithm=data.get("a", "AES-256-GCM"),
            encrypted_at=datetime.fromisoformat(data["ts"]),
        )


class KeyManager:
    """Manages encryption keys with rotation support.

    Features:
    - Key generation and storage
    - Key rotation
    - Multiple active keys
    - Key versioning

    Example:
        >>> km = KeyManager()
        >>> key_id = km.generate_key("primary")
        >>> key = km.get_key(key_id)
    """

    def __init__(self, master_key: bytes | None = None) -> None:
        """Initialize key manager.

        Args:
            master_key: Master key for encrypting stored keys
        """
        self._master_key = master_key or self._derive_master_key()
        self._keys: dict[str, bytes] = {}
        self._key_metadata: dict[str, dict[str, Any]] = {}
        self._current_key_id: str | None = None
        self.logger = logger.bind(component="key_manager")

    def _derive_master_key(self) -> bytes:
        """Derive master key from environment or generate new one."""
        env_key = os.getenv("ENCRYPTION_MASTER_KEY")
        if env_key:
            # Derive key from environment variable
            return hashlib.pbkdf2_hmac(
                "sha256",
                env_key.encode(),
                b"mega_agent_salt",  # Fixed salt for deterministic derivation
                100000,
                dklen=32,
            )
        # Generate ephemeral key (not recommended for production)
        self.logger.warning(
            "no_master_key_configured",
            message="Using ephemeral master key - set ENCRYPTION_MASTER_KEY for persistence",
        )
        return secrets.token_bytes(32)

    def generate_key(self, name: str) -> str:
        """Generate a new encryption key.

        Args:
            name: Key name/purpose

        Returns:
            Key ID
        """
        key_id = f"{name}_{secrets.token_hex(8)}"
        key = secrets.token_bytes(32)  # 256-bit key

        self._keys[key_id] = key
        self._key_metadata[key_id] = {
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
            "rotated_from": None,
            "status": "active",
        }

        if self._current_key_id is None:
            self._current_key_id = key_id

        self.logger.info("key_generated", key_id=key_id, name=name)
        return key_id

    def get_key(self, key_id: str) -> bytes | None:
        """Get encryption key by ID."""
        return self._keys.get(key_id)

    def get_current_key(self) -> tuple[str, bytes] | None:
        """Get current active key."""
        if self._current_key_id and self._current_key_id in self._keys:
            return self._current_key_id, self._keys[self._current_key_id]
        return None

    def rotate_key(self, old_key_id: str, new_name: str | None = None) -> str:
        """Rotate to a new key.

        Args:
            old_key_id: ID of key being rotated
            new_name: Name for new key

        Returns:
            New key ID
        """
        if old_key_id not in self._keys:
            raise ValueError(f"Key {old_key_id} not found")

        # Get old key metadata
        old_meta = self._key_metadata.get(old_key_id, {})
        name = new_name or old_meta.get("name", "rotated")

        # Generate new key
        new_key_id = self.generate_key(name)
        self._key_metadata[new_key_id]["rotated_from"] = old_key_id

        # Mark old key as rotated
        self._key_metadata[old_key_id]["status"] = "rotated"
        self._key_metadata[old_key_id]["rotated_to"] = new_key_id
        self._key_metadata[old_key_id]["rotated_at"] = datetime.utcnow().isoformat()

        # Update current key
        self._current_key_id = new_key_id

        self.logger.info(
            "key_rotated",
            old_key_id=old_key_id,
            new_key_id=new_key_id,
        )

        return new_key_id

    def list_keys(self) -> list[dict[str, Any]]:
        """List all keys with metadata."""
        return [{"key_id": k, **v} for k, v in self._key_metadata.items()]


class EncryptionService:
    """Service for encrypting and decrypting sensitive data.

    Provides:
    - AES-256-GCM encryption
    - Field-level encryption
    - Key rotation support
    - Batch operations

    Example:
        >>> service = EncryptionService()
        >>> encrypted = service.encrypt("sensitive data")
        >>> decrypted = service.decrypt(encrypted)
    """

    def __init__(self, key_manager: KeyManager | None = None) -> None:
        """Initialize encryption service.

        Args:
            key_manager: Key manager instance
        """
        self.key_manager = key_manager or KeyManager()
        self.logger = logger.bind(component="encryption_service")

        # Ensure we have at least one key
        if self.key_manager.get_current_key() is None:
            self.key_manager.generate_key("default")

    def encrypt(self, plaintext: str | bytes) -> EncryptedValue:
        """Encrypt data using AES-256-GCM.

        Args:
            plaintext: Data to encrypt

        Returns:
            EncryptedValue with ciphertext and metadata
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Get current key
        key_info = self.key_manager.get_current_key()
        if not key_info:
            raise RuntimeError("No encryption key available")

        key_id, key = key_info

        # Convert to bytes if string
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        # Generate nonce
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM

        # Encrypt
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # GCM appends the tag to ciphertext
        tag = ciphertext[-16:]
        ciphertext = ciphertext[:-16]

        return EncryptedValue(
            ciphertext=ciphertext,
            nonce=nonce,
            tag=tag,
            key_id=key_id,
            encrypted_at=datetime.utcnow(),
        )

    def decrypt(self, encrypted: EncryptedValue | str) -> bytes:
        """Decrypt data.

        Args:
            encrypted: EncryptedValue or encoded string

        Returns:
            Decrypted bytes
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Parse if string
        if isinstance(encrypted, str):
            encrypted = EncryptedValue.from_string(encrypted)

        # Get key
        key = self.key_manager.get_key(encrypted.key_id)
        if not key:
            raise ValueError(f"Key {encrypted.key_id} not found")

        # Decrypt
        aesgcm = AESGCM(key)
        ciphertext_with_tag = encrypted.ciphertext + encrypted.tag

        return aesgcm.decrypt(encrypted.nonce, ciphertext_with_tag, None)

    def decrypt_string(self, encrypted: EncryptedValue | str) -> str:
        """Decrypt to string."""
        return self.decrypt(encrypted).decode("utf-8")

    def encrypt_field(self, data: dict[str, Any], field: str) -> dict[str, Any]:
        """Encrypt a specific field in a dictionary.

        Args:
            data: Dictionary containing the field
            field: Field name to encrypt

        Returns:
            Dictionary with encrypted field
        """
        if field not in data:
            return data

        result = data.copy()
        value = data[field]

        if value is not None:
            encrypted = self.encrypt(str(value))
            result[field] = encrypted.to_string()
            result[f"_{field}_encrypted"] = True

        return result

    def decrypt_field(self, data: dict[str, Any], field: str) -> dict[str, Any]:
        """Decrypt a specific field in a dictionary.

        Args:
            data: Dictionary with encrypted field
            field: Field name to decrypt

        Returns:
            Dictionary with decrypted field
        """
        if field not in data or not data.get(f"_{field}_encrypted"):
            return data

        result = data.copy()
        encrypted_value = data[field]

        if encrypted_value is not None:
            result[field] = self.decrypt_string(encrypted_value)
            del result[f"_{field}_encrypted"]

        return result

    def encrypt_fields(
        self,
        data: dict[str, Any],
        fields: list[str],
    ) -> dict[str, Any]:
        """Encrypt multiple fields.

        Args:
            data: Dictionary
            fields: Fields to encrypt

        Returns:
            Dictionary with encrypted fields
        """
        result = data.copy()
        for f in fields:
            result = self.encrypt_field(result, f)
        return result

    def decrypt_fields(
        self,
        data: dict[str, Any],
        fields: list[str],
    ) -> dict[str, Any]:
        """Decrypt multiple fields.

        Args:
            data: Dictionary with encrypted fields
            fields: Fields to decrypt

        Returns:
            Dictionary with decrypted fields
        """
        result = data.copy()
        for f in fields:
            result = self.decrypt_field(result, f)
        return result


# PII fields that should be encrypted
PII_FIELDS = [
    "ssn",
    "social_security_number",
    "passport_number",
    "alien_number",
    "email",
    "phone",
    "phone_number",
    "address",
    "date_of_birth",
    "bank_account",
    "credit_card",
]


def get_encryption_service() -> EncryptionService:
    """Get global encryption service instance."""
    global _encryption_service
    if "_encryption_service" not in globals():
        _encryption_service = EncryptionService()
    return _encryption_service  # type: ignore


__all__ = [
    "PII_FIELDS",
    "EncryptedValue",
    "EncryptionService",
    "KeyManager",
    "get_encryption_service",
]
