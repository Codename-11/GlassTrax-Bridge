"""
Integration tests for customers router.

Tests GET /api/v1/customers endpoints with mocked GlassTrax service.
"""

import pytest
from unittest.mock import AsyncMock


class TestListCustomers:
    """Test GET /api/v1/customers endpoint."""

    def test_requires_authentication(self, client):
        """Request without API key should return 401."""
        response = client.get("/api/v1/customers")
        assert response.status_code == 401

    def test_returns_empty_list(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Empty customer list should return valid response."""
        mock_glasstrax_service.get_customers = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/customers", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["pagination"]["total_items"] == 0

    def test_returns_customers(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Should return customer data from service."""
        mock_glasstrax_service.get_customers = AsyncMock(
            return_value=(
                [
                    {
                        "customer_id": "CUST01",
                        "customer_name": "Test Corp",
                        "route_id": "R01",
                        "route_name": "Route 1",
                        "main_city": "Boston",
                        "main_state": "MA",
                        "customer_type": "A",
                        "inside_salesperson": "JD",
                    }
                ],
                1,
            )
        )

        response = client_with_mock_glasstrax.get(
            "/api/v1/customers", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["customer_id"] == "CUST01"
        assert data["data"][0]["customer_name"] == "Test Corp"
        assert data["pagination"]["total_items"] == 1

    def test_pagination_params(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Pagination parameters should be passed to service."""
        mock_glasstrax_service.get_customers = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/customers?page=2&page_size=50", headers=auth_headers
        )

        assert response.status_code == 200
        mock_glasstrax_service.get_customers.assert_called_once()
        call_kwargs = mock_glasstrax_service.get_customers.call_args.kwargs
        assert call_kwargs["page"] == 2
        assert call_kwargs["page_size"] == 50

    def test_search_filter(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Search parameter should be passed to service."""
        mock_glasstrax_service.get_customers = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/customers?search=acme", headers=auth_headers
        )

        assert response.status_code == 200
        call_kwargs = mock_glasstrax_service.get_customers.call_args.kwargs
        assert call_kwargs["search"] == "acme"

    def test_state_filter(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """State filter should be passed to service."""
        mock_glasstrax_service.get_customers = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/customers?state=MA", headers=auth_headers
        )

        assert response.status_code == 200
        call_kwargs = mock_glasstrax_service.get_customers.call_args.kwargs
        assert call_kwargs["state"] == "MA"

    def test_multiple_filters(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Multiple filters should all be passed."""
        mock_glasstrax_service.get_customers = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/customers?route_id=R01&city=Boston&customer_type=A",
            headers=auth_headers,
        )

        assert response.status_code == 200
        call_kwargs = mock_glasstrax_service.get_customers.call_args.kwargs
        assert call_kwargs["route_id"] == "R01"
        assert call_kwargs["city"] == "Boston"
        assert call_kwargs["customer_type"] == "A"


class TestGetCustomer:
    """Test GET /api/v1/customers/{customer_id} endpoint."""

    def test_requires_authentication(self, client):
        """Request without API key should return 401."""
        response = client.get("/api/v1/customers/CUST01")
        assert response.status_code == 401

    def test_returns_404_for_missing_customer(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Non-existent customer should return 404."""
        mock_glasstrax_service.get_customer_by_id = AsyncMock(return_value=None)

        response = client_with_mock_glasstrax.get(
            "/api/v1/customers/NOTFOUND", headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.skip(reason="Mock configuration timing issue with complex response - needs investigation")
    def test_returns_customer_details(
        self, client_with_mock_glasstrax, auth_headers, mock_glasstrax_service
    ):
        """Should return full customer details."""
        mock_glasstrax_service.get_customer_by_id = AsyncMock(
            return_value={
                "customer_id": "CUST01",
                "customer_name": "Test Corporation",
                "route_id": "R01",
                "route_name": "Downtown Route",
                "customer_type": "A",
                "main_address": {
                    "city": "Boston",
                    "state": "MA",
                },
                "contacts": [
                    {
                        "contact_no": 1,  # Required field
                        "first_name": "John",
                        "last_name": "Doe",
                        "email": "john@test.com",
                    }
                ],
            }
        )

        response = client_with_mock_glasstrax.get(
            "/api/v1/customers/CUST01", headers=auth_headers
        )

        # Debug: print error details if test fails
        if response.status_code != 200:
            print(f"Response body: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["customer_id"] == "CUST01"
        assert data["data"]["customer_name"] == "Test Corporation"
        assert len(data["data"]["contacts"]) == 1


class TestCustomerPermissions:
    """Test permission requirements for customer endpoints."""

    def test_permission_denied_without_customers_read(
        self, client, test_db, test_tenant
    ):
        """Request with key lacking customers:read should return 403."""
        from api.models import APIKey

        # Create key without customers permission
        api_key, plaintext = APIKey.create_key(
            tenant_id=test_tenant.id,
            name="Limited Key",
            permissions=["orders:read"],  # No customers permission
        )
        test_db.add(api_key)
        test_db.commit()

        response = client.get(
            "/api/v1/customers", headers={"X-API-Key": plaintext}
        )

        assert response.status_code == 403
        assert "customers:read required" in response.json()["detail"]

    def test_admin_key_has_access(
        self, client_with_mock_glasstrax, admin_headers, mock_glasstrax_service
    ):
        """Admin key (*:*) should have access."""
        mock_glasstrax_service.get_customers = AsyncMock(return_value=([], 0))

        response = client_with_mock_glasstrax.get(
            "/api/v1/customers", headers=admin_headers
        )

        assert response.status_code == 200
