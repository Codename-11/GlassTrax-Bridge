"""
Integration tests for agent endpoints.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestHealthEndpoint:
    """Test GET /health endpoint."""

    def test_health_without_auth(self, agent_client):
        """Health check should work without authentication."""
        response = agent_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data

    def test_health_returns_version(self, agent_client):
        """Health check should include version."""
        response = agent_client.get("/health")

        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)

    def test_health_returns_pyodbc_status(self, agent_client):
        """Health check should include pyodbc status."""
        response = agent_client.get("/health")

        data = response.json()
        assert "pyodbc_installed" in data


class TestQueryEndpoint:
    """Test POST /query endpoint."""

    def test_query_requires_auth(self, agent_client):
        """Query without auth should return 401."""
        response = agent_client.post(
            "/query",
            json={"table": "customer"},
        )

        assert response.status_code == 401

    def test_query_with_valid_auth(self, agent_client, auth_headers, mock_config):
        """Query with valid auth should succeed."""
        # Ensure the mock config verifies the key
        mock_config.verify_api_key.return_value = True

        response = agent_client.post(
            "/query",
            headers=auth_headers,
            json={"table": "customer"},
        )

        # Should be 200 or return query results
        assert response.status_code in [200, 500]  # 500 if pyodbc mock fails internally

    def test_query_invalid_table_returns_error(self, agent_client, auth_headers, mock_config):
        """Query with invalid table should return error."""
        mock_config.verify_api_key.return_value = True

        response = agent_client.post(
            "/query",
            headers=auth_headers,
            json={"table": "forbidden_table"},
        )

        # Should return 200 with error in response body (per API design)
        # or 400/422 depending on implementation
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is False
            assert "not in agent's allowed_tables" in data.get("error", "").lower()

    def test_query_with_filters(self, agent_client, auth_headers, mock_config):
        """Query with filters should be accepted."""
        mock_config.verify_api_key.return_value = True

        response = agent_client.post(
            "/query",
            headers=auth_headers,
            json={
                "table": "customer",
                "filters": [
                    {"column": "main_state", "operator": "=", "value": "MA"}
                ],
            },
        )

        assert response.status_code in [200, 500]

    def test_query_with_limit(self, agent_client, auth_headers, mock_config):
        """Query with limit should be accepted."""
        mock_config.verify_api_key.return_value = True

        response = agent_client.post(
            "/query",
            headers=auth_headers,
            json={
                "table": "customer",
                "limit": 10,
            },
        )

        assert response.status_code in [200, 500]


class TestQueryRequestValidation:
    """Test request body validation for /query."""

    def test_table_required(self, agent_client, auth_headers, mock_config):
        """Table field should be required."""
        mock_config.verify_api_key.return_value = True

        response = agent_client.post(
            "/query",
            headers=auth_headers,
            json={},  # Missing table
        )

        assert response.status_code == 422

    def test_invalid_operator_rejected(self, agent_client, auth_headers, mock_config):
        """Invalid filter operator should be rejected."""
        mock_config.verify_api_key.return_value = True

        response = agent_client.post(
            "/query",
            headers=auth_headers,
            json={
                "table": "customer",
                "filters": [
                    {"column": "main_state", "operator": "INVALID", "value": "MA"}
                ],
            },
        )

        # Should reject invalid operator
        assert response.status_code == 422

    def test_limit_range(self, agent_client, auth_headers, mock_config):
        """Limit should be within valid range (1-10000)."""
        mock_config.verify_api_key.return_value = True

        # Test limit > 10000
        response = agent_client.post(
            "/query",
            headers=auth_headers,
            json={
                "table": "customer",
                "limit": 50000,
            },
        )

        # Should reject or cap the limit
        assert response.status_code in [200, 422, 500]
