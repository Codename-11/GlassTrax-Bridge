"""
Integration tests for admin API keys router.

Tests API key CRUD operations at /api/v1/admin/api-keys.
"""

import pytest
from api.models import APIKey


class TestListAPIKeys:
    """Test GET /api/v1/admin/api-keys endpoint."""

    def test_requires_admin_permission(self, client, auth_headers):
        """Regular API key should be denied."""
        response = client.get("/api/v1/admin/api-keys", headers=auth_headers)
        assert response.status_code == 403

    def test_returns_keys(self, client, admin_headers, test_api_key):
        """Should return list of API keys."""
        response = client.get("/api/v1/admin/api-keys", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1

    def test_keys_have_prefix_not_hash(self, client, admin_headers, test_api_key):
        """Returned keys should have prefix, not full hash."""
        response = client.get("/api/v1/admin/api-keys", headers=admin_headers)

        data = response.json()
        for key in data["data"]:
            assert "key_prefix" in key
            assert "key_hash" not in key  # Hash should not be exposed

    def test_filter_by_tenant(self, client, admin_headers, test_tenant, test_api_key):
        """Should filter by tenant_id."""
        response = client.get(
            f"/api/v1/admin/api-keys?tenant_id={test_tenant.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        for key in data["data"]:
            assert key["tenant_id"] == test_tenant.id


class TestCreateAPIKey:
    """Test POST /api/v1/admin/api-keys endpoint."""

    def test_requires_admin_permission(self, client, auth_headers, test_tenant):
        """Regular API key should be denied."""
        response = client.post(
            "/api/v1/admin/api-keys",
            headers=auth_headers,
            json={"tenant_id": test_tenant.id, "name": "New Key"},
        )
        assert response.status_code == 403

    def test_creates_key(self, client, admin_headers, test_tenant):
        """Should create a new API key."""
        response = client.post(
            "/api/v1/admin/api-keys",
            headers=admin_headers,
            json={
                "tenant_id": test_tenant.id,
                "name": "New Test Key",
                "permissions": ["customers:read"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "New Test Key"
        assert "key" in data["data"]  # Plaintext key returned on creation
        assert data["data"]["key"].startswith("gtb_")

    def test_key_only_shown_once(self, client, admin_headers, test_tenant):
        """Plaintext key should only be shown on creation."""
        # Create key
        create_response = client.post(
            "/api/v1/admin/api-keys",
            headers=admin_headers,
            json={
                "tenant_id": test_tenant.id,
                "name": "Show Once Key",
                "permissions": ["customers:read"],
            },
        )
        key_id = create_response.json()["data"]["id"]

        # Get key - should not have plaintext
        get_response = client.get(
            f"/api/v1/admin/api-keys/{key_id}", headers=admin_headers
        )

        assert "key" not in get_response.json()["data"]

    def test_requires_tenant_id(self, client, admin_headers):
        """tenant_id should be required."""
        response = client.post(
            "/api/v1/admin/api-keys",
            headers=admin_headers,
            json={"name": "No Tenant"},
        )

        assert response.status_code == 422

    def test_requires_name(self, client, admin_headers, test_tenant):
        """name should be required."""
        response = client.post(
            "/api/v1/admin/api-keys",
            headers=admin_headers,
            json={"tenant_id": test_tenant.id},
        )

        assert response.status_code == 422

    def test_invalid_tenant_fails(self, client, admin_headers):
        """Non-existent tenant should fail."""
        response = client.post(
            "/api/v1/admin/api-keys",
            headers=admin_headers,
            json={"tenant_id": 99999, "name": "Invalid Tenant Key"},
        )

        assert response.status_code == 404


class TestGetAPIKey:
    """Test GET /api/v1/admin/api-keys/{key_id} endpoint."""

    def test_requires_admin_permission(self, client, auth_headers, test_api_key):
        """Regular API key should be denied."""
        api_key, _ = test_api_key
        response = client.get(
            f"/api/v1/admin/api-keys/{api_key.id}", headers=auth_headers
        )
        assert response.status_code == 403

    def test_returns_key(self, client, admin_headers, test_api_key):
        """Should return key details."""
        api_key, _ = test_api_key
        response = client.get(
            f"/api/v1/admin/api-keys/{api_key.id}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == api_key.id
        assert data["data"]["name"] == api_key.name

    def test_returns_404_for_missing(self, client, admin_headers):
        """Non-existent key should return 404."""
        response = client.get(
            "/api/v1/admin/api-keys/99999", headers=admin_headers
        )

        assert response.status_code == 404


class TestUpdateAPIKey:
    """Test PATCH /api/v1/admin/api-keys/{key_id} endpoint."""

    def test_requires_admin_permission(self, client, auth_headers, test_api_key):
        """Regular API key should be denied."""
        api_key, _ = test_api_key
        response = client.patch(
            f"/api/v1/admin/api-keys/{api_key.id}",
            headers=auth_headers,
            json={"name": "Updated"},
        )
        assert response.status_code == 403

    def test_updates_key(self, client, admin_headers, test_api_key):
        """Should update key fields."""
        api_key, _ = test_api_key
        response = client.patch(
            f"/api/v1/admin/api-keys/{api_key.id}",
            headers=admin_headers,
            json={
                "name": "Updated Key Name",
                "description": "Updated description",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated Key Name"
        assert data["data"]["description"] == "Updated description"

    def test_can_update_permissions(self, client, admin_headers, test_api_key):
        """Should be able to update permissions."""
        api_key, _ = test_api_key
        response = client.patch(
            f"/api/v1/admin/api-keys/{api_key.id}",
            headers=admin_headers,
            json={"permissions": ["customers:read", "customers:write", "orders:read"]},
        )

        assert response.status_code == 200
        assert "customers:write" in response.json()["data"]["permissions"]


class TestDeactivateAPIKey:
    """Test POST /api/v1/admin/api-keys/{key_id}/deactivate endpoint."""

    def test_requires_admin_permission(self, client, auth_headers, test_api_key):
        """Regular API key should be denied."""
        api_key, _ = test_api_key
        response = client.post(
            f"/api/v1/admin/api-keys/{api_key.id}/deactivate", headers=auth_headers
        )
        assert response.status_code == 403

    def test_deactivates_key(self, client, admin_headers, test_db, test_tenant):
        """Should deactivate the key."""
        # Create a key to deactivate
        api_key, _ = APIKey.create_key(
            tenant_id=test_tenant.id,
            name="To Deactivate",
            permissions=["customers:read"],
        )
        test_db.add(api_key)
        test_db.commit()

        response = client.post(
            f"/api/v1/admin/api-keys/{api_key.id}/deactivate", headers=admin_headers
        )

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False


class TestActivateAPIKey:
    """Test POST /api/v1/admin/api-keys/{key_id}/activate endpoint."""

    def test_activates_key(self, client, admin_headers, test_db, test_tenant):
        """Should activate a deactivated key."""
        # Create a deactivated key
        api_key, _ = APIKey.create_key(
            tenant_id=test_tenant.id,
            name="To Activate",
            permissions=["customers:read"],
        )
        api_key.is_active = False
        test_db.add(api_key)
        test_db.commit()

        response = client.post(
            f"/api/v1/admin/api-keys/{api_key.id}/activate", headers=admin_headers
        )

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is True


class TestDeleteAPIKey:
    """Test DELETE /api/v1/admin/api-keys/{key_id} endpoint."""

    def test_requires_admin_permission(self, client, auth_headers, test_api_key):
        """Regular API key should be denied."""
        api_key, _ = test_api_key
        response = client.delete(
            f"/api/v1/admin/api-keys/{api_key.id}", headers=auth_headers
        )
        assert response.status_code == 403

    def test_deletes_key(self, client, admin_headers, test_db, test_tenant):
        """Should delete the key."""
        # Create a key to delete
        api_key, _ = APIKey.create_key(
            tenant_id=test_tenant.id,
            name="To Delete",
            permissions=["customers:read"],
        )
        test_db.add(api_key)
        test_db.commit()
        key_id = api_key.id

        response = client.delete(
            f"/api/v1/admin/api-keys/{key_id}", headers=admin_headers
        )

        # DELETE returns 204 No Content on success
        assert response.status_code == 204

        # Verify deletion
        deleted = test_db.query(APIKey).filter(APIKey.id == key_id).first()
        assert deleted is None
