"""
GlassTrax API Agent Client

HTTP client for communicating with the GlassTrax API Agent.
Used when running in agent mode (Docker deployment).
"""

import logging
from typing import Any

import httpx

from api.services.agent_schemas import (
    FilterCondition,
    JoinClause,
    OrderBy,
    QueryRequest,
    QueryResponse,
)

logger = logging.getLogger(__name__)


class AgentConnectionError(Exception):
    """Raised when agent is unreachable or returns unexpected response"""

    pass


class AgentAuthError(Exception):
    """Raised when agent authentication fails"""

    pass


class AgentQueryError(Exception):
    """Raised when agent returns a query error"""

    pass


class AgentClient:
    """
    HTTP client for the GlassTrax API Agent.

    Provides methods to execute queries and check health of the agent.
    Uses connection pooling for performance.
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        timeout: int = 30,
    ):
        """
        Initialize the agent client.

        Args:
            url: Agent base URL (e.g., "http://192.168.1.100:8001")
            api_key: Agent API key for authentication
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.url,
                timeout=httpx.Timeout(self.timeout),
                headers={"X-Agent-Key": self.api_key},
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> dict[str, Any]:
        """
        Check agent health.

        Returns:
            Health response dict with status, version, database_connected, etc.

        Raises:
            AgentConnectionError: If agent is unreachable
        """
        try:
            client = await self._get_client()
            response = await client.get("/health")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise AgentConnectionError(f"Cannot connect to agent at {self.url}: {e}")
        except httpx.TimeoutException:
            raise AgentConnectionError(f"Agent request timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            raise AgentConnectionError(f"Agent returned error: {e.response.status_code}")
        except Exception as e:
            raise AgentConnectionError(f"Unexpected error connecting to agent: {e}")

    async def is_healthy(self) -> bool:
        """
        Quick health check - returns True if agent is reachable and healthy.

        Returns:
            True if agent is healthy, False otherwise
        """
        try:
            health = await self.health_check()
            return health.get("status") == "healthy"
        except AgentConnectionError:
            return False

    async def query(self, request: QueryRequest) -> QueryResponse:
        """
        Execute a query via the agent.

        Args:
            request: QueryRequest with table, columns, filters, etc.

        Returns:
            QueryResponse with columns, rows, and status

        Raises:
            AgentConnectionError: If agent is unreachable
            AgentAuthError: If authentication fails
            AgentQueryError: If query execution fails
        """
        try:
            client = await self._get_client()
            response = await client.post(
                "/query",
                json=request.model_dump(exclude_none=True),
            )

            # Check for auth errors
            if response.status_code == 401:
                raise AgentAuthError("Agent authentication failed - check API key")

            response.raise_for_status()

            data = response.json()
            result = QueryResponse.model_validate(data)

            # Check for query-level errors
            if not result.success and result.error:
                raise AgentQueryError(result.error)

            return result

        except httpx.ConnectError as e:
            raise AgentConnectionError(f"Cannot connect to agent at {self.url}: {e}")
        except httpx.TimeoutException:
            raise AgentConnectionError(f"Agent request timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AgentAuthError("Agent authentication failed - check API key")
            raise AgentConnectionError(f"Agent returned error: {e.response.status_code}")
        except (AgentAuthError, AgentQueryError):
            raise
        except Exception as e:
            raise AgentConnectionError(f"Unexpected error: {e}")

    # Convenience methods for common queries

    async def query_table(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[FilterCondition] | None = None,
        joins: list[JoinClause] | None = None,
        order_by: list[OrderBy] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        alias: str | None = None,
    ) -> QueryResponse:
        """
        Convenience method to query a table.

        Args:
            table: Table name
            columns: Columns to select (None = all)
            filters: WHERE conditions
            joins: JOIN clauses
            order_by: ORDER BY clauses
            limit: Max rows to return
            offset: Rows to skip
            alias: Table alias

        Returns:
            QueryResponse with results
        """
        request = QueryRequest(
            table=table,
            alias=alias,
            columns=columns,
            filters=filters or [],
            joins=joins or [],
            order_by=order_by or [],
            limit=limit,
            offset=offset,
        )
        return await self.query(request)

    async def count_table(
        self,
        table: str,
        filters: list[FilterCondition] | None = None,
    ) -> int:
        """
        Count rows in a table.

        Args:
            table: Table name
            filters: WHERE conditions

        Returns:
            Row count
        """
        request = QueryRequest(
            table=table,
            columns=["COUNT(*)"],
            filters=filters or [],
        )
        result = await self.query(request)

        if result.rows and result.rows[0]:
            return int(result.rows[0][0])
        return 0


# Global client instance (set by dependency injection)
_agent_client: AgentClient | None = None


def get_agent_client() -> AgentClient | None:
    """Get the global agent client instance"""
    return _agent_client


def set_agent_client(client: AgentClient | None) -> None:
    """Set the global agent client instance"""
    global _agent_client
    _agent_client = client
