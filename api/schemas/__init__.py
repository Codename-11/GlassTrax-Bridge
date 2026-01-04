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

from .customer import CustomerBase, CustomerResponse, CustomerListResponse
from .order import OrderBase, OrderResponse, OrderListResponse
from .responses import APIResponse, PaginatedResponse, ErrorResponse

__all__ = [
    "CustomerBase",
    "CustomerResponse",
    "CustomerListResponse",
    "OrderBase",
    "OrderResponse",
    "OrderListResponse",
    "APIResponse",
    "PaginatedResponse",
    "ErrorResponse",
]
