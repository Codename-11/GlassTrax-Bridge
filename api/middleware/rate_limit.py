### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Rate Limiting Middleware -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Rate Limiting Middleware

Implements per-API-key rate limiting using slowapi.
Each API key has its own rate limit (requests per minute).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse


def get_api_key_identifier(request: Request) -> str:
    """
    Get rate limit identifier from API key.
    Falls back to IP address if no key present.
    """
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        # Use key prefix for identification (first 12 chars)
        return f"key:{api_key[:12]}"
    return f"ip:{get_remote_address(request)}"


def get_key_rate_limit(request: Request) -> str:
    """
    Get the rate limit for the current request based on API key.
    Returns a rate limit string like "60/minute".
    """
    # Check if api_key_info was set by auth middleware
    api_key_info = getattr(request.state, "api_key_info", None)

    if api_key_info:
        # Get rate limit from the key (default 60/min)
        rate = getattr(api_key_info, "rate_limit", 60) or 60
        return f"{rate}/minute"

    # Default rate limit for unauthenticated requests
    return "30/minute"


# Create limiter instance
limiter = Limiter(
    key_func=get_api_key_identifier,
    default_limits=["60/minute"],
    storage_uri="memory://",
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded. {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60),
        },
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
    )
