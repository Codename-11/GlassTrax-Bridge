"""
Query Execution Service

Builds and executes SQL queries against GlassTrax via ODBC.
"""

import logging
from typing import Any

from agent.config import get_config
from agent.schemas import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

# pyodbc is optional - may need manual installation
try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    pyodbc = None  # type: ignore
    PYODBC_AVAILABLE = False


def check_pyodbc_available() -> None:
    """Raise helpful error if pyodbc is not installed"""
    if not PYODBC_AVAILABLE:
        raise ImportError(
            "pyodbc is not installed. The GlassTrax API Agent requires pyodbc to connect to the database.\n\n"
            "To install pyodbc, open a command prompt and run:\n"
            '  "C:\\Program Files\\GlassTrax API Agent\\python\\python.exe" -m pip install pyodbc\n\n'
            "Note: You also need the Pervasive ODBC driver installed on this system."
        )


class QueryService:
    """
    Executes queries against GlassTrax database.

    Builds parameterized SQL from QueryRequest and returns results as QueryResponse.
    Enforces read-only access and table allowlist.
    """

    def __init__(self):
        self.config = get_config()
        self._conn: Any = None  # pyodbc.Connection or None

    def _get_connection(self) -> Any:
        """Get or create database connection"""
        check_pyodbc_available()
        if self._conn is None:
            readonly_str = "Yes" if self.config.readonly else "No"
            conn_str = f"DSN={self.config.dsn};ReadOnly={readonly_str}"
            self._conn = pyodbc.connect(conn_str, timeout=self.config.timeout)
        return self._conn

    def close(self) -> None:
        """Close the database connection"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass  # Already closed or connection error
            self._conn = None

    def test_connection(self) -> bool:
        """Test if database connection works"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception:
            self._conn = None
            return False

    def _validate_table(self, table: str) -> None:
        """Validate table name against allowlist"""
        allowed = self.config.allowed_tables
        if table.lower() not in [t.lower() for t in allowed]:
            raise ValueError(
                f"Table '{table}' is not in agent's allowed_tables. "
                f"Add '{table}' to agent_config.yaml and restart the agent. "
                f"Current allowed tables: {allowed}"
            )

    def _validate_identifier(self, name: str, allow_expressions: bool = False) -> str:
        """
        Validate and sanitize a SQL identifier or expression.

        For simple identifiers (table/column names): only alphanumeric, underscore, dot.
        For expressions (allow_expressions=True): block SQL injection but allow functions.

        The agent trusts the API Bridge for query construction - this validation
        is just a safety net against obvious injection attempts.
        """
        # Remove surrounding quotes
        name = name.strip('"\'`[]')

        # Block obvious SQL injection attempts (regardless of mode)
        dangerous = [';', '--', '/*', '*/', 'DROP ', 'DELETE ', 'INSERT ', 'UPDATE ', 'TRUNCATE ']
        upper = name.upper()
        for pattern in dangerous:
            if pattern in upper:
                raise ValueError(f"Invalid identifier: {name}")

        # For expressions (SELECT columns), allow more flexibility
        if allow_expressions:
            return name

        # For strict identifiers (table names, etc.), only allow safe chars
        if not all(c.isalnum() or c in ('_', '.') for c in name):
            raise ValueError(f"Invalid identifier: {name}")

        return name

    def _build_select(self, request: QueryRequest) -> str:
        """Build the SELECT clause"""
        if request.columns:
            # Validate each column (allow expressions like COUNT(*), aliases, etc.)
            cols = [self._validate_identifier(c, allow_expressions=True) for c in request.columns]
            return f"SELECT {', '.join(cols)}"
        else:
            # Select all from main table
            alias = request.alias or request.table[0]
            return f"SELECT {alias}.*"

    def _build_from(self, request: QueryRequest) -> str:
        """Build the FROM clause"""
        table = self._validate_identifier(request.table)
        self._validate_table(table)

        if request.alias:
            alias = self._validate_identifier(request.alias)
            return f"FROM {table} {alias}"
        else:
            return f"FROM {table}"

    def _build_joins(self, request: QueryRequest) -> tuple[str, list[Any]]:
        """Build JOIN clauses"""
        if not request.joins:
            return "", []

        join_parts = []
        for join in request.joins:
            table = self._validate_identifier(join.table)
            self._validate_table(table)

            alias = self._validate_identifier(join.alias) if join.alias else ""
            on_left = self._validate_identifier(join.on_left)
            on_right = self._validate_identifier(join.on_right)

            join_str = f"{join.join_type} JOIN {table}"
            if alias:
                join_str += f" {alias}"
            join_str += f" ON {on_left} = {on_right}"

            join_parts.append(join_str)

        return " ".join(join_parts), []

    def _build_where(self, request: QueryRequest) -> tuple[str, list[Any]]:
        """Build WHERE clause with parameters"""
        if not request.filters:
            return "", []

        conditions = []
        params = []

        for f in request.filters:
            col = self._validate_identifier(f.column)

            if f.operator in ("IS NULL", "IS NOT NULL"):
                conditions.append(f"{col} {f.operator}")
            elif f.operator == "IN":
                if not isinstance(f.value, list):
                    raise ValueError("IN operator requires a list value")
                placeholders = ", ".join("?" for _ in f.value)
                conditions.append(f"{col} IN ({placeholders})")
                params.extend(f.value)
            elif f.operator == "NOT IN":
                if not isinstance(f.value, list):
                    raise ValueError("NOT IN operator requires a list value")
                placeholders = ", ".join("?" for _ in f.value)
                conditions.append(f"{col} NOT IN ({placeholders})")
                params.extend(f.value)
            else:
                conditions.append(f"{col} {f.operator} ?")
                params.append(f.value)

        return "WHERE " + " AND ".join(conditions), params

    def _build_order_by(self, request: QueryRequest) -> str:
        """Build ORDER BY clause"""
        if not request.order_by:
            return ""

        parts = []
        for o in request.order_by:
            col = self._validate_identifier(o.column)
            parts.append(f"{col} {o.direction}")

        return "ORDER BY " + ", ".join(parts)

    def _build_query(self, request: QueryRequest) -> tuple[str, list[Any]]:
        """
        Build complete SQL query from request.

        Pervasive SQL uses TOP for limiting rows but doesn't support OFFSET.
        We fetch extra rows and slice in Python for pagination.
        """
        select = self._build_select(request)
        from_clause = self._build_from(request)
        joins, join_params = self._build_joins(request)
        where, where_params = self._build_where(request)
        order_by = self._build_order_by(request)

        # Handle pagination - Pervasive uses TOP without OFFSET
        # We fetch limit + offset rows and slice in Python
        if request.limit:
            fetch_count = request.limit + (request.offset or 0)
            select = select.replace("SELECT", f"SELECT TOP {fetch_count}", 1)

        # Combine parts
        parts = [select, from_clause]
        if joins:
            parts.append(joins)
        if where:
            parts.append(where)
        if order_by:
            parts.append(order_by)

        sql = " ".join(parts)
        params = join_params + where_params

        return sql, params

    def execute(self, request: QueryRequest) -> QueryResponse:
        """
        Execute a query request and return results.

        Args:
            request: QueryRequest with table, columns, filters, etc.

        Returns:
            QueryResponse with columns, rows, and status
        """
        try:
            # Build and execute query
            sql, params = self._build_query(request)
            logger.debug(f"Executing query: {sql} with params: {params}")

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)

            # Get column names
            columns = [col[0] for col in cursor.description] if cursor.description else []

            # Fetch all rows
            rows = cursor.fetchall()
            cursor.close()

            # Convert rows to lists and handle pagination offset
            result_rows = []
            offset = request.offset or 0

            for i, row in enumerate(rows):
                if i < offset:
                    continue
                # Convert row to list, handling special types
                result_rows.append([self._convert_value(v) for v in row])

            logger.debug(f"Query returned {len(result_rows)} rows")
            return QueryResponse(
                success=True,
                columns=columns,
                rows=result_rows,
                row_count=len(result_rows),
            )

        except ValueError as e:
            # Validation errors (bad table/column names)
            logger.warning(f"Query validation error: {e}")
            return QueryResponse(success=False, error=str(e))
        except Exception as e:
            # Check if this is a pyodbc error (pyodbc may be None in tests/CI)
            is_pyodbc_error = (
                pyodbc is not None
                and hasattr(pyodbc, 'Error')
                and isinstance(e, pyodbc.Error)
            )
            if is_pyodbc_error:
                # Database errors
                self._conn = None  # Reset connection on error
                error_msg = str(e)
                if hasattr(e, 'args') and len(e.args) > 1:
                    error_msg = e.args[1]
                logger.error(f"Database error: {error_msg}")
                return QueryResponse(success=False, error=f"Database error: {error_msg}")
            else:
                # Unexpected errors
                logger.exception(f"Unexpected error executing query: {e}")
                return QueryResponse(success=False, error=f"Unexpected error: {e!s}")

    def _convert_value(self, value: Any) -> Any:
        """Convert database values to JSON-serializable types"""
        if value is None:
            return None
        if isinstance(value, bytes):
            # Try to decode as string, otherwise return as hex
            try:
                return value.decode('utf-8').strip()
            except UnicodeDecodeError:
                return value.hex()
        if isinstance(value, str):
            stripped = value.strip()
            # Try to convert numeric strings to proper types
            # This handles Pervasive returning numbers as strings
            if stripped:
                # Check for integer (including negative)
                if stripped.lstrip('-').isdigit():
                    try:
                        return int(stripped)
                    except ValueError:
                        pass
                # Check for float/decimal (including negative, with decimal point)
                if stripped.replace('.', '', 1).replace('-', '', 1).isdigit():
                    try:
                        return float(stripped)
                    except ValueError:
                        pass
            return stripped
        # Let other types pass through (int, float, bool, date, datetime)
        return value


# Global service instance
_service: QueryService | None = None


def get_query_service() -> QueryService:
    """Get the global query service instance"""
    global _service
    if _service is None:
        _service = QueryService()
    return _service
