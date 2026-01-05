"""
Mock pyodbc module for testing without actual ODBC driver.

pyodbc is Windows-only and requires the Pervasive ODBC driver,
so we mock it entirely for cross-platform testing.
"""

from typing import Any
from unittest.mock import MagicMock

from tests.fixtures.data import (
    SAMPLE_CUSTOMERS,
    SAMPLE_ORDERS,
    CUSTOMER_COLUMNS,
    ORDER_COLUMNS,
)


class MockCursor:
    """
    Mock pyodbc cursor that returns predefined data.

    Simulates cursor.execute(), fetchone(), fetchall(), and description.
    """

    def __init__(
        self,
        data: list[tuple] | None = None,
        columns: list[str] | None = None,
    ):
        self._data = data or []
        self._columns = columns or []
        self._index = 0

        # Format description like pyodbc: list of 7-tuples
        # (name, type_code, display_size, internal_size, precision, scale, null_ok)
        self.description = (
            [(col, str, None, None, None, None, True) for col in self._columns]
            if self._columns
            else None
        )

    def execute(self, sql: str, params: list | None = None) -> "MockCursor":
        """Execute a SQL query (no-op in mock)."""
        self._last_sql = sql
        self._last_params = params
        return self

    def fetchone(self) -> tuple | None:
        """Fetch one row from results."""
        if self._index < len(self._data):
            row = self._data[self._index]
            self._index += 1
            return row
        return None

    def fetchall(self) -> list[tuple]:
        """Fetch all remaining rows from results."""
        remaining = self._data[self._index :]
        self._index = len(self._data)
        return remaining

    def fetchmany(self, size: int = 1) -> list[tuple]:
        """Fetch up to size rows from results."""
        end = min(self._index + size, len(self._data))
        rows = self._data[self._index : end]
        self._index = end
        return rows

    def close(self) -> None:
        """Close the cursor."""
        pass

    def tables(self, catalog: str | None = None, tableType: str | None = None):
        """List tables (mock implementation)."""
        self._data = [("customer",), ("sales_orders_headers",)]
        self._columns = ["table_name"]
        return self


class MockConnection:
    """
    Mock pyodbc connection.

    Returns MockCursor instances and handles commit/close.
    """

    def __init__(self, cursor: MockCursor | None = None):
        self._cursor = cursor or MockCursor()
        self._closed = False

    def cursor(self) -> MockCursor:
        """Get a cursor for executing queries."""
        return self._cursor

    def commit(self) -> None:
        """Commit transaction (no-op in mock)."""
        pass

    def rollback(self) -> None:
        """Rollback transaction (no-op in mock)."""
        pass

    def close(self) -> None:
        """Close the connection."""
        self._closed = True

    def getinfo(self, info_type: int) -> str:
        """Get connection info."""
        return "MockDB"


def _dict_to_tuple(d: dict, columns: list[str]) -> tuple:
    """Convert a dict to a tuple based on column order."""
    return tuple(d.get(col) for col in columns)


def create_mock_pyodbc(
    customers: list[dict] | None = None,
    orders: list[dict] | None = None,
    connection_error: Exception | None = None,
) -> MagicMock:
    """
    Create a configured mock pyodbc module.

    Args:
        customers: List of customer dicts to return (default: SAMPLE_CUSTOMERS)
        orders: List of order dicts to return (default: SAMPLE_ORDERS)
        connection_error: Exception to raise on connect() (simulates DB failure)

    Returns:
        MagicMock configured as pyodbc module
    """
    mock = MagicMock()

    # Define Error class for exception handling
    mock.Error = Exception

    # Use default sample data if not provided
    customers = customers if customers is not None else SAMPLE_CUSTOMERS
    orders = orders if orders is not None else SAMPLE_ORDERS

    # Convert dicts to tuples for cursor data
    customer_rows = [_dict_to_tuple(c, CUSTOMER_COLUMNS) for c in customers]
    order_rows = [_dict_to_tuple(o, ORDER_COLUMNS) for o in orders]

    def mock_connect(conn_str: str, **kwargs) -> MockConnection:
        """Mock pyodbc.connect()"""
        if connection_error:
            raise connection_error

        # Return connection with appropriate data based on typical queries
        # Default to customer data; actual query parsing would be more complex
        cursor = MockCursor(data=customer_rows, columns=CUSTOMER_COLUMNS)
        return MockConnection(cursor=cursor)

    mock.connect = mock_connect

    # Store data for test assertions
    mock._test_customers = customers
    mock._test_orders = orders

    return mock


def create_mock_pyodbc_with_error(error_message: str = "Connection failed") -> MagicMock:
    """
    Create a mock pyodbc that raises an error on connect.

    Args:
        error_message: Error message for the exception

    Returns:
        MagicMock that raises Exception on connect
    """
    return create_mock_pyodbc(connection_error=Exception(error_message))
