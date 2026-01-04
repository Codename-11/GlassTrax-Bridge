### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - FastAPI Dependencies -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
FastAPI Dependencies

Provides dependency injection for:
- GlassTrax database service (direct ODBC or via agent)
- Configuration settings
"""

from typing import Generator

from api.services.glasstrax import GlassTraxService
from api.services.config_service import get_config_service


# Service instances (created on first request, reused)
_glasstrax_service: GlassTraxService | None = None
_agent_client = None  # AgentClient when in agent mode


def get_glasstrax_service() -> Generator[GlassTraxService, None, None]:
    """
    Dependency that provides GlassTrax database service.

    Uses a singleton pattern to maintain connection across requests.
    Connection is established on first use.

    Supports two modes based on config.yaml:
    1. Agent Mode (agent.enabled=true): Uses AgentClient to communicate
       with GlassTrax Agent on Windows
    2. Direct Mode (agent.enabled=false): Uses pyodbc for direct ODBC access
       (requires Windows with 32-bit Python)

    Yields:
        GlassTraxService instance
    """
    global _glasstrax_service, _agent_client

    if _glasstrax_service is None:
        config = get_config_service()

        # Check if agent mode is enabled
        agent_enabled = config.get("agent.enabled", False)

        if agent_enabled:
            # Agent mode: create AgentClient and pass to service
            from api.services.agent_client import AgentClient

            agent_url = config.get("agent.url", "http://localhost:8001")
            agent_key = config.get("agent.api_key", "")
            agent_timeout = config.get("agent.timeout", 30)

            _agent_client = AgentClient(
                url=agent_url,
                api_key=agent_key,
                timeout=agent_timeout,
            )

            _glasstrax_service = GlassTraxService(agent_client=_agent_client)
        else:
            # Direct mode: use pyodbc
            dsn = config.get("database.dsn", "LIVE")
            readonly = config.get("database.readonly", True)
            _glasstrax_service = GlassTraxService(dsn=dsn, readonly=readonly)

    yield _glasstrax_service


async def close_glasstrax_service():
    """Close the GlassTrax service connection (call on shutdown)"""
    global _glasstrax_service, _agent_client

    if _glasstrax_service is not None:
        _glasstrax_service.close()
        _glasstrax_service = None

    if _agent_client is not None:
        await _agent_client.close()
        _agent_client = None


def reset_glasstrax_service():
    """
    Reset the GlassTrax service (forces recreation on next request).

    Call this when config changes require a new service instance.
    """
    global _glasstrax_service, _agent_client

    if _glasstrax_service is not None:
        _glasstrax_service.close()
        _glasstrax_service = None

    # Note: Agent client is closed synchronously here
    # In async context, use close_glasstrax_service instead
    _agent_client = None


def is_agent_mode() -> bool:
    """Check if running in agent mode"""
    config = get_config_service()
    return config.get("agent.enabled", False)
