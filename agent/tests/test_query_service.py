"""
Unit tests for QueryService.

Tests SQL building, validation, and query execution.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from agent.schemas import (
    FilterCondition,
    JoinClause,
    OrderBy,
    QueryRequest,
)


class TestValidateIdentifier:
    """Test identifier validation."""

    @pytest.fixture
    def query_service(self, mock_config, mock_pyodbc):
        """Create QueryService with mocks."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    from agent.query import QueryService

                    return QueryService()

    def test_valid_simple_name(self, query_service):
        """Simple alphanumeric name should pass."""
        result = query_service._validate_identifier("customer")
        assert result == "customer"

    def test_valid_with_underscore(self, query_service):
        """Name with underscore should pass."""
        result = query_service._validate_identifier("customer_name")
        assert result == "customer_name"

    def test_valid_with_dot(self, query_service):
        """Name with dot (table.column) should pass."""
        result = query_service._validate_identifier("c.customer_id")
        assert result == "c.customer_id"

    def test_strips_quotes(self, query_service):
        """Quotes should be stripped."""
        result = query_service._validate_identifier('"customer"')
        assert result == "customer"

    def test_rejects_sql_injection(self, query_service):
        """SQL injection attempt should be rejected."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            query_service._validate_identifier("customer; DROP TABLE--")

    def test_rejects_semicolon(self, query_service):
        """Semicolon should be rejected."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            query_service._validate_identifier("customer;")

    def test_rejects_comment(self, query_service):
        """Comment markers should be rejected."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            query_service._validate_identifier("customer--comment")

    def test_count_rejected_without_expression_flag(self, query_service):
        """COUNT(*) should be rejected without allow_expressions."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            query_service._validate_identifier("COUNT(*)")

    def test_count_allowed_with_expression_flag(self, query_service):
        """COUNT(*) should be allowed with allow_expressions=True."""
        result = query_service._validate_identifier("COUNT(*)", allow_expressions=True)
        assert result == "COUNT(*)"

    def test_complex_expression_allowed(self, query_service):
        """Complex expressions should be allowed with allow_expressions=True."""
        result = query_service._validate_identifier("COALESCE(a, b) AS result", allow_expressions=True)
        assert result == "COALESCE(a, b) AS result"

    def test_sql_injection_blocked_even_in_expression_mode(self, query_service):
        """SQL injection should be blocked even with allow_expressions=True."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            query_service._validate_identifier("col; DROP TABLE users--", allow_expressions=True)


class TestValidateTable:
    """Test table allowlist validation."""

    @pytest.fixture
    def query_service(self, mock_config, mock_pyodbc):
        """Create QueryService with mocks."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    from agent.query import QueryService

                    return QueryService()

    def test_allowed_table_passes(self, query_service):
        """Allowed table should pass validation."""
        query_service._validate_table("customer")  # Should not raise

    def test_allowed_table_case_insensitive(self, query_service):
        """Table validation should be case-insensitive."""
        query_service._validate_table("CUSTOMER")  # Should not raise
        query_service._validate_table("Customer")  # Should not raise

    def test_disallowed_table_fails(self, query_service):
        """Disallowed table should raise ValueError."""
        with pytest.raises(ValueError, match="not in agent's allowed_tables"):
            query_service._validate_table("forbidden_table")

    def test_error_lists_allowed_tables(self, query_service):
        """Error message should list allowed tables."""
        with pytest.raises(ValueError) as exc_info:
            query_service._validate_table("hackers_table")

        assert "customer" in str(exc_info.value).lower()


