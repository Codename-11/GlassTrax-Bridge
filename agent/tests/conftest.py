"""
Pytest fixtures for agent tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agent.tests.mocks.mock_pyodbc import create_mock_pyodbc


@pytest.fixture
def mock_config():
    """Mock agent configuration."""
    config = MagicMock()
    config.dsn = "TEST"
    config.readonly = True
    config.timeout = 30
    config.port = 8001
    config.test_query = "SELECT 1"
    config.allowed_tables = [
        "customer",
        "customer_contacts",
        "delivery_routes",
        "sales_orders_headers",
        "sales_order_detail",
    ]
    config.verify_api_key = MagicMock(return_value=True)
    # Support get() method for accessing nested config values
    config.get = MagicMock(side_effect=lambda key, default=None: {
        "agent.test_query": "SELECT 1",
    }.get(key, default))
    return config


@pytest.fixture
def mock_pyodbc():
    """Create mock pyodbc module with sample data."""
    return create_mock_pyodbc(
        data=[
            ("CUST01", "Test Customer", "R01"),
        ],
        columns=["customer_id", "customer_name", "route_id"],
    )


@pytest.fixture
def valid_agent_key():
    """Valid agent API key for tests."""
    return "gta_test_key_valid_12345"


@pytest.fixture
def agent_client(mock_config, mock_pyodbc, valid_agent_key):
    """
    FastAPI test client for agent with mocked dependencies.

    Sets up:
    - Mock pyodbc module
    - Mock config with valid API key verification
    """
    with patch.dict("sys.modules", {"pyodbc": mock_pyodbc}):
        with patch("agent.config.get_config", return_value=mock_config):
            with patch("agent.auth.get_config", return_value=mock_config):
                with patch("agent.query.PYODBC_AVAILABLE", True):
                    with patch("agent.query.pyodbc", mock_pyodbc):
                        # Import after patching
                        from agent.main import app

                        with TestClient(app) as client:
                            yield client


@pytest.fixture
def auth_headers(valid_agent_key):
    """Headers with valid agent API key."""
    return {"X-Agent-Key": valid_agent_key}
