### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Key Management Router -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Key Management API Endpoints

Provides endpoints for managing tenants and API keys:
- Tenants: CRUD operations
- API Keys: Create, list, revoke, update permissions

Note: These endpoints require admin API key with 'admin:*' permission.
"""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.middleware import APIKeyInfo, get_api_key, require_admin
from api.models import AccessLog, APIKey, Tenant
from api.schemas.key_management import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyResponse,
    APIKeyUpdate,
    TenantCreate,
    TenantResponse,
    TenantUpdate,
)
from api.schemas.responses import APIResponse, PaginatedResponse, PaginationMeta

router = APIRouter()


# ========================================
# Tenant Endpoints
# ========================================

@router.get(
    "/tenants",
    response_model=PaginatedResponse[TenantResponse],
    summary="List tenants",
    description="List all tenants with pagination",
)
async def list_tenants(
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = Query(False, description="Only show active tenants"),
) -> PaginatedResponse[TenantResponse]:
    """List all tenants"""
    query = db.query(Tenant)
    if active_only:
        query = query.filter(Tenant.is_active)

    total = query.count()
    tenants = query.offset((page - 1) * page_size).limit(page_size).all()

    # Add API key counts
    responses = []
    for tenant in tenants:
        response = TenantResponse.model_validate(tenant)
        response.api_key_count = db.query(APIKey).filter(APIKey.tenant_id == tenant.id).count()
        responses.append(response)

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        success=True,
        data=responses,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.post(
    "/tenants",
    response_model=APIResponse[TenantResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create tenant",
    description="Create a new tenant/organization",
)
async def create_tenant(
    data: TenantCreate,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[TenantResponse]:
    """Create a new tenant"""
    # Check if tenant name already exists
    existing = db.query(Tenant).filter(Tenant.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with name '{data.name}' already exists",
        )

    tenant = Tenant(
        name=data.name,
        description=data.description,
        contact_email=data.contact_email,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    response = TenantResponse.model_validate(tenant)
    response.api_key_count = 0

    return APIResponse(success=True, data=response, message="Tenant created successfully")


@router.get(
    "/tenants/{tenant_id}",
    response_model=APIResponse[TenantResponse],
    summary="Get tenant",
    description="Get tenant details by ID",
)
async def get_tenant(
    tenant_id: int,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[TenantResponse]:
    """Get tenant by ID"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )

    response = TenantResponse.model_validate(tenant)
    response.api_key_count = db.query(APIKey).filter(APIKey.tenant_id == tenant.id).count()

    return APIResponse(success=True, data=response)


@router.patch(
    "/tenants/{tenant_id}",
    response_model=APIResponse[TenantResponse],
    summary="Update tenant",
    description="Update tenant details",
)
async def update_tenant(
    tenant_id: int,
    data: TenantUpdate,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[TenantResponse]:
    """Update tenant"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    db.commit()
    db.refresh(tenant)

    response = TenantResponse.model_validate(tenant)
    response.api_key_count = db.query(APIKey).filter(APIKey.tenant_id == tenant.id).count()

    return APIResponse(success=True, data=response, message="Tenant updated successfully")


@router.delete(
    "/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant",
    description="Delete a tenant and all associated API keys",
)
async def delete_tenant(
    tenant_id: int,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete tenant (cascades to API keys)"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )

    # Protect System tenant from deletion
    if tenant.name == "System":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the System tenant",
        )

    db.delete(tenant)
    db.commit()


# ========================================
# API Key Endpoints
# ========================================

@router.get(
    "/api-keys",
    response_model=PaginatedResponse[APIKeyResponse],
    summary="List API keys",
    description="List all API keys with pagination",
)
async def list_api_keys(
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: int | None = Query(None, description="Filter by tenant"),
    active_only: bool = Query(False, description="Only show active keys"),
) -> PaginatedResponse[APIKeyResponse]:
    """List all API keys"""
    query = db.query(APIKey)

    if tenant_id:
        query = query.filter(APIKey.tenant_id == tenant_id)
    if active_only:
        query = query.filter(APIKey.is_active)

    total = query.count()
    keys = query.offset((page - 1) * page_size).limit(page_size).all()

    # Add tenant names
    responses = []
    for key in keys:
        response = APIKeyResponse.model_validate(key)
        if key.tenant:
            response.tenant_name = key.tenant.name
        responses.append(response)

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        success=True,
        data=responses,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


@router.post(
    "/api-keys",
    response_model=APIResponse[APIKeyCreatedResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="Create a new API key. The key will only be shown once!",
)
async def create_api_key(
    data: APIKeyCreate,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[APIKeyCreatedResponse]:
    """
    Create a new API key.

    **IMPORTANT**: The returned `key` value is the only time the full API key
    will be shown. Store it securely - it cannot be retrieved later!
    """
    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == data.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {data.tenant_id} not found",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant {data.tenant_id} is not active",
        )

    # Create the key
    new_key, plaintext_key = APIKey.create_key(
        tenant_id=data.tenant_id,
        name=data.name,
        description=data.description,
        permissions=data.permissions,
        rate_limit=data.rate_limit,
        expires_at=data.expires_at,
    )

    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    return APIResponse(
        success=True,
        data=APIKeyCreatedResponse(
            id=new_key.id,
            tenant_id=new_key.tenant_id,
            name=new_key.name,
            key_prefix=new_key.key_prefix,
            key=plaintext_key,  # Only shown once!
            permissions=new_key.permissions,
            rate_limit=new_key.rate_limit,
            expires_at=new_key.expires_at,
            created_at=new_key.created_at,
        ),
        message="API key created successfully. Store the key securely - it cannot be retrieved later!",
    )


@router.get(
    "/api-keys/{key_id}",
    response_model=APIResponse[APIKeyResponse],
    summary="Get API key",
    description="Get API key details by ID (key value is not returned)",
)
async def get_api_key_by_id(
    key_id: int,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[APIKeyResponse]:
    """Get API key by ID"""
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found",
        )

    response = APIKeyResponse.model_validate(key)
    if key.tenant:
        response.tenant_name = key.tenant.name

    return APIResponse(success=True, data=response)


@router.patch(
    "/api-keys/{key_id}",
    response_model=APIResponse[APIKeyResponse],
    summary="Update API key",
    description="Update API key details (cannot change the key value)",
)
async def update_api_key(
    key_id: int,
    data: APIKeyUpdate,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[APIKeyResponse]:
    """Update API key"""
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(key, field, value)

    db.commit()
    db.refresh(key)

    response = APIKeyResponse.model_validate(key)
    if key.tenant:
        response.tenant_name = key.tenant.name

    return APIResponse(success=True, data=response, message="API key updated successfully")


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke API key",
    description="Revoke (delete) an API key",
)
async def revoke_api_key(
    key_id: int,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Revoke (delete) an API key"""
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found",
        )

    db.delete(key)
    db.commit()


