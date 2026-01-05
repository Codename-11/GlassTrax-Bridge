"""
Unit tests for GlassTraxService.

Tests date parsing utilities and service mode detection.
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, AsyncMock, patch

from api.services.glasstrax import (
    GlassTraxService,
    parse_glasstrax_date,
    format_date_for_query,
    PYODBC_AVAILABLE,
)


class TestDateParsing:
    """Test GlassTrax date parsing utilities."""

    def test_parse_valid_date(self):
        """Parse a standard YYYYMMDD date string."""
        result = parse_glasstrax_date("20240115")
        assert result == date(2024, 1, 15)

    def test_parse_date_first_of_month(self):
        """Parse date at the start of a month."""
        result = parse_glasstrax_date("20241001")
        assert result == date(2024, 10, 1)

    def test_parse_date_end_of_year(self):
        """Parse date at year end."""
        result = parse_glasstrax_date("20241231")
        assert result == date(2024, 12, 31)

    def test_parse_null_date_returns_none(self):
        """GlassTrax null date (18991230) should return None."""
        result = parse_glasstrax_date("18991230")
        assert result is None

    def test_parse_empty_string_returns_none(self):
        """Empty string should return None."""
        result = parse_glasstrax_date("")
        assert result is None

    def test_parse_none_returns_none(self):
        """None input should return None."""
        result = parse_glasstrax_date(None)
        assert result is None

    def test_parse_short_string_returns_none(self):
        """String shorter than 8 chars should return None."""
        result = parse_glasstrax_date("2024011")
        assert result is None

    def test_parse_invalid_date_returns_none(self):
        """Invalid date (e.g., month 13) should return None."""
        result = parse_glasstrax_date("20241332")
        assert result is None

    def test_parse_non_numeric_returns_none(self):
        """Non-numeric string should return None."""
        result = parse_glasstrax_date("ABCDEFGH")
        assert result is None


class TestDateFormatting:
    """Test date formatting for GlassTrax queries."""

    def test_format_standard_date(self):
        """Format a standard date to YYYYMMDD."""
        result = format_date_for_query(date(2024, 1, 15))
        assert result == "20240115"

    def test_format_single_digit_month_day(self):
        """Format date with single-digit month and day (should be zero-padded)."""
        result = format_date_for_query(date(2024, 3, 5))
        assert result == "20240305"

    def test_format_none_returns_none(self):
        """None date should return None."""
        result = format_date_for_query(None)
        assert result is None


class TestGlassTraxServiceModes:
    """Test GlassTraxService mode detection."""

    def test_is_agent_mode_false_by_default(self):
        """Service without agent_client should not be in agent mode."""
        service = GlassTraxService(dsn="TEST")
        assert service.is_agent_mode is False

    def test_is_agent_mode_true_with_client(self):
        """Service with agent_client should be in agent mode."""
        mock_client = MagicMock()
        service = GlassTraxService(agent_client=mock_client)
        assert service.is_agent_mode is True

    def test_dsn_stored(self):
        """DSN should be stored on service."""
        service = GlassTraxService(dsn="PRODUCTION")
        assert service.dsn == "PRODUCTION"

    def test_readonly_default_true(self):
        """Readonly should default to True."""
        service = GlassTraxService(dsn="TEST")
        assert service.readonly is True

    def test_readonly_can_be_false(self):
        """Readonly can be set to False."""
        service = GlassTraxService(dsn="TEST", readonly=False)
        assert service.readonly is False


class TestGlassTraxServiceAgentMode:
    """Test GlassTraxService agent mode operations."""

    @pytest.fixture
    def mock_agent_client(self):
        """Create a mock agent client."""
        mock = MagicMock()
        mock.is_healthy = AsyncMock(return_value=True)
        mock.health_check = AsyncMock(return_value={"status": "healthy"})
        mock.query_table = AsyncMock()
        mock.count_table = AsyncMock(return_value=0)
        mock.close = AsyncMock()
        return mock

    @pytest.fixture
    def service_with_agent(self, mock_agent_client):
        """Create service in agent mode."""
        return GlassTraxService(agent_client=mock_agent_client)

    def test_agent_mode_enabled(self, service_with_agent):
        """Verify agent mode is detected."""
        assert service_with_agent.is_agent_mode is True

    def test_get_connection_raises_in_agent_mode(self, service_with_agent):
        """_get_connection should raise in agent mode."""
        with pytest.raises(RuntimeError, match="Cannot get direct connection in agent mode"):
            service_with_agent._get_connection()

    @pytest.mark.asyncio
    async def test_test_connection_calls_agent(self, service_with_agent, mock_agent_client):
        """test_connection should call agent's is_healthy."""
        result = await service_with_agent.test_connection()
        assert result is True
        mock_agent_client.is_healthy.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_customers_calls_agent(self, service_with_agent, mock_agent_client):
        """get_customers should call agent in agent mode."""
        # Setup mock response
        mock_result = MagicMock()
        mock_result.columns = ["customer_id", "customer_name"]
        mock_result.rows = [["C001", "Test Corp"]]
        mock_agent_client.query_table.return_value = mock_result

        customers, total = await service_with_agent.get_customers()

        mock_agent_client.query_table.assert_called_once()
        mock_agent_client.count_table.assert_called_once()


