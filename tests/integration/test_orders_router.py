"""
Integration tests for orders router.

Tests GET /api/v1/orders endpoints with mocked GlassTrax service.
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock


class TestListOrders:
    """Test GET /api/v1/orders endpoint."""

    def test_requires_authentication(self, client):
        """Request without API key should return 401."""
        response = client.get("/api/v1/orders")
        assert response.status_code == 401

    def test_returns_empty_list(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Empty order list should return valid response."""
        mock_glasstrax_service.get_orders = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/orders", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["pagination"]["total_items"] == 0

    def test_returns_orders(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Should return order data from service."""
        mock_glasstrax_service.get_orders = AsyncMock(
            return_value=(
                [
                    {
                        "so_no": 12345,
                        "customer_id": "CUST01",
                        "customer_name": "Test Corp",
                        "order_date": date(2024, 1, 15),
                        "status": "Open",
                        "job_name": "Test Job",
                    }
                ],
                1,
            )
        )

        response = client_with_mock_glasstrax.get(
            "/api/v1/orders", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["so_no"] == 12345
        assert data["data"][0]["customer_id"] == "CUST01"

    def test_pagination_params(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Pagination parameters should be passed to service."""
        mock_glasstrax_service.get_orders = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/orders?page=3&page_size=25", headers=auth_headers
        )

        assert response.status_code == 200
        call_kwargs = mock_glasstrax_service.get_orders.call_args.kwargs
        assert call_kwargs["page"] == 3
        assert call_kwargs["page_size"] == 25

    def test_customer_filter(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Customer filter should be passed to service."""
        mock_glasstrax_service.get_orders = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/orders?customer_id=CUST01", headers=auth_headers
        )

        assert response.status_code == 200
        call_kwargs = mock_glasstrax_service.get_orders.call_args.kwargs
        assert call_kwargs["customer_id"] == "CUST01"

    def test_status_filter(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Status filter should be passed to service."""
        mock_glasstrax_service.get_orders = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/orders?status=O", headers=auth_headers
        )

        assert response.status_code == 200
        call_kwargs = mock_glasstrax_service.get_orders.call_args.kwargs
        assert call_kwargs["status"] == "O"

    def test_date_filters(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Date filters should be passed to service."""
        mock_glasstrax_service.get_orders = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/orders?date_from=2024-01-01&date_to=2024-01-31",
            headers=auth_headers,
        )

        assert response.status_code == 200
        call_kwargs = mock_glasstrax_service.get_orders.call_args.kwargs
        assert call_kwargs["date_from"] == date(2024, 1, 1)
        assert call_kwargs["date_to"] == date(2024, 1, 31)

    def test_search_filter(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Search parameter should be passed to service."""
        mock_glasstrax_service.get_orders = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/orders?search=test", headers=auth_headers
        )

        assert response.status_code == 200
        call_kwargs = mock_glasstrax_service.get_orders.call_args.kwargs
        assert call_kwargs["search"] == "test"


class TestGetOrder:
    """Test GET /api/v1/orders/{so_no} endpoint."""

    def test_requires_authentication(self, client):
        """Request without API key should return 401."""
        response = client.get("/api/v1/orders/12345")
        assert response.status_code == 401

    def test_returns_404_for_missing_order(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Non-existent order should return 404."""
        mock_glasstrax_service.get_order_by_number = AsyncMock(return_value=None)

        response = client_with_mock_glasstrax.get(
            "/api/v1/orders/99999", headers=auth_headers
        )

        assert response.status_code == 404

    def test_returns_order_details(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Should return full order details with line items."""
        mock_glasstrax_service.get_order_by_number = AsyncMock(
            return_value={
                "so_no": 12345,
                "customer_id": "CUST01",
                "customer_name": "Test Corporation",
                "order_date": date(2024, 1, 15),
                "status": "Open",
                "job_name": "Big Project",
                "line_items": [
                    {
                        "so_line_no": 1,
                        "item_id": "GLASS01",
                        "item_description": "Tempered Glass",
                        "order_qty": 10,
                        "unit_price": 50.00,
                    }
                ],
                "total_lines": 1,
                "total_qty": 10,
                "total_amount": 500.00,
            }
        )

        response = client_with_mock_glasstrax.get(
            "/api/v1/orders/12345", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["so_no"] == 12345
        assert data["data"]["customer_name"] == "Test Corporation"
        assert data["data"]["total_lines"] == 1
        assert len(data["data"]["line_items"]) == 1


class TestOrderPermissions:
    """Test permission requirements for order endpoints."""

    def test_permission_denied_without_orders_read(self, client, test_db, test_tenant):
        """Request with key lacking orders:read should return 403."""
        from api.models import APIKey

        # Create key without orders permission
        api_key, plaintext = APIKey.create_key(
            tenant_id=test_tenant.id,
            name="Limited Key",
            permissions=["customers:read"],  # No orders permission
        )
        test_db.add(api_key)
        test_db.commit()

        response = client.get("/api/v1/orders", headers={"X-API-Key": plaintext})

        assert response.status_code == 403
        assert "orders:read required" in response.json()["detail"]
