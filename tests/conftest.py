"""
Shared pytest fixtures for GlassTrax-Bridge API tests.

Provides:
- Isolated in-memory SQLite database per test
- FastAPI TestClient with dependency overrides
- Authentication fixtures (tenants, API keys)
- GlassTrax service mocking
"""

import pytest
from typing import Generator
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from api.database import Base, get_db
from api.main import app
from api.models import Tenant, APIKey
from api.dependencies import get_glasstrax_service

from tests.fixtures.factories import (
    create_tenant,
    create_api_key,
    create_admin_api_key,
)
from tests.mocks.mock_agent_client import create_mock_agent_client


# ============================================
# Database Fixtures
# ============================================


@pytest.fixture(scope="function")
def test_engine(tmp_path):
    """
    Create an isolated SQLite database engine for each test.

    Uses a file-based database in tmp_path to avoid connection isolation
    issues with in-memory SQLite.
    """
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    return engine


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """
    Create database tables and provide a session.

    Yields a Session that is isolated to this test.
    Tables are created before and dropped after.
    """
    # Import all models to ensure they're registered with Base.metadata
    # This is necessary because we use a separate test engine
    from api.models import api_key, tenant, access_log  # noqa: F401

    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    TestingSessionLocal = sessionmaker(bind=test_engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient with database dependency overridden.

    Uses the test_db session instead of the production database.
    """

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================
# Authentication Fixtures
# ============================================


@pytest.fixture
def test_tenant(test_db: Session) -> Tenant:
    """Create a test tenant for authentication testing."""
    return create_tenant(
        db=test_db,
        name="Test Tenant",
        description="Automated test tenant",
        contact_email="test@example.com",
    )


@pytest.fixture
def test_api_key(test_db: Session, test_tenant: Tenant) -> tuple[APIKey, str]:
    """
    Create a test API key with standard permissions.

    Returns:
        Tuple of (APIKey model, plaintext key string)
    """
    return create_api_key(
        db=test_db,
        tenant=test_tenant,
        name="Test API Key",
        permissions=["customers:read", "orders:read"],
    )


@pytest.fixture
def admin_api_key(test_db: Session, test_tenant: Tenant) -> tuple[APIKey, str]:
    """
    Create an admin API key with full permissions.

    Returns:
        Tuple of (APIKey model, plaintext key string)
    """
    return create_admin_api_key(
        db=test_db,
        tenant=test_tenant,
        name="Admin API Key",
    )


@pytest.fixture
def auth_headers(test_api_key: tuple[APIKey, str]) -> dict[str, str]:
    """
    HTTP headers with valid API key for authenticated requests.

    Usage:
        def test_endpoint(client, auth_headers):
            response = client.get("/api/v1/customers", headers=auth_headers)
    """
    _, plaintext_key = test_api_key
    return {"X-API-Key": plaintext_key}


@pytest.fixture
def admin_headers(admin_api_key: tuple[APIKey, str]) -> dict[str, str]:
    """
    HTTP headers with admin API key for admin-only requests.
    """
    _, plaintext_key = admin_api_key
    return {"X-API-Key": plaintext_key}


# ============================================
# GlassTrax Service Mocking
# ============================================


@pytest.fixture
def mock_glasstrax_service():
    """
    Create a mock GlassTraxService for isolated router tests.

    Configure return values in your test:
        mock_glasstrax_service.get_customers = AsyncMock(return_value=([...], 10))
    """
    mock_service = MagicMock()

    # Default return values for common methods
    mock_service.get_customers = AsyncMock(return_value=([], 0))
    mock_service.get_customer_by_id = AsyncMock(return_value=None)
    mock_service.get_orders = AsyncMock(return_value=([], 0))
    mock_service.get_order_by_number = AsyncMock(return_value=None)
    mock_service.test_connection = AsyncMock(return_value=True)
    mock_service.close = MagicMock()

    # Mode indicators
    mock_service.is_agent_mode = False
    mock_service.is_connected = True

    return mock_service


@pytest.fixture
def mock_agent_client():
    """
    Create a mock AgentClient for testing agent mode.

    Uses the full mock from tests.mocks.mock_agent_client.
    """
    return create_mock_agent_client()


@pytest.fixture
def client_with_mock_glasstrax(
    test_db: Session,
    mock_glasstrax_service,
) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient with both database and GlassTrax service mocked.

    Use this for testing routes that interact with GlassTrax data.
    """

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    def override_glasstrax():
        yield mock_glasstrax_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_glasstrax_service] = override_glasstrax

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================
# Convenience Fixtures
# ============================================


@pytest.fixture
def sample_customers():
    """Return sample customer data for tests."""
    from tests.fixtures.data import SAMPLE_CUSTOMERS

    return SAMPLE_CUSTOMERS.copy()


@pytest.fixture
def sample_orders():
    """Return sample order data for tests."""
    from tests.fixtures.data import SAMPLE_ORDERS

    return SAMPLE_ORDERS.copy()
