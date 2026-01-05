"""
Mock AgentClient for testing agent mode without actual agent.

The AgentClient makes HTTP calls to the GlassTrax API Agent running on Windows.
This mock simulates those responses for cross-platform testing.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from tests.fixtures.data import (
    SAMPLE_CUSTOMERS,
    SAMPLE_ORDERS,
    CUSTOMER_COLUMNS,
    ORDER_COLUMNS,
)


def _dict_to_row(d: dict, columns: list[str]) -> list[Any]:
    """Convert a dict to a list based on column order."""
    return [d.get(col) for col in columns]


def create_mock_agent_client(
    customers: list[dict] | None = None,
    orders: list[dict] | None = None,
    is_healthy: bool = True,
    connection_error: Exception | None = None,
) -> MagicMock:
    """
    Create a mock AgentClient for testing agent mode.

    Args:
        customers: Customer data to return
        orders: Order data to return
        is_healthy: Whether health check passes
        connection_error: Exception to raise on queries (simulates network failure)

    Returns:
        MagicMock configured as AgentClient
    """
    mock = MagicMock()

    # Use default sample data if not provided
    customers = customers if customers is not None else SAMPLE_CUSTOMERS
    orders = orders if orders is not None else SAMPLE_ORDERS

    # Convert dicts to row format (list of lists)
    customer_rows = [_dict_to_row(c, CUSTOMER_COLUMNS) for c in customers]
    order_rows = [_dict_to_row(o, ORDER_COLUMNS) for o in orders]

    # Mock health check
    async def mock_health_check():
        if connection_error:
            raise connection_error
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "version": "1.0.0",
            "pyodbc_installed": True,
            "database_connected": is_healthy,
            "dsn": "TEST",
            "message": "OK" if is_healthy else "Database connection failed",
        }

    mock.health_check = AsyncMock(side_effect=mock_health_check)

    # Mock is_healthy property
    async def mock_is_healthy_check():
        if connection_error:
            return False
        return is_healthy

    mock.is_healthy = AsyncMock(side_effect=mock_is_healthy_check)

    # Mock query method
    async def mock_query(request):
        if connection_error:
            raise connection_error

        # Return QueryResponse-like object
        result = MagicMock()
        result.success = True
        result.error = None

        # Determine which data to return based on table name
        table = getattr(request, "table", "customer")
        if "order" in table.lower():
            result.columns = ORDER_COLUMNS
            result.rows = order_rows
            result.row_count = len(order_rows)
        else:
            result.columns = CUSTOMER_COLUMNS
            result.rows = customer_rows
            result.row_count = len(customer_rows)

        return result

    mock.query = AsyncMock(side_effect=mock_query)

    # Mock query_table method (simplified interface)
    async def mock_query_table(
        table: str,
        columns: list[str] | None = None,
        filters: list | None = None,
        order_by: list | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        if connection_error:
            raise connection_error

        result = MagicMock()
        result.success = True
        result.error = None

        if "order" in table.lower():
            result.columns = ORDER_COLUMNS
            result.rows = order_rows[offset : offset + limit]
            result.row_count = len(result.rows)
        else:
            result.columns = CUSTOMER_COLUMNS
            result.rows = customer_rows[offset : offset + limit]
            result.row_count = len(result.rows)

        return result

    mock.query_table = AsyncMock(side_effect=mock_query_table)

    # Mock count_table method
    async def mock_count_table(table: str, filters: list | None = None):
        if connection_error:
            raise connection_error

        if "order" in table.lower():
            return len(orders)
        return len(customers)

    mock.count_table = AsyncMock(side_effect=mock_count_table)

    # Mock close method
    mock.close = AsyncMock()

    # Store data for test assertions
    mock._test_customers = customers
    mock._test_orders = orders

    return mock


def create_mock_agent_client_with_error(
    error_message: str = "Agent connection failed",
) -> MagicMock:
    """
    Create a mock AgentClient that raises errors on all operations.

    Args:
        error_message: Error message for exceptions

    Returns:
        MagicMock that raises Exception on all async operations
    """
    return create_mock_agent_client(connection_error=Exception(error_message))
