"""
Unit tests for authentication middleware.

Tests API key validation, JWT handling, and permission checking.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from fastapi import HTTPException

from api.middleware.auth import (
    APIKeyInfo,
    ExpiredKeyError,
    _check_db_key,
    _verify_jwt_token,
    require_permission,
)
from api.models import APIKey, Tenant


class TestAPIKeyInfo:
    """Test APIKeyInfo container class."""

    def test_init_with_required_params(self):
        """Create APIKeyInfo with required params."""
        info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test1234",
            tenant_id="42",
            name="Test Key",
            permissions=["customers:read"],
        )

        assert info.key_id == 1
        assert info.key_prefix == "gtb_test1234"
        assert info.tenant_id == "42"
        assert info.name == "Test Key"
        assert info.permissions == ["customers:read"]

    def test_init_with_all_params(self):
        """Create APIKeyInfo with all params."""
        expires = datetime.utcnow() + timedelta(days=30)

        info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test1234",
            tenant_id="42",
            name="Test Key",
            permissions=["customers:read"],
            is_active=True,
            expires_at=expires,
            rate_limit=100,
        )

        assert info.is_active is True
        assert info.expires_at == expires
        assert info.rate_limit == 100


class TestAPIKeyInfoDaysUntilExpiry:
    """Test APIKeyInfo.days_until_expiry method."""

    def test_no_expiration_returns_none(self):
        """Key without expiration should return None."""
        info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test",
            tenant_id="1",
            name="Test",
            permissions=[],
            expires_at=None,
        )

        assert info.days_until_expiry() is None

    def test_future_expiration_returns_days(self):
        """Key with future expiration should return positive days."""
        expires = datetime.utcnow() + timedelta(days=30)
        info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test",
            tenant_id="1",
            name="Test",
            permissions=[],
            expires_at=expires,
        )

        days = info.days_until_expiry()
        assert days is not None
        assert 29 <= days <= 31

    def test_past_expiration_returns_zero(self):
        """Expired key should return 0."""
        expires = datetime.utcnow() - timedelta(days=5)
        info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test",
            tenant_id="1",
            name="Test",
            permissions=[],
            expires_at=expires,
        )

        assert info.days_until_expiry() == 0


class TestAPIKeyInfoHasPermission:
    """Test APIKeyInfo.has_permission method."""

    def test_exact_permission_match(self):
        """Exact permission should match."""
        info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test",
            tenant_id="1",
            name="Test",
            permissions=["customers:read", "orders:read"],
        )

        assert info.has_permission("customers:read") is True
        assert info.has_permission("orders:read") is True
        assert info.has_permission("orders:write") is False

    def test_wildcard_permission(self):
        """Wildcard *:* should match all."""
        info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test",
            tenant_id="1",
            name="Test",
            permissions=["*:*"],
        )

        assert info.has_permission("customers:read") is True
        assert info.has_permission("admin:delete") is True

    def test_resource_wildcard(self):
        """Resource wildcard should match any action."""
        info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test",
            tenant_id="1",
            name="Test",
            permissions=["customers:*"],
        )

        assert info.has_permission("customers:read") is True
        assert info.has_permission("customers:write") is True
        assert info.has_permission("orders:read") is False

    def test_empty_permissions(self):
        """Empty permissions should deny all."""
        info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test",
            tenant_id="1",
            name="Test",
            permissions=[],
        )

        assert info.has_permission("customers:read") is False

    def test_none_permissions(self):
        """None permissions should deny all."""
        info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test",
            tenant_id="1",
            name="Test",
            permissions=None,
        )

        assert info.has_permission("customers:read") is False


class TestCheckDbKey:
    """Test _check_db_key function."""

    def test_non_gtb_prefix_returns_none(self):
        """Key without gtb_ prefix should return None."""
        mock_db = MagicMock()
        result = _check_db_key("xyz_somekey123", mock_db)
        assert result is None

    def test_valid_key_returns_info(self, test_db, test_tenant):
        """Valid key should return APIKeyInfo."""
        # Create a key
        api_key, plaintext = APIKey.create_key(
            tenant_id=test_tenant.id,
            name="Test Key",
            permissions=["customers:read"],
        )
        test_db.add(api_key)
        test_db.commit()

        result = _check_db_key(plaintext, test_db)

        assert result is not None
        assert isinstance(result, APIKeyInfo)
        assert result.key_id == api_key.id
        assert result.permissions == ["customers:read"]

    def test_invalid_key_returns_none(self, test_db, test_tenant):
        """Invalid key should return None."""
        # Create a key but use wrong plaintext
        api_key, _ = APIKey.create_key(
            tenant_id=test_tenant.id,
            name="Test Key",
            permissions=["customers:read"],
        )
        test_db.add(api_key)
        test_db.commit()

        result = _check_db_key("gtb_wrongkey1234567890123456789012", test_db)

        assert result is None

    def test_expired_key_raises(self, test_db, test_tenant):
        """Expired key should raise ExpiredKeyError."""
        api_key, plaintext = APIKey.create_key(
            tenant_id=test_tenant.id,
            name="Expired Key",
            permissions=["customers:read"],
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
        test_db.add(api_key)
        test_db.commit()

        with pytest.raises(ExpiredKeyError, match="has expired"):
            _check_db_key(plaintext, test_db)

    def test_inactive_key_not_found(self, test_db, test_tenant):
        """Inactive key should not be found."""
        api_key, plaintext = APIKey.create_key(
            tenant_id=test_tenant.id,
            name="Inactive Key",
            permissions=["customers:read"],
        )
        api_key.is_active = False
        test_db.add(api_key)
        test_db.commit()

        result = _check_db_key(plaintext, test_db)

        assert result is None

    def test_records_usage(self, test_db, test_tenant):
        """Successful validation should record usage."""
        api_key, plaintext = APIKey.create_key(
            tenant_id=test_tenant.id,
            name="Test Key",
            permissions=["customers:read"],
        )
        test_db.add(api_key)
        test_db.commit()

        assert api_key.use_count == 0
        assert api_key.last_used_at is None

        _check_db_key(plaintext, test_db)

        test_db.refresh(api_key)
        assert api_key.use_count == 1
        assert api_key.last_used_at is not None


class TestVerifyJwtToken:
    """Test JWT token verification."""

    def test_invalid_token_returns_none(self):
        """Invalid JWT should return None."""
        result = _verify_jwt_token("invalid.token.here")
        assert result is None

    def test_expired_token_returns_none(self):
        """Expired JWT should return None."""
        # This would require a valid but expired token
        # For now, just test that invalid tokens are rejected
        result = _verify_jwt_token("")
        assert result is None


class TestRequirePermission:
    """Test require_permission dependency factory."""

    def test_creates_dependency(self):
        """require_permission should return a callable."""
        dependency = require_permission("customers:read")
        assert callable(dependency)

    @pytest.mark.asyncio
    async def test_permission_granted(self):
        """Should not raise when permission is granted."""
        dependency = require_permission("customers:read")

        api_key_info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test",
            tenant_id="1",
            name="Test",
            permissions=["customers:read"],
        )

        # Should not raise
        result = await dependency(api_key=api_key_info)
        assert result is None

    @pytest.mark.asyncio
    async def test_permission_denied(self):
        """Should raise HTTPException when permission denied."""
        dependency = require_permission("admin:delete")

        api_key_info = APIKeyInfo(
            key_id=1,
            key_prefix="gtb_test",
            tenant_id="1",
            name="Test",
            permissions=["customers:read"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await dependency(api_key=api_key_info)

        assert exc_info.value.status_code == 403
        assert "admin:delete required" in exc_info.value.detail
