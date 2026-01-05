"""
Integration tests for admin tenants router.

Tests tenant CRUD operations at /api/v1/admin/tenants.
"""

import pytest
from api.models import Tenant


class TestListTenants:
    """Test GET /api/v1/admin/tenants endpoint."""

    def test_requires_admin_permission(self, client, auth_headers):
        """Regular API key should be denied."""
        response = client.get("/api/v1/admin/tenants", headers=auth_headers)
        assert response.status_code == 403

    def test_returns_tenants(self, client, admin_headers, test_tenant):
        """Should return list of tenants."""
        response = client.get("/api/v1/admin/tenants", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1

        # Find test tenant in results
        tenant_names = [t["name"] for t in data["data"]]
        assert test_tenant.name in tenant_names

    def test_pagination(self, client, admin_headers, test_db):
        """Should support pagination."""
        # Create multiple tenants
        for i in range(5):
            tenant = Tenant(
                name=f"Paginated Tenant {i}",
                description=f"Test {i}",
                is_active=True,
            )
            test_db.add(tenant)
        test_db.commit()

        response = client.get(
            "/api/v1/admin/tenants?page=1&page_size=3", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["page_size"] == 3


class TestCreateTenant:
    """Test POST /api/v1/admin/tenants endpoint."""

    def test_requires_admin_permission(self, client, auth_headers):
        """Regular API key should be denied."""
        response = client.post(
            "/api/v1/admin/tenants",
            headers=auth_headers,
            json={"name": "New Tenant"},
        )
        assert response.status_code == 403

    def test_creates_tenant(self, client, admin_headers):
        """Should create a new tenant."""
        response = client.post(
            "/api/v1/admin/tenants",
            headers=admin_headers,
            json={
                "name": "New Test Tenant",
                "description": "Created via API",
                "contact_email": "new@test.com",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "New Test Tenant"
        assert data["data"]["contact_email"] == "new@test.com"
        assert data["data"]["is_active"] is True

    def test_requires_name(self, client, admin_headers):
        """Name should be required."""
        response = client.post(
            "/api/v1/admin/tenants",
            headers=admin_headers,
            json={"description": "No name"},
        )

        assert response.status_code == 422

    def test_name_must_be_unique(self, client, admin_headers, test_tenant):
        """Duplicate name should fail."""
        response = client.post(
            "/api/v1/admin/tenants",
            headers=admin_headers,
            json={"name": test_tenant.name},  # Already exists
        )

        # 409 Conflict for duplicate name
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()


class TestGetTenant:
    """Test GET /api/v1/admin/tenants/{tenant_id} endpoint."""

    def test_requires_admin_permission(self, client, auth_headers, test_tenant):
        """Regular API key should be denied."""
        response = client.get(
            f"/api/v1/admin/tenants/{test_tenant.id}", headers=auth_headers
        )
        assert response.status_code == 403

    def test_returns_tenant(self, client, admin_headers, test_tenant):
        """Should return tenant details."""
        response = client.get(
            f"/api/v1/admin/tenants/{test_tenant.id}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == test_tenant.id
        assert data["data"]["name"] == test_tenant.name

    def test_returns_404_for_missing(self, client, admin_headers):
        """Non-existent tenant should return 404."""
        response = client.get(
            "/api/v1/admin/tenants/99999", headers=admin_headers
        )

        assert response.status_code == 404


class TestUpdateTenant:
    """Test PATCH /api/v1/admin/tenants/{tenant_id} endpoint."""

    def test_requires_admin_permission(self, client, auth_headers, test_tenant):
        """Regular API key should be denied."""
        response = client.patch(
            f"/api/v1/admin/tenants/{test_tenant.id}",
            headers=auth_headers,
            json={"name": "Updated"},
        )
        assert response.status_code == 403

    def test_updates_tenant(self, client, admin_headers, test_db, test_tenant):
        """Should update tenant fields."""
        response = client.patch(
            f"/api/v1/admin/tenants/{test_tenant.id}",
            headers=admin_headers,
            json={
                "description": "Updated description",
                "contact_email": "updated@test.com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["description"] == "Updated description"
        assert data["data"]["contact_email"] == "updated@test.com"

    def test_can_deactivate(self, client, admin_headers, test_db):
        """Should be able to deactivate tenant."""
        # Create a tenant to deactivate
        tenant = Tenant(name="To Deactivate", is_active=True)
        test_db.add(tenant)
        test_db.commit()

        response = client.patch(
            f"/api/v1/admin/tenants/{tenant.id}",
            headers=admin_headers,
            json={"is_active": False},
        )

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False


class TestDeleteTenant:
    """Test DELETE /api/v1/admin/tenants/{tenant_id} endpoint."""

    def test_requires_admin_permission(self, client, auth_headers, test_tenant):
        """Regular API key should be denied."""
        response = client.delete(
            f"/api/v1/admin/tenants/{test_tenant.id}", headers=auth_headers
        )
        assert response.status_code == 403

    def test_deletes_tenant(self, client, admin_headers, test_db):
        """Should delete tenant."""
        # Create a tenant to delete
        tenant = Tenant(name="To Delete", is_active=True)
        test_db.add(tenant)
        test_db.commit()
        tenant_id = tenant.id

        response = client.delete(
            f"/api/v1/admin/tenants/{tenant_id}", headers=admin_headers
        )

        # DELETE returns 204 No Content on success
        assert response.status_code == 204

        # Verify deletion
        deleted = test_db.query(Tenant).filter(Tenant.id == tenant_id).first()
        assert deleted is None

    def test_returns_404_for_missing(self, client, admin_headers):
        """Non-existent tenant should return 404."""
        response = client.delete(
            "/api/v1/admin/tenants/99999", headers=admin_headers
        )

        assert response.status_code == 404
