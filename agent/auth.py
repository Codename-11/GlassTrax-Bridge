"""
Agent Authentication

Simple API key authentication for the agent.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from agent.config import get_config

# API key header
api_key_header = APIKeyHeader(name="X-Agent-Key", auto_error=False)


async def verify_agent_key(api_key: str | None = Security(api_key_header)) -> str:
    """
    Verify the agent API key from request header.

    Args:
        api_key: API key from X-Agent-Key header

    Returns:
        The verified API key

    Raises:
        HTTPException: If key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-Agent-Key header.",
        )

    config = get_config()
    if not config.verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key


# Dependency for protected endpoints
require_auth = Depends(verify_agent_key)
