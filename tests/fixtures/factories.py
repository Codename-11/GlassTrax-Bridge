"""
Factory functions for creating test model instances.

These factories create valid model instances with sensible defaults,
making it easy to set up test scenarios.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from api.models import Tenant, APIKey


def create_tenant(
    db: Session,
    name: str = "Test Tenant",
    description: str = "Test tenant for automated testing",
    contact_email: str = "test@example.com",
    is_active: bool = True,
) -> Tenant:
    """
    Create and persist a tenant for testing.

    Args:
        db: Database session
        name: Tenant name (must be unique)
        description: Tenant description
        contact_email: Contact email
        is_active: Whether tenant is active

    Returns:
        Created Tenant instance
    """
    tenant = Tenant(
        name=name,
        description=description,
        contact_email=contact_email,
        is_active=is_active,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def create_api_key(
    db: Session,
    tenant: Tenant,
    name: str = "Test API Key",
    permissions: Optional[list[str]] = None,
    rate_limit: int = 1000,
    expires_at: Optional[datetime] = None,
    is_active: bool = True,
) -> tuple[APIKey, str]:
    """
    Create and persist an API key for testing.

    Args:
        db: Database session
        tenant: Owning tenant
        name: Key name
        permissions: List of permissions (default: customers:read, orders:read)
        rate_limit: Rate limit per minute
        expires_at: Optional expiration datetime
        is_active: Whether key is active

    Returns:
        Tuple of (APIKey instance, plaintext key string)
    """
    if permissions is None:
        permissions = ["customers:read", "orders:read"]

    api_key, plaintext = APIKey.create_key(
        tenant_id=tenant.id,
        name=name,
        permissions=permissions,
        rate_limit=rate_limit,
        expires_at=expires_at,
    )

    if not is_active:
        api_key.is_active = False

    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key, plaintext


def create_admin_api_key(
    db: Session,
    tenant: Tenant,
    name: str = "Admin API Key",
) -> tuple[APIKey, str]:
    """
    Create and persist an admin API key with full permissions.

    Args:
        db: Database session
        tenant: Owning tenant
        name: Key name

    Returns:
        Tuple of (APIKey instance, plaintext key string)
    """
    return create_api_key(
        db=db,
        tenant=tenant,
        name=name,
        permissions=["*:*", "admin:*"],
        rate_limit=10000,
    )


def create_expired_api_key(
    db: Session,
    tenant: Tenant,
    name: str = "Expired API Key",
) -> tuple[APIKey, str]:
    """
    Create and persist an expired API key for testing expiration logic.

    Args:
        db: Database session
        tenant: Owning tenant
        name: Key name

    Returns:
        Tuple of (APIKey instance, plaintext key string)
    """
    return create_api_key(
        db=db,
        tenant=tenant,
        name=name,
        permissions=["customers:read"],
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
