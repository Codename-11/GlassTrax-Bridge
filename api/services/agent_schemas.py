"""
Agent Request/Response Schemas (API Side)

These schemas mirror the agent's schemas and are used by the AgentClient
to communicate with the GlassTrax Agent.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class FilterCondition(BaseModel):
    """A single WHERE clause condition"""

    column: str = Field(..., description="Column name to filter on")
    operator: Literal["=", "!=", "<", ">", "<=", ">=", "LIKE", "IN", "NOT IN", "IS NULL", "IS NOT NULL"] = Field(
        ..., description="Comparison operator"
    )
    value: Any = Field(default=None, description="Value to compare against")


class OrderBy(BaseModel):
    """ORDER BY clause specification"""

    column: str = Field(..., description="Column name to order by")
    direction: Literal["ASC", "DESC"] = Field(default="ASC", description="Sort direction")


class JoinClause(BaseModel):
    """JOIN clause specification"""

    table: str = Field(..., description="Table to join")
    alias: str | None = Field(default=None, description="Table alias")
    join_type: Literal["INNER", "LEFT", "RIGHT"] = Field(default="LEFT", description="Join type")
    on_left: str = Field(..., description="Left side of ON condition")
    on_right: str = Field(..., description="Right side of ON condition")


class QueryRequest(BaseModel):
    """Generic query request for GlassTrax data"""

    table: str = Field(..., description="Main table name to query")
    alias: str | None = Field(default=None, description="Table alias")
    columns: list[str] | None = Field(default=None, description="Columns to select")
    filters: list[FilterCondition] = Field(default_factory=list, description="WHERE conditions")
    joins: list[JoinClause] = Field(default_factory=list, description="JOIN clauses")
    order_by: list[OrderBy] = Field(default_factory=list, description="ORDER BY clauses")
    limit: int | None = Field(default=None, ge=1, le=10000, description="Maximum rows")
    offset: int | None = Field(default=None, ge=0, description="Rows to skip")


class QueryResponse(BaseModel):
    """Response from a query execution"""

    success: bool = Field(..., description="Whether the query succeeded")
    columns: list[str] = Field(default_factory=list, description="Column names")
    rows: list[list[Any]] = Field(default_factory=list, description="Result rows")
    row_count: int = Field(default=0, description="Number of rows returned")
    error: str | None = Field(default=None, description="Error message if failed")
