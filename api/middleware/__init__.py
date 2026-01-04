### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - API Middleware Package -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
API Middleware Package

Contains middleware for request processing:
- auth: API key validation
- logging: Request/response logging
- rate_limit: Rate limiting (future)
"""

from .auth import (
    get_api_key,
    require_permission,
    require_customers_read,
    require_orders_read,
    require_admin,
    APIKeyInfo,
)
from .logging import RequestLoggingMiddleware

__all__ = [
    "get_api_key",
    "require_permission",
    "require_customers_read",
    "require_orders_read",
    "require_admin",
    "APIKeyInfo",
    "RequestLoggingMiddleware",
]