class TestBuildQuery:
    """Test SQL query building."""

    @pytest.fixture
    def query_service(self, mock_config, mock_pyodbc):
        """Create QueryService with mocks."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    from agent.query import QueryService

                    return QueryService()

    def test_simple_select(self, query_service):
        """Build simple SELECT * query."""
        request = QueryRequest(table="customer")
        sql, params = query_service._build_query(request)

        assert "SELECT" in sql
        assert "FROM customer" in sql
        assert params == []

    def test_select_with_columns(self, query_service):
        """Build SELECT with specific columns."""
        request = QueryRequest(
            table="customer",
            columns=["customer_id", "customer_name"],
        )
        sql, params = query_service._build_query(request)

        assert "customer_id" in sql
        assert "customer_name" in sql

    def test_select_with_limit(self, query_service):
        """Build SELECT with TOP limit."""
        request = QueryRequest(table="customer", limit=10)
        sql, params = query_service._build_query(request)

        assert "TOP 10" in sql

    def test_select_with_offset(self, query_service):
        """Build SELECT with offset (fetches extra rows)."""
        request = QueryRequest(table="customer", limit=10, offset=20)
        sql, params = query_service._build_query(request)

        # Should fetch limit + offset rows
        assert "TOP 30" in sql

    def test_select_with_where(self, query_service):
        """Build SELECT with WHERE clause."""
        request = QueryRequest(
            table="customer",
            filters=[
                FilterCondition(column="main_state", operator="=", value="MA"),
            ],
        )
        sql, params = query_service._build_query(request)

        assert "WHERE" in sql
        assert "main_state = ?" in sql
        assert params == ["MA"]

    def test_where_with_like(self, query_service):
        """Build WHERE with LIKE operator."""
        request = QueryRequest(
            table="customer",
            filters=[
                FilterCondition(column="customer_name", operator="LIKE", value="%test%"),
            ],
        )
        sql, params = query_service._build_query(request)

        assert "LIKE ?" in sql
        assert params == ["%test%"]

    def test_where_with_in(self, query_service):
        """Build WHERE with IN operator."""
        request = QueryRequest(
            table="customer",
            filters=[
                FilterCondition(column="main_state", operator="IN", value=["MA", "NY", "CT"]),
            ],
        )
        sql, params = query_service._build_query(request)

        assert "IN (?, ?, ?)" in sql
        assert params == ["MA", "NY", "CT"]

    def test_where_with_is_null(self, query_service):
        """Build WHERE with IS NULL."""
        request = QueryRequest(
            table="customer",
            filters=[
                FilterCondition(column="fax", operator="IS NULL", value=None),
            ],
        )
        sql, params = query_service._build_query(request)

        assert "IS NULL" in sql
        assert params == []

    def test_select_with_order_by(self, query_service):
        """Build SELECT with ORDER BY."""
        request = QueryRequest(
            table="customer",
            order_by=[
                OrderBy(column="customer_name", direction="ASC"),
            ],
        )
        sql, params = query_service._build_query(request)

        assert "ORDER BY" in sql
        assert "customer_name ASC" in sql

    def test_select_with_join(self, query_service):
        """Build SELECT with JOIN."""
        request = QueryRequest(
            table="customer",
            alias="c",
            columns=["c.customer_id", "r.route_name"],
            joins=[
                JoinClause(
                    table="delivery_routes",
                    alias="r",
                    join_type="LEFT",
                    on_left="c.route_id",
                    on_right="r.route_id",
                ),
            ],
        )
        sql, params = query_service._build_query(request)

        assert "LEFT JOIN delivery_routes r" in sql
        assert "ON c.route_id = r.route_id" in sql


class TestConvertValue:
    """Test value conversion for JSON serialization."""

    @pytest.fixture
    def query_service(self, mock_config, mock_pyodbc):
        """Create QueryService with mocks."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    from agent.query import QueryService

                    return QueryService()

    def test_none_value(self, query_service):
        """None should remain None."""
        assert query_service._convert_value(None) is None

    def test_string_stripped(self, query_service):
        """Strings should be stripped."""
        assert query_service._convert_value("  test  ") == "test"

    def test_bytes_decoded(self, query_service):
        """Bytes should be decoded to string."""
        result = query_service._convert_value(b"  hello  ")
        assert result == "hello"

    def test_bytes_non_utf8_to_hex(self, query_service):
        """Non-UTF8 bytes should become hex."""
        result = query_service._convert_value(b"\xff\xfe")
        assert result == "fffe"

    def test_int_passthrough(self, query_service):
        """Integers should pass through."""
        assert query_service._convert_value(42) == 42

    def test_float_passthrough(self, query_service):
        """Floats should pass through."""
        assert query_service._convert_value(3.14) == 3.14


