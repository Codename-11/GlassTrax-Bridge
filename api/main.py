# GlassTrax Bridge - API Server
# Copyright (c) 2025-2026 Axiom-Labs. All Rights Reserved.
# See LICENSE file for details.

"""
GlassTrax Bridge API - Main Application

FastAPI application entry point that provides:
- REST API endpoints for GlassTrax data access
- API key authentication
- Request logging and attribution
- OpenAPI documentation at /docs

Usage:
    # Development
    uvicorn api.main:app --reload --port 8000

    # Production
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.config import get_api_settings, get_db_settings, load_yaml_config
from api.routers import customers_router, orders_router, keys_router
from api.schemas.responses import ErrorResponse, HealthResponse
from api.middleware import RequestLoggingMiddleware
from api.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from api.dependencies import close_glasstrax_service, get_glasstrax_service
from api.database import init_db, get_db, DATABASE_PATH, engine
from api.models import Tenant, APIKey


# Load settings
settings = get_api_settings()


def _setup_initial_admin_key():
    """
    Auto-generate admin API key on first run if none exist.

    This ensures secure initial setup:
    - Creates a 'System' tenant for admin operations
    - Generates an admin API key with full permissions
    - Displays the key ONCE in the console (won't be shown again)
    - Once this key exists, bootstrap keys are automatically disabled
    """
    db = next(get_db())
    try:
        # Check if any admin API keys exist
        admin_keys = db.query(APIKey).filter(APIKey.is_active == True).all()
        has_admin_key = any(
            key.permissions and ("admin:*" in key.permissions or "*:*" in key.permissions)
            for key in admin_keys
        )

        if has_admin_key:
            return  # Admin key already exists

        # Check if System tenant exists, create if not
        system_tenant = db.query(Tenant).filter(Tenant.name == "System").first()
        if not system_tenant:
            system_tenant = Tenant(
                name="System",
                description="System tenant for admin operations",
                contact_email="admin@localhost",
                is_active=True,
            )
            db.add(system_tenant)
            db.commit()
            db.refresh(system_tenant)

        # Generate admin API key
        api_key, raw_key = APIKey.create_key(
            tenant_id=system_tenant.id,
            name="Auto-generated Admin Key",
            permissions=["*:*", "admin:*"],
            rate_limit=1000,  # Higher limit for admin
        )
        db.add(api_key)
        db.commit()

        # Display the key prominently (only shown once!)
        print("\n" + "=" * 70)
        print("  INITIAL ADMIN API KEY GENERATED")
        print("=" * 70)
        print(f"\n  Key: {raw_key}\n")
        print("  IMPORTANT: Save this key now! It will NOT be shown again.")
        print("  This key has full admin permissions.")
        print("  Bootstrap keys are now DISABLED.\n")
        print("=" * 70 + "\n")

    finally:
        db.close()


def _check_pending_migrations():
    """
    Check for pending Alembic migrations on startup.

    Logs a warning if the database schema is not up to date.
    Does not block startup - just warns the administrator.
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext

        # Load Alembic config
        alembic_cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)

        # Get current revision from database
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()

        # Get latest revision from migration scripts
        head_rev = script.get_current_head()

        if current_rev is None:
            print("\n" + "=" * 70)
            print("  DATABASE MIGRATION REQUIRED")
            print("=" * 70)
            print("\n  The database has not been initialized with Alembic.")
            print("  If this is an existing database, stamp it with the current version:")
            print("\n    python32\\python.exe -m alembic stamp head")
            print("\n  For a new database, run migrations:")
            print("\n    python32\\python.exe -m alembic upgrade head")
            print("=" * 70 + "\n")
        elif current_rev != head_rev:
            print("\n" + "=" * 70)
            print("  PENDING DATABASE MIGRATIONS")
            print("=" * 70)
            print(f"\n  Current version: {current_rev}")
            print(f"  Latest version:  {head_rev}")
            print("\n  Run migrations with:")
            print("\n    python32\\python.exe -m alembic upgrade head")
            print("=" * 70 + "\n")
        else:
            print(f"Database schema is up to date (revision: {current_rev})")

    except ImportError:
        # Alembic not installed - skip check
        pass
    except Exception as e:
        # Don't fail startup on migration check errors
        print(f"Warning: Could not check migrations: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager

    Handles startup and shutdown events:
    - Startup: Initialize database connections, load config
    - Shutdown: Clean up resources
    """
    # Startup
    print(f"Starting {settings.api_title} v{settings.api_version}")
    print(f"API documentation available at: http://localhost:{settings.port}/docs")

    # Load YAML config for GlassTrax connection settings
    yaml_config = load_yaml_config()
    app.state.yaml_config = yaml_config

    # Ensure data directory exists for SQLite
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # Initialize app database (SQLite)
    init_db()
    app.state.app_db_connected = True

    # Check for pending migrations
    _check_pending_migrations()

    # Auto-generate admin key on first run (if none exist)
    _setup_initial_admin_key()

    yield

    # Shutdown
    print("Shutting down GlassTrax Bridge API...")
    close_glasstrax_service()


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
## GlassTrax Bridge API

REST API for accessing GlassTrax ERP data.

### Features
- **Customers**: Query customer information
- **Orders**: Query order data and history
- **Authentication**: API key-based access control
- **Rate Limiting**: Per-key request limits
- **Logging**: Full request attribution and audit trail

### Authentication
All endpoints require an API key passed in the `X-API-Key` header.

```
X-API-Key: your-api-key-here
```
    """,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            details=[{"message": str(exc)}] if settings.debug else None,
        ).model_dump(),
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Check API health and connectivity status",
)
async def health_check():
    """
    Health check endpoint

    Returns the health status of the API including:
    - API version
    - GlassTrax database connectivity
    - App database connectivity
    - Data access mode (agent or direct)
    """
    from api.config import load_yaml_config

    # Get database settings
    db_settings = get_db_settings()

    # Check if agent mode is enabled
    yaml_config = load_yaml_config()
    agent_config = yaml_config.get("agent", {}) if yaml_config else {}
    agent_enabled = agent_config.get("enabled", False)
    mode = "agent" if agent_enabled else "direct"

    # Test GlassTrax connectivity
    glasstrax_connected = False
    try:
        service = next(get_glasstrax_service())
        glasstrax_connected = await service.test_connection()
    except Exception:
        pass

    # Check app DB
    app_db_connected = getattr(app.state, "app_db_connected", False)

    # Build response with mode info
    response = {
        "status": "healthy" if glasstrax_connected and app_db_connected else "degraded",
        "version": settings.api_version,
        "database_name": db_settings.friendly_name,
        "glasstrax_connected": glasstrax_connected,
        "app_db_connected": app_db_connected,
        "mode": mode,
    }

    # Add agent URL if in agent mode
    if agent_enabled:
        response["agent_url"] = agent_config.get("url", "")

    return response


