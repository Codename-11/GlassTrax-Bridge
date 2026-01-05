"""
Unit tests for agent authentication.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException


class TestVerifyAgentKey:
    """Test agent API key verification."""

    @pytest.mark.asyncio
    async def test_missing_key_raises_401(self):
        """Missing API key should raise 401."""
        from agent.auth import verify_agent_key

        with pytest.raises(HTTPException) as exc_info:
            await verify_agent_key(None)

        assert exc_info.value.status_code == 401
        assert "Missing API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_key_raises_401(self, mock_config):
        """Invalid API key should raise 401."""
        mock_config.verify_api_key = MagicMock(return_value=False)

        with patch("agent.auth.get_config", return_value=mock_config):
            from agent.auth import verify_agent_key

            with pytest.raises(HTTPException) as exc_info:
                await verify_agent_key("gta_invalid_key")

            assert exc_info.value.status_code == 401
            assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_valid_key_returns_key(self, mock_config):
        """Valid API key should return the key."""
        mock_config.verify_api_key = MagicMock(return_value=True)

        with patch("agent.auth.get_config", return_value=mock_config):
            from agent.auth import verify_agent_key

            result = await verify_agent_key("gta_valid_key")

            assert result == "gta_valid_key"
            mock_config.verify_api_key.assert_called_once_with("gta_valid_key")
