"""
Mock pyodbc module for agent testing.

The agent uses pyodbc for ODBC database access to GlassTrax.
This mock allows testing without the actual driver.
"""

from unittest.mock import MagicMock


class MockCursor:
    """Mock pyodbc cursor."""

    def __init__(
        self,
        data: list[tuple] | None = None,
        columns: list[str] | None = None,
    ):
        self._data = data or []
        self._columns = columns or []
        self._index = 0
        self._last_sql = ""
        self._last_params = []

        # pyodbc cursor.description format
        self.description = (
            [(col, str, None, None, None, None, True) for col in self._columns]
            if self._columns
            else None
        )

    def execute(self, sql: str, params: list | None = None) -> "MockCursor":
        """Record executed SQL and params."""
        self._last_sql = sql
        self._last_params = params or []
        return self

    def fetchone(self) -> tuple | None:
        """Fetch next row."""
        if self._index < len(self._data):
            row = self._data[self._index]
            self._index += 1
            return row
        return None

    def fetchall(self) -> list[tuple]:
        """Fetch all remaining rows."""
        remaining = self._data[self._index:]
        self._index = len(self._data)
        return remaining

    def close(self) -> None:
        """Close cursor."""
        pass


class MockConnection:
    """Mock pyodbc connection."""

    def __init__(self, cursor: MockCursor | None = None):
        self._cursor = cursor or MockCursor()
        self._closed = False

    def cursor(self) -> MockCursor:
        """Get cursor."""
        return self._cursor

    def close(self) -> None:
        """Close connection."""
        self._closed = True


class MockPyodbcError(Exception):
    """Mock pyodbc.Error exception."""

    pass


def create_mock_pyodbc(
    data: list[tuple] | None = None,
    columns: list[str] | None = None,
    connection_error: Exception | None = None,
) -> MagicMock:
    """
    Create a mock pyodbc module.

    Args:
        data: Rows to return from queries
        columns: Column names
        connection_error: Exception to raise on connect

    Returns:
        MagicMock configured as pyodbc
    """
    mock = MagicMock()
    mock.Error = MockPyodbcError

    def mock_connect(conn_str: str, **kwargs) -> MockConnection:
        if connection_error:
            raise connection_error
        cursor = MockCursor(data=data, columns=columns)
        return MockConnection(cursor=cursor)

    mock.connect = mock_connect

    return mock