# Root endpoint
@app.get("/", tags=["System"], summary="API Info")
async def root():
    """API root - returns basic API information"""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
    }


# Include routers
app.include_router(
    customers_router,
    prefix=f"{settings.api_prefix}/customers",
    tags=["Customers"],
)

app.include_router(
    orders_router,
    prefix=f"{settings.api_prefix}/orders",
    tags=["Orders"],
)

app.include_router(
    keys_router,
    prefix=f"{settings.api_prefix}/admin",
    tags=["Admin - Key Management"],
)


# Mount static files for production (when built assets exist)
# Documentation hosted on GitHub Pages: https://codename-11.github.io/GlassTrax-Bridge/
_portal_dist = Path(__file__).parent.parent / "portal" / "dist"

if _portal_dist.exists():
    # Serve portal static assets
    app.mount("/assets", StaticFiles(directory=str(_portal_dist / "assets")), name="portal-assets")

    # SPA fallback - serve index.html for all non-API routes
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_portal(full_path: str):
        """Serve portal SPA - fallback for client-side routing"""
        # Don't serve for API routes
        if full_path.startswith(("api/", "health")):
            return JSONResponse({"error": "Not found"}, status_code=404)

        index_file = _portal_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse({"error": "Portal not built"}, status_code=404)


# Entry point for running directly
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
