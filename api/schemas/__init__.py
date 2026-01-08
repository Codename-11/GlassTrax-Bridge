### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - API Schemas Package -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
API Schemas Package

Contains Pydantic models for request/response validation:
- customer: Customer data schemas
- order: Order data schemas
- responses: Common response schemas
"""

from .customer import CustomerBase, CustomerListResponse, CustomerResponse
from .order import OrderBase, OrderListResponse, OrderResponse
from .responses import APIResponse, ErrorResponse, PaginatedResponse

__all__ = [
    "APIResponse",
    "CustomerBase",
    "CustomerListResponse",
    "CustomerResponse",
    "ErrorResponse",
    "OrderBase",
    "OrderListResponse",
    "OrderResponse",
    "PaginatedResponse",
]
