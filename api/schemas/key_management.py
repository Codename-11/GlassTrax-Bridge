### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Key Management Schemas -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Key Management Schemas

Pydantic models for tenant and API key management endpoints.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ========================================
# Tenant Schemas
# ========================================

class TenantCreate(BaseModel):
    """Create a new tenant"""
    name: str = Field(..., min_length=1, max_length=100, description="Tenant name")
    description: Optional[str] = Field(None, max_length=500, description="Description")
    contact_email: Optional[str] = Field(None, max_length=255, description="Contact email")


class TenantUpdate(BaseModel):
    """Update tenant fields"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    contact_email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    """Tenant response"""
    id: int
    name: str
    description: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    api_key_count: Optional[int] = None

    class Config:
        from_attributes = True


# ========================================
# API Key Schemas
# ========================================

class APIKeyCreate(BaseModel):
    """Create a new API key"""
    tenant_id: int = Field(..., description="ID of the owning tenant")
    name: str = Field(..., min_length=1, max_length=100, description="Key name (e.g., 'Production')")
    description: Optional[str] = Field(None, max_length=500, description="Description")
    permissions: List[str] = Field(
        default=["customers:read"],
        description="List of permissions (e.g., 'customers:read', 'orders:read')"
    )
    rate_limit: int = Field(default=60, ge=1, le=1000, description="Requests per minute")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date")


class APIKeyResponse(BaseModel):
    """API key response (without the actual key)"""
    id: int
    tenant_id: int
    tenant_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    key_prefix: str  # "gtb_xxxx..." for identification
    permissions: List[str]
    rate_limit: int
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    use_count: int

    class Config:
        from_attributes = True


class APIKeyCreatedResponse(BaseModel):
    """
    Response when creating a new API key.

    IMPORTANT: The 'key' field contains the plaintext API key.
    This is the ONLY time the key will be shown - it cannot be retrieved later.
    Store it securely!
    """
    id: int
    tenant_id: int
    name: str
    key_prefix: str
    key: str = Field(..., description="The API key (shown only once - store securely!)")
    permissions: List[str]
    rate_limit: int
    expires_at: Optional[datetime] = None
    created_at: datetime
    message: str = "API key created successfully. Store the key securely - it cannot be retrieved later."


class APIKeyUpdate(BaseModel):
    """Update API key fields (cannot change the key itself)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: Optional[List[str]] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


# ========================================
# Access Log Schemas
# ========================================

class AccessLogResponse(BaseModel):
    """Access log entry response"""
    id: int
    request_id: str
    api_key_id: Optional[int] = None
    tenant_id: Optional[int] = None
    key_prefix: Optional[str] = None
    method: str
    path: str
    query_string: Optional[str] = None
    client_ip: Optional[str] = None
    status_code: int
    response_time_ms: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AccessLogStats(BaseModel):
    """Access log statistics"""
    total_requests: int
    requests_today: int
    avg_response_time_ms: Optional[float] = None
    error_count: int  # 4xx and 5xx responses
    top_endpoints: List[dict]  # [{path: str, count: int}]
