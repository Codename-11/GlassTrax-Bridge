"""
GlassTrax Agent - Main Application

Minimal FastAPI service for ODBC query execution.
Runs on Windows with 32-bit Python for Pervasive driver compatibility.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent import __version__
from agent.auth import verify_agent_key
from agent.config import get_config
from agent.query import get_query_service
from agent.schemas import HealthResponse, QueryRequest, QueryResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    # Startup
    config = get_config()
    print(f"GlassTrax Agent v{__version__} starting on port {config.port}")
    print(f"DSN: {config.dsn} (readonly: {config.readonly})")
    print(f"Allowed tables: {', '.join(config.allowed_tables)}")

    yield

    # Shutdown
    service = get_query_service()
    service.close()
    print("GlassTrax Agent stopped")


# Create FastAPI app
app = FastAPI(
    title="GlassTrax Agent",
    description="Minimal ODBC query service for GlassTrax ERP",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# CORS - allow requests from any origin (agent is internal-only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Check agent health and database connectivity.

    No authentication required - used for monitoring.
    """
    config = get_config()
    service = get_query_service()

    db_connected = service.test_connection()

    return HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        version=__version__,
        database_connected=db_connected,
        dsn=config.dsn,
        message=None if db_connected else "Database connection failed",
    )


@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def execute_query(
    request: QueryRequest,
    _: str = Depends(verify_agent_key),
) -> QueryResponse:
    """
    Execute a database query.

    Requires X-Agent-Key header for authentication.

    The query is built from the request parameters:
    - table: Main table to query (must be in allowed_tables)
    - columns: Columns to select (None = all from main table)
    - filters: WHERE conditions (AND-ed together)
    - joins: JOIN clauses for related tables
    - order_by: ORDER BY clauses
    - limit: Maximum rows to return
    - offset: Rows to skip (for pagination)
    """
    service = get_query_service()
    return service.execute(request)


# Entry point for running with uvicorn
if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "agent.main:app",
        host="0.0.0.0",
        port=config.port,
        reload=False,
    )