class TestGlassTraxServiceDirectMode:
    """Test GlassTraxService direct ODBC mode."""

    def test_pyodbc_availability_detected(self):
        """PYODBC_AVAILABLE should be boolean."""
        assert isinstance(PYODBC_AVAILABLE, bool)

    @patch("api.services.glasstrax.PYODBC_AVAILABLE", False)
    def test_get_connection_raises_without_pyodbc(self):
        """_get_connection should raise when pyodbc unavailable."""
        service = GlassTraxService(dsn="TEST")
        with pytest.raises(RuntimeError, match="pyodbc not available"):
            service._get_connection()

    def test_close_handles_no_connection(self):
        """close() should work even without active connection."""
        service = GlassTraxService(dsn="TEST")
        service.close()  # Should not raise

    def test_context_manager_closes(self):
        """Context manager should call close on exit."""
        service = GlassTraxService(dsn="TEST")
        with service as s:
            assert s is service
        # No error means close was called


class TestBuildCustomerResponse:
    """Test customer response building."""

    def test_build_customer_response_basic(self):
        """Build response from minimal customer data."""
        service = GlassTraxService(dsn="TEST")

        customer = {
            "customer_id": "  CUST01  ",
            "customer_name": "  Test Company  ",
            "route_id": "R01",
            "route_name": "Route 1",
            "customer_type": "A",
        }
        contacts = []

        result = service._build_customer_response(customer, contacts)

        assert result["customer_id"] == "CUST01"
        assert result["customer_name"] == "Test Company"
        assert result["route_id"] == "R01"
        assert result["contacts"] == []

    def test_build_customer_response_with_contacts(self):
        """Build response including contacts."""
        service = GlassTraxService(dsn="TEST")

        customer = {"customer_id": "CUST01", "customer_name": "Test"}
        contacts = [
            {
                "contact_no": "1",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@test.com",
            }
        ]

        result = service._build_customer_response(customer, contacts)

        assert len(result["contacts"]) == 1
        assert result["contacts"][0]["first_name"] == "John"

    def test_build_customer_response_handles_none_values(self):
        """Build response with None values."""
        service = GlassTraxService(dsn="TEST")

        customer = {
            "customer_id": "CUST01",
            "customer_name": None,
            "route_id": None,
        }
        contacts = []

        result = service._build_customer_response(customer, contacts)

        assert result["customer_id"] == "CUST01"
        assert result["customer_name"] is None
        assert result["route_id"] is None


class TestBuildOrderResponse:
    """Test order response building."""

    def test_build_order_response_basic(self):
        """Build response from minimal order data."""
        service = GlassTraxService(dsn="TEST")

        header = {
            "so_no": 12345,
            "customer_id": "  CUST01  ",
            "customer_name": "Test Company",
            "order_date": "20240115",
            "open_closed_flag": "O",
        }
        line_items = []

        result = service._build_order_response(header, line_items)

        assert result["so_no"] == 12345
        assert result["customer_id"] == "CUST01"
        assert result["order_date"] == date(2024, 1, 15)
        assert result["status"] == "Open"
        assert result["line_items"] == []
        assert result["total_lines"] == 0

    def test_build_order_response_closed_status(self):
        """Build response for closed order."""
        service = GlassTraxService(dsn="TEST")

        header = {
            "so_no": 12345,
            "customer_id": "CUST01",
            "open_closed_flag": "C",
        }
        line_items = []

        result = service._build_order_response(header, line_items)

        assert result["status"] == "Closed"

    def test_build_order_response_calculates_totals(self):
        """Build response with line item totals."""
        service = GlassTraxService(dsn="TEST")

        header = {
            "so_no": 12345,
            "customer_id": "CUST01",
        }
        line_items = [
            {"so_line_no": 1, "order_qty": 10, "total_extended_price": 100.00},
            {"so_line_no": 2, "order_qty": 5, "total_extended_price": 75.50},
        ]

        result = service._build_order_response(header, line_items)

        assert result["total_lines"] == 2
        assert result["total_qty"] == 15
        assert result["total_amount"] == 175.50
