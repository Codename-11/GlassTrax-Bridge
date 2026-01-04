### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - API Key Model -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
API Key Model

Stores API keys with:
- Hashed key value (bcrypt) - the actual key is only shown once on creation
- Key prefix for identification (first 8 chars stored plaintext)
- Permissions (JSON list of allowed resources)
- Rate limiting settings
- Expiration support
"""

import secrets
import string
import bcrypt as _bcrypt
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from api.database import Base


def hash_key(plaintext: str) -> str:
    """Hash a key using bcrypt"""
    return _bcrypt.hashpw(plaintext.encode(), _bcrypt.gensalt()).decode()


def verify_key_hash(plaintext: str, hashed: str) -> bool:
    """Verify a plaintext key against a hash"""
    return _bcrypt.checkpw(plaintext.encode(), hashed.encode())


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.

    Format: gtb_{random_chars}
    Example: gtb_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6

    Args:
        length: Length of the random portion (default 32)

    Returns:
        New API key string
    """
    chars = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(length))
    return f"gtb_{random_part}"


class APIKey(Base):
    """
    API Key model - authentication credential for API access.

    The actual key is hashed with bcrypt and cannot be retrieved.
    Only the first 8 characters (prefix) are stored in plaintext
    for identification purposes.
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "Production", "Development"
    description = Column(String(500), nullable=True)

    # Key storage - only prefix is visible, full key is hashed
    key_prefix = Column(String(12), nullable=False)  # "gtb_xxxx" for display
    key_hash = Column(String(255), nullable=False)  # bcrypt hash

    # Permissions - list of allowed resources
    # e.g., ["customers:read", "orders:read", "orders:write"]
    permissions = Column(JSON, default=list, nullable=False)

    # Rate limiting
    rate_limit = Column(Integer, default=60, nullable=False)  # requests per minute

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}')>"

    @classmethod
    def create_key(
        cls,
        tenant_id: int,
        name: str,
        permissions: List[str],
        description: Optional[str] = None,
        rate_limit: int = 60,
        expires_at: Optional[datetime] = None,
    ) -> tuple["APIKey", str]:
        """
        Create a new API key with a generated secret.

        Returns both the APIKey model instance and the plaintext key.
        The plaintext key should be shown to the user once and never stored.

        Args:
            tenant_id: ID of the owning tenant
            name: Human-readable name for the key
            permissions: List of permission strings
            description: Optional description
            rate_limit: Requests per minute (default 60)
            expires_at: Optional expiration datetime

        Returns:
            Tuple of (APIKey instance, plaintext key string)
        """
        # Generate the key
        plaintext_key = generate_api_key()

        # Create the model
        api_key = cls(
            tenant_id=tenant_id,
            name=name,
            description=description,
            key_prefix=plaintext_key[:12],  # "gtb_" + first 8 chars
            key_hash=hash_key(plaintext_key),
            permissions=permissions,
            rate_limit=rate_limit,
            expires_at=expires_at,
        )

        return api_key, plaintext_key

    def verify_key(self, plaintext_key: str) -> bool:
        """
        Verify a plaintext key against this key's hash.

        Args:
            plaintext_key: The key to verify

        Returns:
            True if the key matches, False otherwise
        """
        return verify_key_hash(plaintext_key, self.key_hash)

    def is_valid(self) -> bool:
        """
        Check if this key is valid (active and not expired).

        Returns:
            True if the key can be used, False otherwise
        """
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def has_permission(self, resource: str, action: str = "read") -> bool:
        """
        Check if this key has a specific permission.

        Args:
            resource: Resource name (e.g., "customers", "orders")
            action: Action type (e.g., "read", "write")

        Returns:
            True if permission granted, False otherwise
        """
        if not self.permissions:
            return False

        # Check for exact permission
        permission = f"{resource}:{action}"
        if permission in self.permissions:
            return True

        # Check for wildcard permissions
        if f"{resource}:*" in self.permissions:
            return True
        if "*:*" in self.permissions:
            return True

        return False

    def record_use(self):
        """Record that this key was used (updates last_used_at and use_count)"""
        self.last_used_at = datetime.utcnow()
        self.use_count += 1
