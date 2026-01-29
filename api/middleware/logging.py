### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Request Logging Middleware -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Request Logging Middleware

Logs all API requests with attribution information:
- Who: API key/tenant info
- What: Endpoint, method, parameters
- When: Timestamp
- Result: Status code, response time

Logs to both file and SQLite database for dashboard viewing.
"""

import time
import uuid
from collections.abc import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.database import SessionLocal
from api.models.access_log import AccessLog
from api.utils import setup_logger

# Set up API logger
api_logger = setup_logger("glasstrax_api", log_to_file=True, log_to_console=False)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all API requests

    Captures:
    - Request ID (UUID)
    - Timestamp
    - Method and path
    - API key (masked)
    - Client IP
    - Response status
    - Response time

    Excludes internal/admin requests from database logging (still logs to file).
    """

    # Paths to exclude from database logging (internal/admin operations)
    EXCLUDE_FROM_DB = (
        "/health",
        "/api/v1/admin/",  # All admin endpoints (portal operations)
        "/api/v1/auth/",   # Auth endpoints
        "/docs",
        "/openapi.json",
        "/favicon.ico",
    )

    def _should_log_to_db(self, path: str) -> bool:
        """Check if request should be logged to database (excludes internal requests)"""
        return not any(path.startswith(prefix) for prefix in self.EXCLUDE_FROM_DB)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Capture start time
        start_time = time.time()

        # Extract request info
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        client_ip = request.client.host if request.client else "unknown"

        # Get API key (masked)
        api_key = request.headers.get("X-API-Key", "none")
        masked_key = api_key[:8] + "..." if len(api_key) > 8 else api_key

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            api_logger.error(
                f"[{request_id}] ERROR {method} {path} - {e!s}"
            )
            raise

        # Calculate response time
        response_time = (time.time() - start_time) * 1000  # ms

        # Log the request
        log_entry = (
            f"[{request_id}] "
            f"{method} {path}"
            f"{f'?{query}' if query else ''} "
            f"| key={masked_key} "
            f"| ip={client_ip} "
            f"| status={status_code} "
            f"| time={response_time:.2f}ms"
        )

        # Log at appropriate level
        if status_code >= 500:
            api_logger.error(log_entry)
        elif status_code >= 400:
            api_logger.warning(log_entry)
        else:
            api_logger.info(log_entry)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Save to database (non-blocking, separate session)
        # Skip internal/admin requests - they clutter the logs meant for API clients
        if self._should_log_to_db(path):
            self._save_access_log(
                request_id=request_id,
                method=method,
                path=path,
                query_string=query if query else None,
                status_code=status_code,
                response_time_ms=response_time,
                client_ip=client_ip,
                user_agent=request.headers.get("User-Agent"),
                request=request,
            )

        return response

    def _save_access_log(
        self,
        request_id: str,
        method: str,
        path: str,
        query_string: str,
        status_code: int,
        response_time_ms: float,
        client_ip: str,
        user_agent: str,
        request: Request,
    ):
        """Save access log entry to database"""
        try:
            # Get API key info from request state (set by auth middleware)
            api_key_info = getattr(request.state, "api_key_info", None)

            api_key_id = None
            tenant_id = None
            key_prefix = None

            if api_key_info:
                # key_id may be None for dev keys, or a string for JWT auth
                key_id = api_key_info.key_id
                api_key_id = key_id if isinstance(key_id, int) else None
                tenant_id_str = getattr(api_key_info, "tenant_id", None)
                # Convert tenant_id to int if it's a numeric string
                if tenant_id_str and tenant_id_str.isdigit():
                    tenant_id = int(tenant_id_str)
                key_prefix = api_key_info.key_prefix

            # Create log entry in a new session
            db = SessionLocal()
            try:
                log_entry = AccessLog.create_from_request(
                    request_id=request_id,
                    method=method,
                    path=path,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    api_key_id=api_key_id,
                    tenant_id=tenant_id,
                    key_prefix=key_prefix,
                    query_string=query_string,
                    client_ip=client_ip,
                    user_agent=user_agent,
                )
                db.add(log_entry)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            # Log the error but don't fail the request
            api_logger.error(f"Failed to save access log: {e!s}")


class AccessLogEntry:
    """
    Access log entry for database storage (Phase 2)

    Will be stored in SQLite for dashboard viewing and audit trails.
    """

    def __init__(
        self,
        request_id: str,
        timestamp: datetime,
        method: str,
        path: str,
        query_params: str,
        api_key_id: str,
        tenant_id: str,
        client_ip: str,
        status_code: int,
        response_time_ms: float,
        user_agent: str | None = None,
    ):
        self.request_id = request_id
        self.timestamp = timestamp
        self.method = method
        self.path = path
        self.query_params = query_params
        self.api_key_id = api_key_id
        self.tenant_id = tenant_id
        self.client_ip = client_ip
        self.status_code = status_code
        self.response_time_ms = response_time_ms
        self.user_agent = user_agent

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "method": self.method,
            "path": self.path,
            "query_params": self.query_params,
            "api_key_id": self.api_key_id,
            "tenant_id": self.tenant_id,
            "client_ip": self.client_ip,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "user_agent": self.user_agent,
        }