@router.post(
    "/api-keys/{key_id}/deactivate",
    response_model=APIResponse[APIKeyResponse],
    summary="Deactivate API key",
    description="Deactivate an API key without deleting it",
)
async def deactivate_api_key(
    key_id: int,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[APIKeyResponse]:
    """Deactivate an API key"""
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found",
        )

    key.is_active = False
    db.commit()
    db.refresh(key)

    response = APIKeyResponse.model_validate(key)
    if key.tenant:
        response.tenant_name = key.tenant.name

    return APIResponse(success=True, data=response, message="API key deactivated")


@router.post(
    "/api-keys/{key_id}/activate",
    response_model=APIResponse[APIKeyResponse],
    summary="Activate API key",
    description="Re-activate a deactivated API key",
)
async def activate_api_key(
    key_id: int,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[APIKeyResponse]:
    """Activate an API key"""
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found",
        )

    key.is_active = True
    db.commit()
    db.refresh(key)

    response = APIKeyResponse.model_validate(key)
    if key.tenant:
        response.tenant_name = key.tenant.name

    return APIResponse(success=True, data=response, message="API key activated")


# ========================================
# Access Log Endpoints
# ========================================

import os
import subprocess
import sys
import threading
from datetime import datetime as dt
from datetime import timedelta

import jwt

# pyodbc is optional (not available in Docker)
try:
    import pyodbc
    HAS_PYODBC = True
except ImportError:
    pyodbc = None
    HAS_PYODBC = False

from api.config import get_admin_settings, get_api_settings


class AccessLogResponse(BaseModel):
    """Access log entry response"""
    id: int
    request_id: str
    api_key_id: int | None = None
    tenant_id: int | None = None
    key_prefix: str | None = None
    method: str
    path: str
    query_string: str | None = None
    client_ip: str | None = None
    status_code: int
    response_time_ms: float | None = None
    created_at: dt

    class Config:
        from_attributes = True


@router.get(
    "/access-logs",
    response_model=PaginatedResponse[AccessLogResponse],
    summary="List access logs",
    description="List API access logs with pagination",
)
async def list_access_logs(
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tenant_id: int | None = Query(None, description="Filter by tenant"),
    api_key_id: int | None = Query(None, description="Filter by API key"),
    limit: int | None = Query(None, description="Limit total results"),
    exclude_admin: bool = Query(False, description="Exclude admin/portal requests from results"),
) -> PaginatedResponse[AccessLogResponse]:
    """List access logs"""
    query = db.query(AccessLog).order_by(AccessLog.created_at.desc())

    if tenant_id:
        query = query.filter(AccessLog.tenant_id == tenant_id)
    if api_key_id:
        query = query.filter(AccessLog.api_key_id == api_key_id)
    if exclude_admin:
        # Exclude admin portal requests and health checks from stats
        query = query.filter(~AccessLog.path.startswith("/api/v1/admin"))
        query = query.filter(AccessLog.path != "/health")

    total = query.count()

    # Apply limit if specified (but keep total as actual count for pagination info)
    if limit:
        logs = query.limit(limit).all()
    else:
        logs = query.offset((page - 1) * page_size).limit(page_size).all()

    responses = [AccessLogResponse.model_validate(log) for log in logs]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        success=True,
        data=responses,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        ),
    )


# ========================================
# Diagnostics Endpoint
# ========================================

class DiagnosticCheck(BaseModel):
    """Individual diagnostic check result"""
    name: str
    status: str  # 'pass', 'fail', 'warning'
    message: str
    details: dict | None = None


class DiagnosticsResponse(BaseModel):
    """Full diagnostics response"""
    overall_status: str  # 'healthy', 'degraded', 'unhealthy'
    checks: list[DiagnosticCheck]
    system_info: dict