class TestExecute:
    """Test query execution."""

    def test_execute_success(self, mock_config, mock_pyodbc):
        """Successful query should return success response."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    with patch("agent.query.check_pyodbc_available"):
                        from agent.query import QueryService

                        service = QueryService()
                        service._conn = mock_pyodbc.connect("")

                        request = QueryRequest(table="customer")
                        result = service.execute(request)

                        assert result.success is True
                        assert result.error is None
                        assert result.columns == ["customer_id", "customer_name", "route_id"]
                        assert len(result.rows) == 1

    def test_execute_invalid_table(self, mock_config, mock_pyodbc):
        """Invalid table should return error response."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    with patch("agent.query.check_pyodbc_available"):
                        from agent.query import QueryService

                        service = QueryService()
                        service._conn = mock_pyodbc.connect("")

                        request = QueryRequest(table="forbidden_table")
                        result = service.execute(request)

                        assert result.success is False
                        assert "not in agent's allowed_tables" in result.error


class TestConnectionRecycling:
    """Test connection recycling and auto-reconnect."""

    def test_connection_recycle_after_max_age(self, mock_config, mock_pyodbc):
        """Connection should be recycled after MAX_CONNECTION_AGE."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    with patch("agent.query.check_pyodbc_available"):
                        from agent.query import MAX_CONNECTION_AGE, QueryService

                        service = QueryService()
                        # Create initial connection
                        service._get_connection()
                        assert service._conn is not None

                        # Simulate connection age exceeding MAX_CONNECTION_AGE
                        service._conn_created_at = time.time() - MAX_CONNECTION_AGE - 10

                        # Getting connection should trigger recycle
                        service._get_connection()
                        # A new connection should have been created (mock returns new object)
                        assert service._conn_created_at > time.time() - 5

    def test_connection_recycle_after_errors(self, mock_config, mock_pyodbc):
        """Connection should be recycled after MAX_CONSECUTIVE_ERRORS."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    with patch("agent.query.check_pyodbc_available"):
                        from agent.query import MAX_CONSECUTIVE_ERRORS, QueryService

                        service = QueryService()
                        service._get_connection()

                        # Simulate consecutive errors
                        service._consecutive_errors = MAX_CONSECUTIVE_ERRORS

                        # Getting connection should trigger recycle
                        service._get_connection()
                        # Error count should be reset
                        assert service._consecutive_errors == 0

    def test_is_connection_error_detection(self, mock_config, mock_pyodbc):
        """Connection errors should be properly detected."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    from agent.query import QueryService

                    service = QueryService()

                    # Should detect connection errors
                    assert service._is_connection_error("Connection closed")
                    assert service._is_connection_error("network timeout")
                    assert service._is_connection_error("Communication link failure")

                    # Should not flag other errors
                    assert not service._is_connection_error("Invalid syntax")
                    assert not service._is_connection_error("Table not found")

    def test_query_count_increments(self, mock_config, mock_pyodbc):
        """Query count should increment with each execution."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    with patch("agent.query.check_pyodbc_available"):
                        from agent.query import QueryService

                        service = QueryService()
                        service._conn = mock_pyodbc.connect("")

                        assert service._query_count == 0

                        request = QueryRequest(table="customer")
                        service.execute(request)
                        assert service._query_count == 1

                        service.execute(request)
                        assert service._query_count == 2


class TestCustomTestQuery:
    """Test configurable test query for health checks."""

    def test_test_connection_uses_config_query(self, mock_config, mock_pyodbc):
        """test_connection should use configured test_query."""
        mock_config.get = MagicMock(side_effect=lambda key, default=None: {
            "agent.test_query": "SELECT COUNT(*) FROM customer",
        }.get(key, default))

        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    with patch("agent.query.check_pyodbc_available"):
                        from agent.query import QueryService

                        service = QueryService()
                        service._conn = mock_pyodbc.connect("")

                        # Should succeed (mock cursor executes anything)
                        result = service.test_connection()
                        assert result is True

    def test_test_connection_custom_query_parameter(self, mock_config, mock_pyodbc):
        """test_connection should accept custom query parameter."""
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.query.PYODBC_AVAILABLE", True):
                with patch("agent.query.pyodbc", mock_pyodbc):
                    with patch("agent.query.check_pyodbc_available"):
                        from agent.query import QueryService

                        service = QueryService()
                        service._conn = mock_pyodbc.connect("")

                        # Should succeed with custom query
                        result = service.test_connection(custom_query="SELECT TOP 1 * FROM orders")
                        assert result is True
