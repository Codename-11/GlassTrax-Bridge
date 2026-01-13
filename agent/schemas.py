"""
Agent Request/Response Schemas

Pydantic models for the generic query passthrough API.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class FilterCondition(BaseModel):
    """A single WHERE clause condition"""

    column: str = Field(..., description="Column name to filter on")
    operator: Literal["=", "!=", "<", ">", "<=", ">=", "LIKE", "IN", "NOT IN", "IS NULL", "IS NOT NULL"] = Field(
        ..., description="Comparison operator"
    )
    value: Any = Field(default=None, description="Value to compare against (None for IS NULL/IS NOT NULL)")


class OrderBy(BaseModel):
    """ORDER BY clause specification"""

    column: str = Field(..., description="Column name to order by")
    direction: Literal["ASC", "DESC"] = Field(default="ASC", description="Sort direction")


class JoinClause(BaseModel):
    """JOIN clause specification"""

    table: str = Field(..., description="Table to join")
    alias: str | None = Field(default=None, description="Table alias")
    join_type: Literal["INNER", "LEFT", "RIGHT"] = Field(default="LEFT", description="Join type")
    on_left: str = Field(..., description="Left side of ON condition (e.g., 'c.route_id')")
    on_right: str = Field(..., description="Right side of ON condition (e.g., 'r.route_id')")
    additional_conditions: str | None = Field(
        default=None,
        description="Additional ON conditions (e.g., 'a.branch_id = b.branch_id')"
    )


class QueryRequest(BaseModel):
    """
    Generic query request for GlassTrax data.

    Supports SELECT queries with:
    - Column selection (or * for all)
    - WHERE filtering with multiple conditions
    - JOIN support for related tables
    - ORDER BY sorting
    - Pagination via LIMIT/OFFSET (simulated for Pervasive)
    """

    table: str = Field(..., description="Main table name to query")
    alias: str | None = Field(default=None, description="Table alias for the main table")
    columns: list[str] | None = Field(
        default=None, description="Columns to select (None = all columns from main table)"
    )
    filters: list[FilterCondition] = Field(default_factory=list, description="WHERE conditions (AND-ed together)")
    joins: list[JoinClause] = Field(default_factory=list, description="JOIN clauses")
    order_by: list[OrderBy] = Field(default_factory=list, description="ORDER BY clauses")
    limit: int | None = Field(default=None, ge=1, le=10000, description="Maximum rows to return")
    offset: int | None = Field(default=None, ge=0, description="Rows to skip (for pagination)")


class QueryResponse(BaseModel):
    """
    Response from a query execution.

    Returns column names and rows as a 2D array for efficient transfer.
    """

    success: bool = Field(..., description="Whether the query executed successfully")
    columns: list[str] = Field(default_factory=list, description="Column names in result order")
    rows: list[list[Any]] = Field(default_factory=list, description="Result rows as arrays")
    row_count: int = Field(default=0, description="Number of rows returned")
    error: str | None = Field(default=None, description="Error message if success=False")


class HealthResponse(BaseModel):
    """Agent health check response"""

    status: Literal["healthy", "unhealthy", "degraded"] = Field(..., description="Agent health status")
    version: str = Field(..., description="Agent version")
    pyodbc_installed: bool = Field(..., description="Whether pyodbc is installed")
    database_connected: bool = Field(..., description="Whether database connection is working")
    dsn: str = Field(..., description="Configured DSN name")
    test_query: str | None = Field(default=None, description="Query used for connection test")
    message: str | None = Field(default=None, description="Additional status message")
