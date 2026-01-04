### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Common Response Schemas -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Common Response Schemas

Pydantic models for standardized API responses.
"""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper"""

    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    total_items: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response"""

    success: bool = True
    data: List[T] = Field(default_factory=list)
    pagination: PaginationMeta


class ErrorDetail(BaseModel):
    """Error detail for validation errors"""

    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response"""

    success: bool = False
    error: str
    details: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = "healthy"
    version: str
    database_name: str = "GlassTrax Database"
    glasstrax_connected: bool
    app_db_connected: bool
