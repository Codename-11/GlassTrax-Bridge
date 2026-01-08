### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - API Key Authentication Middleware -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
API Key Authentication

Provides authentication via API key in request headers.
Keys are validated against the SQLite database with bcrypt hashing.
"""

from datetime import datetime

import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.config import get_api_settings
from api.database import get_db
from api.models import APIKey

settings = get_api_settings()

# API Key header definition
api_key_header = APIKeyHeader(
    name=settings.api_key_header,
    auto_error=False,
    description="API key for authentication",
)

# Bearer token for JWT authentication
bearer_scheme = HTTPBearer(auto_error=False)


def _verify_jwt_token(token: str) -> dict | None:
    """Verify a JWT token and return the payload if valid"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") == "admin":
            return payload
        return None
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None



class APIKeyInfo:
    """Container for validated API key information"""

    def __init__(
        self,
        key_id: int | str | None,
        key_prefix: str,
        tenant_id: str,
        name: str,
        permissions: list,
        is_active: bool = True,
        expires_at: datetime | None = None,
        rate_limit: int = 60,
    ):
        self.key_id = key_id
        self.key_prefix = key_prefix
        self.tenant_id = tenant_id
        self.name = name
        self.permissions = permissions
        self.is_active = is_active
        self.expires_at = expires_at
        self.rate_limit = rate_limit

    def days_until_expiry(self) -> int | None:
        """Returns days until expiry, or None if no expiration"""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    def has_permission(self, permission: str) -> bool:
        """Check if key has a specific permission"""
        if not self.permissions:
            return False

        # Check for wildcard permission
        if "*:*" in self.permissions:
            return True

        # Check for exact permission or resource wildcard
        resource = permission.split(":")[0] if ":" in permission else permission
        return permission in self.permissions or f"{resource}:*" in self.permissions


class ExpiredKeyError(Exception):
    """Raised when an API key has expired"""
    pass


def _check_db_key(api_key: str, db: Session) -> APIKeyInfo | None:
    """Check if this is a valid database key"""
    # Keys start with "gtb_" prefix
    if not api_key.startswith("gtb_"):
        return None

    # Find potential keys by prefix (first 12 chars)
    key_prefix = api_key[:12]
    potential_keys = db.query(APIKey).filter(
        APIKey.key_prefix == key_prefix,
        APIKey.is_active,
    ).all()

    # Verify the full key against each potential match
    for db_key in potential_keys:
        if db_key.verify_key(api_key):
            # Check expiration
            if db_key.expires_at and datetime.utcnow() > db_key.expires_at:
                raise ExpiredKeyError(f"API key '{key_prefix}...' has expired")

            # Record usage
            db_key.record_use()
            db.commit()

            return APIKeyInfo(
                key_id=db_key.id,
                key_prefix=db_key.key_prefix,
                tenant_id=str(db_key.tenant_id),
                name=db_key.name,
                permissions=db_key.permissions or [],
                is_active=db_key.is_active,
                expires_at=db_key.expires_at,
                rate_limit=db_key.rate_limit or 60,
            )

    return None


async def get_api_key(
    request: Request,
    api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> APIKeyInfo:
    """
    Validate API key or JWT token from request header

    Checks in order:
    1. JWT Bearer token (for admin portal)
    2. Database API keys (gtb_* prefix)

    Args:
        request: FastAPI request object (for storing key info)
        api_key: API key from X-API-Key header
        bearer: JWT token from Authorization: Bearer header
        db: Database session

    Returns:
        APIKeyInfo object with key details

    Raises:
        HTTPException: If no valid authentication provided
    """
    # Check JWT Bearer token first (for admin portal after login)
    if bearer and bearer.credentials:
        payload = _verify_jwt_token(bearer.credentials)
        if payload:
            key_info = APIKeyInfo(
                key_id="jwt-admin",
                key_prefix="jwt",
                tenant_id="system",
                name=f"JWT: {payload.get('sub', 'admin')}",
                permissions=["*:*", "admin:*"],
                is_active=True,
            )
            request.state.api_key_info = key_info
            return key_info

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key or Bearer token is required",
            headers={"WWW-Authenticate": "ApiKey, Bearer"},
        )

    # Check database keys
    try:
        key_info = _check_db_key(api_key, db)
        if key_info:
            # Store in request state for access logging
            request.state.api_key_info = key_info
            return key_info
    except ExpiredKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "ApiKey"},
        ) from e

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def require_permission(permission: str):
    """
    Dependency factory for permission checking

    Usage:
        @router.get("/protected")
        async def protected_route(
            api_key: APIKeyInfo = Depends(get_api_key),
            _: None = Depends(require_permission("customers:read"))
        ):
            ...
    """

    async def check_permission(
        api_key: APIKeyInfo = Security(get_api_key),
    ) -> None:
        if not api_key.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required",
            )

    return check_permission


# Convenience dependencies for common permissions
require_customers_read = require_permission("customers:read")
require_customers_write = require_permission("customers:write")
require_orders_read = require_permission("orders:read")
require_orders_write = require_permission("orders:write")
require_admin = require_permission("admin:*")
