"""
Unit tests for APIKey model.

Tests key generation, verification, permissions, and validation.
"""

import pytest
from datetime import datetime, timedelta

from api.models.api_key import (
    APIKey,
    generate_api_key,
    hash_key,
    verify_key_hash,
)


class TestKeyGeneration:
    """Test API key generation."""

    def test_generate_key_has_prefix(self):
        """Generated key should start with gtb_ prefix."""
        key = generate_api_key()
        assert key.startswith("gtb_")

    def test_generate_key_default_length(self):
        """Default key length should be gtb_ + 32 chars = 36 total."""
        key = generate_api_key()
        assert len(key) == 36

    def test_generate_key_custom_length(self):
        """Custom length should be respected."""
        key = generate_api_key(length=16)
        assert len(key) == 20  # gtb_ + 16

    def test_generate_key_unique(self):
        """Each generated key should be unique."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100

    def test_generate_key_alphanumeric(self):
        """Key should only contain alphanumeric characters after prefix."""
        key = generate_api_key()
        random_part = key[4:]  # Remove gtb_
        assert random_part.isalnum()


class TestKeyHashing:
    """Test key hashing and verification."""

    def test_hash_key_returns_string(self):
        """hash_key should return a string."""
        result = hash_key("test_key")
        assert isinstance(result, str)

    def test_hash_key_different_from_input(self):
        """Hash should be different from plaintext."""
        plaintext = "test_key_123"
        hashed = hash_key(plaintext)
        assert hashed != plaintext

    def test_hash_key_starts_with_bcrypt_prefix(self):
        """bcrypt hash should start with $2b$."""
        hashed = hash_key("test")
        assert hashed.startswith("$2")

    def test_verify_key_hash_correct(self):
        """Correct key should verify successfully."""
        plaintext = "gtb_testkey123"
        hashed = hash_key(plaintext)
        assert verify_key_hash(plaintext, hashed) is True

    def test_verify_key_hash_incorrect(self):
        """Incorrect key should fail verification."""
        hashed = hash_key("gtb_correct")
        assert verify_key_hash("gtb_wrong", hashed) is False


class TestAPIKeyModel:
    """Test APIKey model methods."""

    def test_create_key_returns_tuple(self):
        """create_key should return (APIKey, plaintext) tuple."""
        api_key, plaintext = APIKey.create_key(
            tenant_id=1,
            name="Test Key",
            permissions=["customers:read"],
        )

        assert isinstance(api_key, APIKey)
        assert isinstance(plaintext, str)

    def test_create_key_stores_prefix(self):
        """Key prefix should be stored (first 12 chars)."""
        api_key, plaintext = APIKey.create_key(
            tenant_id=1,
            name="Test Key",
            permissions=["customers:read"],
        )

        assert api_key.key_prefix == plaintext[:12]

    def test_create_key_hashes_full_key(self):
        """Full key should be hashed."""
        api_key, plaintext = APIKey.create_key(
            tenant_id=1,
            name="Test Key",
            permissions=["customers:read"],
        )

        assert api_key.key_hash != plaintext
        assert api_key.key_hash.startswith("$2")

    def test_create_key_with_all_params(self):
        """All parameters should be stored correctly."""
        expires = datetime.utcnow() + timedelta(days=30)

        api_key, _ = APIKey.create_key(
            tenant_id=42,
            name="Full Test",
            permissions=["customers:read", "orders:write"],
            description="Test description",
            rate_limit=100,
            expires_at=expires,
        )

        assert api_key.tenant_id == 42
        assert api_key.name == "Full Test"
        assert api_key.permissions == ["customers:read", "orders:write"]
        assert api_key.description == "Test description"
        assert api_key.rate_limit == 100
        assert api_key.expires_at == expires


class TestAPIKeyVerification:
    """Test APIKey.verify_key method."""

    def test_verify_key_correct(self):
        """Correct key should verify."""
        api_key, plaintext = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=[],
        )

        assert api_key.verify_key(plaintext) is True

    def test_verify_key_incorrect(self):
        """Incorrect key should not verify."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=[],
        )

        assert api_key.verify_key("gtb_wrongkey12345678901234567890") is False


class TestAPIKeyValidity:
    """Test APIKey.is_valid method."""

    def test_is_valid_active_no_expiry(self):
        """Active key without expiry should be valid."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=[],
        )
        api_key.is_active = True

        assert api_key.is_valid() is True

    def test_is_valid_inactive(self):
        """Inactive key should be invalid."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=[],
        )
        api_key.is_active = False

        assert api_key.is_valid() is False

    def test_is_valid_expired(self):
        """Expired key should be invalid."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=[],
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        api_key.is_active = True

        assert api_key.is_valid() is False

    def test_is_valid_future_expiry(self):
        """Key with future expiry should be valid."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=[],
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        api_key.is_active = True

        assert api_key.is_valid() is True


class TestAPIKeyPermissions:
    """Test APIKey.has_permission method."""

    def test_has_permission_exact_match(self):
        """Exact permission match should return True."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=["customers:read"],
        )

        assert api_key.has_permission("customers", "read") is True

    def test_has_permission_no_match(self):
        """Non-matching permission should return False."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=["customers:read"],
        )

        assert api_key.has_permission("orders", "read") is False

    def test_has_permission_resource_wildcard(self):
        """Resource wildcard should match any action."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=["customers:*"],
        )

        assert api_key.has_permission("customers", "read") is True
        assert api_key.has_permission("customers", "write") is True
        assert api_key.has_permission("orders", "read") is False

    def test_has_permission_global_wildcard(self):
        """Global wildcard should match everything."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=["*:*"],
        )

        assert api_key.has_permission("customers", "read") is True
        assert api_key.has_permission("orders", "write") is True
        assert api_key.has_permission("admin", "delete") is True

    def test_has_permission_empty_permissions(self):
        """Empty permissions should deny everything."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=[],
        )

        assert api_key.has_permission("customers", "read") is False

    def test_has_permission_none_permissions(self):
        """None permissions should deny everything."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=[],
        )
        api_key.permissions = None

        assert api_key.has_permission("customers", "read") is False


class TestAPIKeyUsageTracking:
    """Test APIKey.record_use method."""

    def test_record_use_updates_last_used(self):
        """record_use should update last_used_at."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=[],
        )
        # Initialize use_count (SQLAlchemy only applies defaults on DB insert)
        api_key.use_count = 0

        assert api_key.last_used_at is None

        api_key.record_use()

        assert api_key.last_used_at is not None
        assert isinstance(api_key.last_used_at, datetime)

    def test_record_use_increments_count(self):
        """record_use should increment use_count."""
        api_key, _ = APIKey.create_key(
            tenant_id=1,
            name="Test",
            permissions=[],
        )
        # Initialize use_count (SQLAlchemy only applies defaults on DB insert)
        api_key.use_count = 0

        assert api_key.use_count == 0

        api_key.record_use()
        assert api_key.use_count == 1

        api_key.record_use()
        assert api_key.use_count == 2