@router.get(
    "/diagnostics",
    response_model=APIResponse[DiagnosticsResponse],
    summary="System diagnostics",
    description="Run system diagnostics including driver checks and database connectivity tests",
)
async def get_diagnostics(
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[DiagnosticsResponse]:
    """Run system diagnostics"""
    checks: list[DiagnosticCheck] = []

    # 1. Check Python version and architecture
    python_info = {
        "version": sys.version,
        "architecture": "64-bit" if sys.maxsize > 2**32 else "32-bit",
        "executable": sys.executable,
    }
    checks.append(DiagnosticCheck(
        name="Python Environment",
        status="pass",
        message=f"Python {sys.version_info.major}.{sys.version_info.minor} ({python_info['architecture']})",
        details=python_info,
    ))

    # 2. Check ODBC drivers (only if pyodbc available)
    if HAS_PYODBC:
        try:
            drivers = pyodbc.drivers()
            pervasive_drivers = [d for d in drivers if "pervasive" in d.lower() or "actian" in d.lower()]

            if pervasive_drivers:
                checks.append(DiagnosticCheck(
                    name="Pervasive ODBC Driver",
                    status="pass",
                    message=f"Found {len(pervasive_drivers)} Pervasive/Actian driver(s)",
                    details={"drivers": pervasive_drivers, "all_drivers": drivers},
                ))
            else:
                checks.append(DiagnosticCheck(
                    name="Pervasive ODBC Driver",
                    status="fail",
                    message="No Pervasive/Actian ODBC driver found",
                    details={"available_drivers": drivers},
                ))
        except Exception as e:
            checks.append(DiagnosticCheck(
                name="Pervasive ODBC Driver",
                status="fail",
                message=f"Error checking drivers: {e!s}",
            ))
    else:
        checks.append(DiagnosticCheck(
            name="Pervasive ODBC Driver",
            status="warning",
            message="pyodbc not available (agent mode)",
            details={"note": "ODBC access is via agent in this deployment"},
        ))

    # 3. Check GlassTrax database connection
    try:
        from api.dependencies import get_glasstrax_service
        service = next(get_glasstrax_service())
        connected = await service.test_connection()

        if connected:
            checks.append(DiagnosticCheck(
                name="GlassTrax Database",
                status="pass",
                message="Successfully connected to GlassTrax database",
                details={"dsn": service.dsn if hasattr(service, 'dsn') else "configured"},
            ))
        else:
            checks.append(DiagnosticCheck(
                name="GlassTrax Database",
                status="fail",
                message="Failed to connect to GlassTrax database",
            ))
    except Exception as e:
        checks.append(DiagnosticCheck(
            name="GlassTrax Database",
            status="fail",
            message=f"Connection error: {e!s}",
        ))

    # 4. Check app database (SQLite)
    try:
        from sqlalchemy import text
        result = db.execute(text("SELECT COUNT(*) FROM tenants")).scalar()
        from api.database import DATABASE_PATH

        checks.append(DiagnosticCheck(
            name="App Database (SQLite)",
            status="pass",
            message=f"Connected successfully. {result} tenant(s) in database.",
            details={"path": str(DATABASE_PATH), "tenant_count": result},
        ))
    except Exception as e:
        checks.append(DiagnosticCheck(
            name="App Database (SQLite)",
            status="fail",
            message=f"Database error: {e!s}",
        ))

    # 5. Check config file
    try:
        from api.config import load_yaml_config
        config = load_yaml_config()
        has_db_config = bool(config.get("database") if config else False)
        config_status = "pass" if has_db_config else "warning"
        config_message = "Configuration loaded successfully" if has_db_config else "Using default configuration"

        checks.append(DiagnosticCheck(
            name="Configuration",
            status=config_status,
            message=config_message,
            details={"has_database_config": has_db_config},
        ))
    except Exception as e:
        checks.append(DiagnosticCheck(
            name="Configuration",
            status="warning",
            message=f"Config check: {e!s}",
        ))

    # 6. Test API endpoint (customers)
    try:
        import time as time_module

        from api.dependencies import get_glasstrax_service
        service = next(get_glasstrax_service())

        start = time_module.time()
        customers, _total = await service.get_customers(page=1, page_size=1)
        elapsed = (time_module.time() - start) * 1000

        if customers and len(customers) > 0:
            checks.append(DiagnosticCheck(
                name="API Endpoint Test (Customers)",
                status="pass",
                message=f"Successfully retrieved customer data ({elapsed:.0f}ms)",
                details={"response_time_ms": round(elapsed, 2), "sample_count": len(customers)},
            ))
        else:
            checks.append(DiagnosticCheck(
                name="API Endpoint Test (Customers)",
                status="warning",
                message="Query successful but no customers found",
                details={"response_time_ms": round(elapsed, 2)},
            ))
    except Exception as e:
        checks.append(DiagnosticCheck(
            name="API Endpoint Test (Customers)",
            status="fail",
            message=f"Failed to query customers: {e!s}",
        ))

    # Determine overall status
    statuses = [c.status for c in checks]
    if all(s == "pass" for s in statuses):
        overall = "healthy"
    elif "fail" in statuses:
        overall = "unhealthy"
    else:
        overall = "degraded"

    # System info
    settings = get_api_settings()
    from api.config import get_db_settings
    db_settings = get_db_settings()

    # Check if GlassTrax is connected
    glasstrax_connected = False
    for check in checks:
        if check.name == "GlassTrax Database" and check.status == "pass":
            glasstrax_connected = True
            break

    system_info = {
        "platform": sys.platform,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "architecture": python_info["architecture"],
        "timezone": settings.timezone,
        "database_name": db_settings.friendly_name,
        "database_connected": glasstrax_connected,
        "cwd": os.getcwd(),
    }

    return APIResponse(
        success=True,
        data=DiagnosticsResponse(
            overall_status=overall,
            checks=checks,
            system_info=system_info,
        ),
    )


# ========================================
# Speed Test / Latency Diagnostics
# ========================================


class SpeedTestResult(BaseModel):
    """Speed test result with timing breakdown"""

    timestamp: str
    total_ms: float
    health_check_ms: float
    simple_query_ms: float | None = None
    simple_query_error: str | None = None
    mode: str  # 'direct' or 'agent'
    database_name: str
    glasstrax_connected: bool


@router.post(
    "/diagnostics/speedtest",
    response_model=APIResponse[SpeedTestResult],
    summary="Speed test",
    description="Run a speed test measuring latency to GlassTrax database",
)
async def run_speedtest(
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[SpeedTestResult]:
    """
    Run a speed test to measure database query latency.

    Measures:
    - Health check time (Bridge internal)
    - Simple query time (SELECT TOP 1 FROM customer)
    """
    import time as time_module
    from datetime import datetime, timezone

    from api.config import get_db_settings, load_yaml_config
    from api.dependencies import get_glasstrax_service

    # Get mode info
    yaml_config = load_yaml_config()
    agent_config = yaml_config.get("agent", {}) if yaml_config else {}
    agent_enabled = agent_config.get("enabled", False)
    mode = "agent" if agent_enabled else "direct"

    db_settings = get_db_settings()
    total_start = time_module.time()

    # 1. Health check (internal connectivity test)
    health_start = time_module.time()
    service = next(get_glasstrax_service())
    glasstrax_connected = await service.test_connection()
    health_ms = (time_module.time() - health_start) * 1000

    # 2. Simple query (actual database round-trip)
    simple_query_ms = None
    simple_query_error = None
    if glasstrax_connected:
        try:
            query_start = time_module.time()
            # Fetch just 1 customer record to measure query latency
            _customers, _total = await service.get_customers(page=1, page_size=1)
            simple_query_ms = (time_module.time() - query_start) * 1000
        except Exception as e:
            simple_query_error = str(e)

    total_ms = (time_module.time() - total_start) * 1000

    return APIResponse(
        success=True,
        message="Speed test completed",
        data=SpeedTestResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_ms=round(total_ms, 2),
            health_check_ms=round(health_ms, 2),
            simple_query_ms=round(simple_query_ms, 2) if simple_query_ms else None,
            simple_query_error=simple_query_error,
            mode=mode,
            database_name=db_settings.friendly_name,
            glasstrax_connected=glasstrax_connected,
        ),
    )


# ========================================
# Admin Authentication Endpoints
# ========================================

class LoginRequest(BaseModel):
    """Login request body"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response with JWT token"""
    token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    is_default_password: bool = False


class TokenValidateResponse(BaseModel):
    """Token validation response"""
    valid: bool
    username: str | None = None
    expires_at: str | None = None


@router.post(
    "/login",
    response_model=APIResponse[LoginResponse],
    summary="Admin login",
    description="Authenticate with username/password or API key to get a JWT token",
)
async def admin_login(
    data: LoginRequest,
    db: Session = Depends(get_db),
) -> APIResponse[LoginResponse]:
    """
    Authenticate admin user and return JWT token.

    Supports three authentication methods:
    1. Username/password from config.yaml
    2. Bootstrap API key (only works before real admin keys are created)
    3. Database API key with admin permissions
    """
    settings = get_api_settings()
    admin = get_admin_settings()

    authenticated = False
    is_default = False

    # Method 1: Check username/password from config
    if data.username == admin.username and admin.verify_password(data.password):
        authenticated = True
        is_default = admin.is_default_password

    # Method 2: Check if password is a bootstrap key (only if no real admin keys exist)
    if not authenticated:
        from api.middleware.auth import BOOTSTRAP_API_KEYS, _has_real_admin_keys
        key_data = BOOTSTRAP_API_KEYS.get(data.password)
        if key_data and key_data.get("is_active"):
            # Bootstrap keys only work if no real admin keys exist
            if not _has_real_admin_keys(db):
                if "admin:*" in key_data.get("permissions", []) or "*:*" in key_data.get("permissions", []):
                    authenticated = True

    # Method 3: Check if password is a database API key with admin permissions
    if not authenticated and data.password.startswith("gtb_"):
        from api.middleware.auth import _check_db_key
        try:
            key_info = _check_db_key(data.password, db)
            if key_info and key_info.has_permission("admin:*"):
                authenticated = True
        except Exception:
            pass

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Generate JWT token
    expires_delta = timedelta(hours=24)
    expire = dt.utcnow() + expires_delta

    token_data = {
        "sub": admin.username,
        "exp": expire,
        "type": "admin",
    }

    token = jwt.encode(token_data, settings.secret_key, algorithm="HS256")

    return APIResponse(
        success=True,
        data=LoginResponse(
            token=token,
            expires_in=int(expires_delta.total_seconds()),
            is_default_password=is_default,
        ),
        message="Login successful" + (" - please change default password!" if is_default else ""),
    )


@router.post(
    "/validate-token",
    response_model=APIResponse[TokenValidateResponse],
    summary="Validate JWT token",
    description="Check if a JWT token is valid",
)
async def validate_token(
    authorization: str | None = None,
) -> APIResponse[TokenValidateResponse]:
    """Validate a JWT token"""
    get_api_settings()

    # Get token from Authorization header
    # This is a simple endpoint - token comes in request body or we check header

    return APIResponse(
        success=True,
        data=TokenValidateResponse(valid=False),
        message="Use Authorization header with Bearer token",
    )


# ========================================
# Database Management Endpoints
# ========================================

class DatabaseResetRequest(BaseModel):
    """Request for database reset - requires confirmation phrase"""
    confirmation: str  # Must be "RESET DATABASE" to proceed


class DatabaseResetResponse(BaseModel):
    """Response after database reset"""
    tables_cleared: list[str]
    message: str


@router.post(
    "/reset-database",
    response_model=APIResponse[DatabaseResetResponse],
    summary="Reset application database",
    description="⚠️ DANGER: Completely resets the application database. Deletes all API keys, tenants, and access logs. A new admin key will be generated on next startup.",
)
async def reset_database(
    data: DatabaseResetRequest,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIResponse[DatabaseResetResponse]:
    """
    Reset the application database.

    ⚠️ DANGER: This action is IRREVERSIBLE!

    This will:
    - Delete ALL API keys
    - Delete ALL tenants/applications
    - Delete ALL access logs
    - On next startup, a new admin key will be auto-generated

    Requires typing "RESET DATABASE" to confirm.
    """
    # Verify confirmation phrase
    if data.confirmation != "RESET DATABASE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation. Type 'RESET DATABASE' to confirm.",
        )

    tables_cleared = []

    try:
        # Delete in order to respect foreign key constraints
        # 1. Access logs first (references API keys)
        log_count = db.query(AccessLog).delete()
        tables_cleared.append(f"access_logs ({log_count} records)")

        # 2. API keys (references tenants)
        key_count = db.query(APIKey).delete()
        tables_cleared.append(f"api_keys ({key_count} records)")

        # 3. Tenants
        tenant_count = db.query(Tenant).delete()
        tables_cleared.append(f"tenants ({tenant_count} records)")

        db.commit()

        return APIResponse(
            success=True,
            data=DatabaseResetResponse(
                tables_cleared=tables_cleared,
                message="Database reset complete. Restart the server to generate a new admin key.",
            ),
            message="⚠️ Database has been reset. Please restart the API server.",
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset database: {e!s}",
        )


# ========================================
# Server Management Endpoints
# ========================================

class ServerRestartResponse(BaseModel):
    """Response for server restart request"""
    message: str
    restart_in_seconds: int


def _restart_server():
    """Background function to restart the server"""
    import time

    # Wait for response to be sent
    time.sleep(2)

    # Get current Python executable and working directory
    python_exe = sys.executable
    cwd = os.getcwd()

    # Start new server process (detached)
    if sys.platform == "win32":
        # Windows: Use 'start' command to spawn a truly independent process
        # This creates a new console window that survives the parent process
        cmd = f'start "GlassTrax API" /D "{cwd}" "{python_exe}" -m uvicorn api.main:app --host 127.0.0.1 --port 8000'
        subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        # Unix: Start in background with nohup
        restart_cmd = [
            python_exe, "-m", "uvicorn",
            "api.main:app",
            "--host", "127.0.0.1",
            "--port", "8000"
        ]
        subprocess.Popen(
            restart_cmd,
            cwd=cwd,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # Give the new process time to start
    time.sleep(1)

    # Exit current process
    os._exit(0)


@router.post(
    "/restart-server",
    response_model=APIResponse[ServerRestartResponse],
    summary="Restart API server",
    description="Restart the API server. The server will restart after a brief delay.",
)
async def restart_server(
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[ServerRestartResponse]:
    """
    Restart the API server.

    The server will:
    1. Return this response immediately
    2. Wait ~2 seconds for any pending requests
    3. Spawn a new server process
    4. Shut down gracefully

    Note: There may be a brief period (~1-2 seconds) where the server is unavailable.
    """
    # Start restart in background thread
    restart_thread = threading.Thread(target=_restart_server, daemon=False)
    restart_thread.start()

    return APIResponse(
        success=True,
        data=ServerRestartResponse(
            message="Server restart initiated. The server will restart in ~2 seconds.",
            restart_in_seconds=2,
        ),
        message="Server is restarting...",
    )


# ========================================
# System Information Endpoints
# ========================================

class DSNInfo(BaseModel):
    """Information about an ODBC Data Source"""
    name: str
    driver: str
    is_pervasive: bool


class DSNsResponse(BaseModel):
    """Available ODBC Data Sources response"""
    dsns: list[DSNInfo]
    pervasive_dsns: list[str]
    architecture: str


@router.get(
    "/dsns",
    response_model=APIResponse[DSNsResponse],
    summary="List ODBC Data Sources",
    description="Get list of available ODBC Data Source Names (DSNs) on the system",
)
async def list_dsns(
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[DSNsResponse]:
    """
    List available ODBC Data Source Names on the system.

    Returns DSNs visible to the current Python architecture (32-bit).
    Only 32-bit ODBC DSNs are shown because GlassTrax Bridge uses
    32-bit Python for Pervasive ODBC compatibility.

    Pervasive/Actian DSNs are highlighted for easy identification.

    Note: In agent mode (Docker), pyodbc is not available and this
    endpoint returns an empty list.
    """
    # pyodbc not available in agent mode (Docker)
    if not HAS_PYODBC:
        return APIResponse(
            success=True,
            data=DSNsResponse(
                dsns=[],
                pervasive_dsns=[],
                architecture="64-bit (agent mode)",
            ),
            message="DSN listing not available in agent mode",
        )

    try:
        # Get all data sources - returns dict of {dsn_name: driver_name}
        data_sources = pyodbc.dataSources()

        dsns = []
        pervasive_dsns = []

        for dsn_name, driver_name in data_sources.items():
            is_pervasive = (
                "pervasive" in driver_name.lower() or
                "actian" in driver_name.lower()
            )

            dsns.append(DSNInfo(
                name=dsn_name,
                driver=driver_name,
                is_pervasive=is_pervasive,
            ))

            if is_pervasive:
                pervasive_dsns.append(dsn_name)

        # Sort: Pervasive DSNs first, then alphabetically
        dsns.sort(key=lambda x: (not x.is_pervasive, x.name.lower()))

        # Determine architecture
        architecture = "32-bit" if sys.maxsize <= 2**32 else "64-bit"

        return APIResponse(
            success=True,
            data=DSNsResponse(
                dsns=dsns,
                pervasive_dsns=pervasive_dsns,
                architecture=architecture,
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list DSNs: {e!s}",
        )


class TestDSNRequest(BaseModel):
    """Request to test a DSN connection"""
    dsn: str
    readonly: bool = True


class TestDSNResponse(BaseModel):
    """Response from DSN connection test"""
    success: bool
    dsn: str
    message: str
    tables_found: int | None = None
    sample_tables: list[str] | None = None


@router.post(
    "/test-dsn",
    response_model=APIResponse[TestDSNResponse],
    summary="Test DSN connection",
    description="Test connection to an ODBC Data Source and verify GlassTrax data is accessible",
)
async def test_dsn(
    data: TestDSNRequest,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[TestDSNResponse]:
    """
    Test a DSN connection before saving to config.

    Attempts to connect to the specified DSN and queries for tables
    to verify the connection works and GlassTrax data is accessible.

    Note: Not available in agent mode (Docker).
    """
    if not HAS_PYODBC:
        return APIResponse(
            success=True,
            data=TestDSNResponse(
                success=False,
                dsn=data.dsn,
                message="DSN testing not available in agent mode. Use 'Test Agent Connection' instead.",
            ),
        )

    try:
        # Build connection string
        readonly_str = "Yes" if data.readonly else "No"
        conn_str = f"DSN={data.dsn};ReadOnly={readonly_str}"

        # Attempt connection with timeout
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()

        # Try to get table list
        tables = []
        try:
            for row in cursor.tables(tableType='TABLE'):
                tables.append(row.table_name)
        except Exception:
            # Some drivers don't support tables() - that's ok
            pass

        cursor.close()
        conn.close()

        # Check for expected GlassTrax tables
        glasstrax_tables = [t for t in tables if t.upper() in [
            'CUSTOMER', 'ORDERS', 'ORDERDET', 'INVENTRY', 'VENDOR'
        ]]

        if glasstrax_tables:
            message = "Connected successfully! Found GlassTrax tables."
        elif tables:
            message = f"Connected successfully! Found {len(tables)} tables (may not be GlassTrax)."
        else:
            message = "Connected successfully! Could not enumerate tables."

        return APIResponse(
            success=True,
            data=TestDSNResponse(
                success=True,
                dsn=data.dsn,
                message=message,
                tables_found=len(tables) if tables else None,
                sample_tables=tables[:10] if tables else None,
            ),
        )

    except pyodbc.Error as e:
        error_msg = str(e)
        # Extract the more readable part of ODBC errors
        if '[' in error_msg and ']' in error_msg:
            # Try to get the last bracketed message which is usually most relevant
            parts = error_msg.split(']')
            if len(parts) > 1:
                error_msg = parts[-1].strip() or parts[-2].strip('[ ')

        return APIResponse(
            success=True,  # API call succeeded, but DSN test failed
            data=TestDSNResponse(
                success=False,
                dsn=data.dsn,
                message=f"Connection failed: {error_msg}",
            ),
        )
    except Exception as e:
        return APIResponse(
            success=True,
            data=TestDSNResponse(
                success=False,
                dsn=data.dsn,
                message=f"Connection failed: {e!s}",
            ),
        )


# ========================================
# Agent Connection Test Endpoint
# ========================================

class TestAgentRequest(BaseModel):
    """Request to test agent connection"""
    url: str
    api_key: str
    timeout: int = 30


class TestAgentResponse(BaseModel):
    """Response from agent connection test"""
    connected: bool
    url: str
    message: str
    agent_version: str | None = None
    database_connected: bool | None = None
    authenticated: bool | None = None  # True if API key is valid


@router.post(
    "/test-agent",
    response_model=APIResponse[TestAgentResponse],
    summary="Test agent connection",
    description="Test connection to a GlassTrax API Agent to verify it's reachable and authenticated",
)
async def test_agent(
    data: TestAgentRequest,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[TestAgentResponse]:
    """
    Test connection to a GlassTrax API Agent.

    Attempts to connect to the specified agent URL and verify:
    - Agent is reachable (via /health endpoint - no auth required)
    - API key is valid (via authenticated query)
    - Agent can connect to GlassTrax database
    """
    from api.services.agent_client import (
        AgentAuthError,
        AgentClient,
        AgentConnectionError,
        AgentQueryError,
    )
    from api.services.agent_schemas import QueryRequest

    try:
        # Create temporary client for testing
        client = AgentClient(url=data.url, api_key=data.api_key, timeout=data.timeout)

        try:
            # Step 1: Test health endpoint (no auth required)
            health = await client.health_check()

            agent_version = health.get("version", "unknown")
            database_connected = health.get("database_connected", False)
            status = health.get("status", "unknown")

            # Step 2: Test authentication by making an actual query
            # The /health endpoint doesn't require auth, so we need to test /query
            authenticated = False
            auth_message = ""

            try:
                # Simple count query to verify auth works
                test_query = QueryRequest(
                    table="customer",
                    columns=["COUNT(*)"],
                    limit=1,
                )
                result = await client.query(test_query)
                if result.success:
                    authenticated = True
                    auth_message = "API key verified."
                else:
                    auth_message = f"Query failed: {result.error or 'unknown error'}"
            except AgentAuthError:
                authenticated = False
                auth_message = "API key is invalid."
            except AgentQueryError as e:
                # Query error but auth worked
                authenticated = True
                auth_message = f"Authenticated, but query error: {e!s}"
            except Exception as e:
                auth_message = f"Auth test error: {e!s}"

            # Build final message
            if status == "healthy" and authenticated:
                message = f"Connected and authenticated! Agent is healthy. {auth_message}"
            elif status == "healthy" and not authenticated:
                message = f"Agent reachable but authentication failed. {auth_message}"
            elif database_connected:
                message = f"Connected to agent (status: {status}), database accessible. {auth_message}"
            else:
                message = f"Connected to agent (status: {status}), database not accessible. {auth_message}"

            return APIResponse(
                success=True,
                data=TestAgentResponse(
                    connected=True,
                    url=data.url,
                    message=message,
                    agent_version=agent_version,
                    database_connected=database_connected,
                    authenticated=authenticated,
                ),
            )

        finally:
            await client.close()

    except AgentAuthError as e:
        return APIResponse(
            success=True,  # API call succeeded, but agent test failed
            data=TestAgentResponse(
                connected=False,
                url=data.url,
                message=f"Authentication failed: {e!s}",
                authenticated=False,
            ),
        )
    except AgentConnectionError as e:
        return APIResponse(
            success=True,
            data=TestAgentResponse(
                connected=False,
                url=data.url,
                message=f"Connection failed: {e!s}",
            ),
        )
    except Exception as e:
        return APIResponse(
            success=True,
            data=TestAgentResponse(
                connected=False,
                url=data.url,
                message=f"Unexpected error: {e!s}",
            ),
        )


# ========================================
# Password Management Endpoints
# ========================================

class ChangePasswordRequest(BaseModel):
    """Request to change admin password"""
    current_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    """Response after password change"""
    message: str


@router.post(
    "/change-password",
    response_model=APIResponse[ChangePasswordResponse],
    summary="Change admin password",
    description="Change the admin portal password",
)
async def change_password(
    data: ChangePasswordRequest,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[ChangePasswordResponse]:
    """
    Change the admin password.

    Requires the current password for verification.
    The new password will be hashed and saved to config.yaml.
    """
    from api.config import get_admin_settings, hash_password
    from api.services.config_service import get_config_service

    # Verify current password
    admin = get_admin_settings()
    if not admin.verify_password(data.current_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Validate new password
    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters",
        )

    try:
        # Hash new password
        new_hash = hash_password(data.new_password)

        # Update config file
        config_service = get_config_service()
        config_service.reload()
        config_service.set("admin.password_hash", new_hash)
        config_service.save()

        return APIResponse(
            success=True,
            data=ChangePasswordResponse(
                message="Password changed successfully",
            ),
            message="Password changed successfully. You may need to log in again.",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {e!s}",
        )


# ========================================
# Configuration Management Endpoints
# ========================================

class ConfigResponse(BaseModel):
    """Configuration response for UI editing"""
    database: dict
    application: dict
    features: dict
    caching: dict
    admin: dict
    agent: dict


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration"""
    database: dict | None = None
    application: dict | None = None
    features: dict | None = None
    caching: dict | None = None
    admin: dict | None = None
    agent: dict | None = None


class ConfigUpdateResponse(BaseModel):
    """Response after config update"""
    changed_fields: list[str]
    restart_required: bool
    restart_required_fields: list[str]
    message: str


@router.get(
    "/config",
    response_model=APIResponse[ConfigResponse],
    summary="Get configuration",
    description="Get current configuration for UI editing (sensitive fields excluded)",
)
async def get_config(
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[ConfigResponse]:
    """
    Get current configuration suitable for UI editing.

    Returns all editable configuration values, excluding sensitive data
    like password hashes and database credentials.
    """
    from api.services.config_service import get_config_service

    try:
        config_service = get_config_service()
        config = config_service.get_editable_config()

        return APIResponse(
            success=True,
            data=ConfigResponse(**config),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration file not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load configuration: {e!s}",
        )


@router.patch(
    "/config",
    response_model=APIResponse[ConfigUpdateResponse],
    summary="Update configuration",
    description="Update configuration and save to config.yaml (preserves comments)",
)
async def update_config(
    data: ConfigUpdateRequest,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[ConfigUpdateResponse]:
    """
    Update configuration and save to config.yaml.

    This endpoint:
    - Validates updates against Pydantic schema before applying
    - Preserves all YAML comments and formatting
    - Only updates provided fields
    - Returns which fields were changed
    - Indicates if a restart is required for changes to take effect

    Some settings take effect immediately (hot-reload), others require restart.
    """
    from api.config import get_api_settings, get_db_settings
    from api.services.config_service import get_config_service

    try:
        config_service = get_config_service()
        config_service.reload()  # Ensure fresh load

        # Build update dict from provided sections
        updates = {}
        if data.database:
            updates["database"] = data.database
        if data.application:
            updates["application"] = data.application
        if data.features:
            updates["features"] = data.features
        if data.admin:
            # Exclude password_hash from updates (handled separately)
            admin_update = {k: v for k, v in data.admin.items() if k != "password_hash"}
            if admin_update:
                updates["admin"] = admin_update
        if data.agent:
            updates["agent"] = data.agent

        if not updates:
            return APIResponse(
                success=True,
                data=ConfigUpdateResponse(
                    changed_fields=[],
                    restart_required=False,
                    restart_required_fields=[],
                    message="No changes provided",
                ),
            )

        # Validate updates before applying
        validation_errors = config_service.validate_update(updates)
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid configuration: {'; '.join(validation_errors)}",
            )

        # Apply updates
        changed = config_service.update_from_dict(updates)

        if not changed:
            return APIResponse(
                success=True,
                data=ConfigUpdateResponse(
                    changed_fields=[],
                    restart_required=False,
                    restart_required_fields=[],
                    message="No changes detected",
                ),
            )

        # Save to file
        config_service.save()

        # Clear cached settings so they reload
        get_api_settings.cache_clear()
        get_db_settings.cache_clear()

        # Reset GlassTrax service if agent or database settings changed
        agent_or_db_fields = [f for f in changed if f.startswith("agent.") or f.startswith("database.")]
        if agent_or_db_fields:
            from api.dependencies import reset_glasstrax_service
            reset_glasstrax_service()

        # Check if any changed fields require restart
        restart_fields = config_service.get_restart_required_fields()
        restart_required_changes = [f for f in changed if f in restart_fields]
        restart_required = len(restart_required_changes) > 0

        message = f"Configuration updated ({len(changed)} field(s) changed)"
        if restart_required:
            message += ". Restart required for some changes to take effect."

        return APIResponse(
            success=True,
            data=ConfigUpdateResponse(
                changed_fields=changed,
                restart_required=restart_required,
                restart_required_fields=restart_required_changes,
                message=message,
            ),
            message=message,
        )

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration file not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {e!s}",
        )


# ========================================
# Cache Management Endpoints
# ========================================


class CacheStatusResponse(BaseModel):
    """Cache status information"""
    enabled: bool
    entries: int
    total_hits: int
    total_misses: int
    oldest_entry: str | None = None
    newest_entry: str | None = None
    cached_dates: list[str]
    hit_rate: float | None = None  # Percentage


class CacheInvalidateResponse(BaseModel):
    """Response after cache invalidation"""
    invalidated: bool
    date: str | None = None
    cleared_count: int | None = None
    message: str


@router.get(
    "/cache/status",
    response_model=APIResponse[CacheStatusResponse],
    summary="Get cache status",
    description="Get FAB order cache statistics and status",
)
async def get_cache_status(
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[CacheStatusResponse]:
    """
    Get current FAB order cache status.

    Returns statistics including:
    - Number of cached dates
    - Total hits and misses
    - Hit rate percentage
    - List of cached dates
    """
    from api.services.cache_service import get_fab_cache

    cache = get_fab_cache()
    stats = cache.get_stats()

    # Calculate hit rate
    total_requests = stats.total_hits + stats.total_misses
    hit_rate = (stats.total_hits / total_requests * 100) if total_requests > 0 else None

    return APIResponse(
        success=True,
        data=CacheStatusResponse(
            enabled=stats.enabled,
            entries=stats.entries,
            total_hits=stats.total_hits,
            total_misses=stats.total_misses,
            oldest_entry=stats.oldest_entry,
            newest_entry=stats.newest_entry,
            cached_dates=stats.cached_dates,
            hit_rate=round(hit_rate, 1) if hit_rate is not None else None,
        ),
    )


@router.delete(
    "/cache/fabs/{date}",
    response_model=APIResponse[CacheInvalidateResponse],
    summary="Invalidate cache for date",
    description="Clear cached FAB orders for a specific date",
)
async def invalidate_cache_date(
    date: str,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[CacheInvalidateResponse]:
    """
    Invalidate cached FAB orders for a specific date.

    Args:
        date: Date to invalidate (YYYY-MM-DD format)

    Returns:
        Whether the date was found and invalidated
    """
    from api.services.cache_service import get_fab_cache

    cache = get_fab_cache()
    invalidated = cache.invalidate(date)

    return APIResponse(
        success=True,
        data=CacheInvalidateResponse(
            invalidated=invalidated,
            date=date,
            message=f"Cache for {date} invalidated" if invalidated else f"No cache entry for {date}",
        ),
    )


@router.delete(
    "/cache/fabs",
    response_model=APIResponse[CacheInvalidateResponse],
    summary="Clear all FAB cache",
    description="Clear all cached FAB orders",
)
async def clear_all_cache(
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_admin),
) -> APIResponse[CacheInvalidateResponse]:
    """
    Clear all cached FAB orders.

    This invalidates cache for all dates, forcing fresh queries
    on the next request for each date.
    """
    from api.services.cache_service import get_fab_cache

    cache = get_fab_cache()
    count = cache.clear_all()

    return APIResponse(
        success=True,
        data=CacheInvalidateResponse(
            invalidated=count > 0,
            cleared_count=count,
            message=f"Cleared {count} cached date(s)" if count > 0 else "Cache was already empty",
        ),
    )
