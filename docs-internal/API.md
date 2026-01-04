# GlassTrax Bridge API Documentation

## Overview

GlassTrax Bridge provides a REST API for accessing GlassTrax ERP data. The API is read-only for GlassTrax data and requires authentication.

**API Version:** v1

| Environment | Base URL | OpenAPI Docs |
|-------------|----------|--------------|
| Development | `http://localhost:5173` | `http://localhost:5173/api/docs` |
| Production (Windows) | `http://localhost:8000` | `http://localhost:8000/api/docs` |
| Production (Docker) | `http://localhost:3000` | `http://localhost:3000/api/docs` |

In development, Vite proxies `/api` to the backend. All environments use the same paths (`/api/v1/*`).

---

## Authentication

The API supports two authentication methods:

### 1. API Key (X-API-Key header)

```bash
curl -H "X-API-Key: gtb_your-api-key" http://localhost:8000/api/v1/customers
```

### 2. JWT Bearer Token (Authorization header)

```bash
curl -H "Authorization: Bearer your-jwt-token" http://localhost:8000/api/v1/customers
```

JWT tokens are obtained by logging in via the `/api/v1/admin/login` endpoint.

---

## API Keys

API keys are database-managed with bcrypt hashing. Keys start with prefix `gtb_`.

On first startup, an admin API key is auto-generated and displayed in the console. **Save this key!**

### Permissions

Permissions follow the format `resource:action`:

| Permission | Description |
|------------|-------------|
| `customers:read` | Read customer data |
| `orders:read` | Read order data |
| `admin:*` | Full admin access |
| `*:*` | Superuser (all permissions) |

---

## Endpoints

### Health Check

```
GET /health
```

Returns API health status. **No authentication required.**

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "glasstrax_connected": true,
  "app_db_connected": true
}
```

---

### Customers

#### List Customers

```
GET /api/v1/customers
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (max 100) |
| `search` | string | - | Search by name or ID |
| `route_id` | string | - | Filter by route |

**Example:**
```bash
curl -H "X-API-Key: gtb_your-key" \
  "http://localhost:8000/api/v1/customers?page_size=10&search=glass"
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "customer_id": "1234",
      "customer_name": "ABC Glass Co",
      "route_id": "RT01",
      "route_name": "Route 1",
      "main_city": "Tampa",
      "main_state": "FL",
      "customer_type": "A",
      "inside_salesperson": "John"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_items": 463,
    "total_pages": 47,
    "has_next": true,
    "has_previous": false
  }
}
```

#### Get Customer by ID

```
GET /api/v1/customers/{customer_id}
```

---

### Orders

#### List Orders

```
GET /api/v1/orders
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (max 100) |
| `customer_id` | string | - | Filter by customer |

#### Get Order by ID

```
GET /api/v1/orders/{order_id}
```

---

## Admin Endpoints

Admin endpoints require `admin:*` permission.

### Authentication

#### Login

```
POST /api/v1/admin/login
```

Authenticate and receive a JWT token.

**Request Body:**
```json
{
  "username": "admin",
  "password": "your-password-or-api-key"
}
```

**Supported authentication methods:**
1. Username + password from config.yaml
2. Username + database API key with admin permissions

**Response:**
```json
{
  "success": true,
  "data": {
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "is_default_password": true
  },
  "message": "Login successful"
}
```

---

### Applications (Tenants)

```
GET    /api/v1/admin/tenants          # List applications
POST   /api/v1/admin/tenants          # Create application
GET    /api/v1/admin/tenants/{id}     # Get application
PATCH  /api/v1/admin/tenants/{id}     # Update application
DELETE /api/v1/admin/tenants/{id}     # Delete application
```

**Create Application:**
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My App", "description": "Production app"}' \
  http://localhost:8000/api/v1/admin/tenants
```

---

### API Keys

```
GET    /api/v1/admin/api-keys              # List keys
POST   /api/v1/admin/api-keys              # Create key
GET    /api/v1/admin/api-keys/{id}         # Get key
PATCH  /api/v1/admin/api-keys/{id}         # Update key
DELETE /api/v1/admin/api-keys/{id}         # Revoke key
POST   /api/v1/admin/api-keys/{id}/activate    # Activate
POST   /api/v1/admin/api-keys/{id}/deactivate  # Deactivate
```

**Create API Key:**
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "name": "Production Key",
    "permissions": ["customers:read", "orders:read"],
    "rate_limit": 60
  }' \
  http://localhost:8000/api/v1/admin/api-keys
```

**Response (key shown only once!):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "tenant_id": 1,
    "name": "Production Key",
    "key_prefix": "gtb_a1B2c3D4",
    "key": "gtb_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6",
    "permissions": ["customers:read", "orders:read"],
    "rate_limit": 60,
    "expires_at": null,
    "created_at": "2026-01-03T12:00:00"
  },
  "message": "API key created successfully. Store the key securely!"
}
```

---

### Access Logs

```
GET /api/v1/admin/access-logs
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `page_size` | int | Items per page |
| `tenant_id` | int | Filter by tenant |
| `api_key_id` | int | Filter by API key |
| `limit` | int | Limit total results |

---

### Diagnostics

```
GET /api/v1/admin/diagnostics
```

Run system diagnostics including:
- Python environment check
- ODBC driver detection
- GlassTrax database connectivity
- App database (SQLite) status
- Configuration validation
- API endpoint testing

**Response:**
```json
{
  "success": true,
  "data": {
    "overall_status": "healthy",
    "checks": [
      {
        "name": "Python Environment",
        "status": "pass",
        "message": "Python 3.11 (32-bit)",
        "details": {...}
      },
      {
        "name": "GlassTrax Database",
        "status": "pass",
        "message": "Successfully connected to GlassTrax database"
      },
      {
        "name": "API Endpoint Test (Customers)",
        "status": "pass",
        "message": "Successfully retrieved customer data (45ms)"
      }
    ],
    "system_info": {
      "platform": "win32",
      "python_version": "3.11.9",
      "architecture": "32-bit",
      "timezone": "America/New_York",
      "cwd": "C:\\path\\to\\GlassTrax-Bridge"
    }
  }
}
```

---

### Server Management

#### Restart Server

```
POST /api/v1/admin/restart-server
```

Restart the API server. The server will restart after ~2 seconds.

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Server restart initiated. The server will restart in ~2 seconds.",
    "restart_in_seconds": 2
  },
  "message": "Server is restarting..."
}
```

#### Reset Database

```
POST /api/v1/admin/reset-database
```

**DANGER:** Completely resets the application database.

**Request Body:**
```json
{
  "confirmation": "RESET DATABASE"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "tables_cleared": [
      "access_logs (150 records)",
      "api_keys (3 records)",
      "tenants (2 records)"
    ],
    "message": "Database reset complete. Restart the server to generate a new admin key."
  }
}
```

---

### Configuration

#### Get Configuration

```
GET /api/v1/admin/config
```

Returns editable configuration values (sensitive fields excluded).

**Response:**
```json
{
  "success": true,
  "data": {
    "database": {
      "friendly_name": "TGI Database",
      "dsn": "LIVE",
      "readonly": true,
      "timeout": 30
    },
    "application": {
      "timezone": "America/New_York",
      "logging": {
        "level": "INFO",
        "log_to_file": true,
        "log_to_console": true
      },
      "performance": {
        "query_timeout": 60,
        "fetch_size": 1000
      }
    },
    "features": {
      "enable_caching": false,
      "enable_exports": true
    },
    "admin": {
      "username": "admin"
    },
    "agent": {
      "enabled": false,
      "url": "http://localhost:8001",
      "timeout": 30
    }
  }
}
```

> **Note:** Feature flags (`enable_caching`, `enable_exports`) and some application settings (`logging`, `performance`) are not yet implemented. See `TODO.md` for details.

#### Update Configuration

```
PATCH /api/v1/admin/config
```

Update configuration and save to config.yaml. Comments and formatting are preserved.

**Request Body:**
```json
{
  "database": {
    "friendly_name": "Production Database",
    "timeout": 60
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "changed_fields": ["database.friendly_name", "database.timeout"],
    "restart_required": false,
    "restart_required_fields": [],
    "message": "Configuration updated (2 field(s) changed)"
  }
}
```

**Restart-Required Fields:**
- `database.dsn` - Changing DSN requires server restart

---

### ODBC Data Sources

#### List DSNs

```
GET /api/v1/admin/dsns
```

Returns available ODBC Data Source Names (DSNs) visible to the current Python architecture.

**Note:** Only 32-bit ODBC DSNs are shown because GlassTrax Bridge uses 32-bit Python for Pervasive ODBC compatibility. Configure DSNs in Windows ODBC Data Source Administrator (32-bit).

**Response:**
```json
{
  "success": true,
  "data": {
    "dsns": [
      { "name": "LIVE", "driver": "Pervasive ODBC Client Interface", "is_pervasive": true },
      { "name": "TEST", "driver": "Pervasive ODBC Client Interface", "is_pervasive": true },
      { "name": "Excel Files", "driver": "Microsoft Excel Driver", "is_pervasive": false }
    ],
    "pervasive_dsns": ["LIVE", "TEST"],
    "architecture": "32-bit"
  }
}
```

#### Test DSN Connection

```
POST /api/v1/admin/test-dsn
```

Test connection to a DSN before saving to configuration. Attempts to connect and enumerate tables to verify GlassTrax data is accessible.

**Request Body:**
```json
{
  "dsn": "LIVE",
  "readonly": true
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "dsn": "LIVE",
    "message": "Connected successfully! Found GlassTrax tables.",
    "tables_found": 45,
    "sample_tables": ["CUSTOMER", "ORDERS", "ORDERDET", "INVENTRY", "VENDOR"]
  }
}
```

**Response (Failure):**
```json
{
  "success": true,
  "data": {
    "success": false,
    "dsn": "INVALID",
    "message": "Connection failed: Data source name not found"
  }
}
```

---

### Password Management

#### Change Password

```
POST /api/v1/admin/change-password
```

Change the admin portal password. Requires current password verification.

**Request Body:**
```json
{
  "current_password": "current-password",
  "new_password": "new-secure-password"
}
```

**Validation:**
- New password must be at least 6 characters

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Password changed successfully"
  },
  "message": "Password changed successfully. You may need to log in again."
}
```

**Errors:**
- `401`: Current password is incorrect
- `400`: New password too short (< 6 characters)

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

| Status Code | Description |
|-------------|-------------|
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorized (missing/invalid API key or token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not found |
| 500 | Internal server error |

---

## Rate Limiting

API keys have a configurable rate limit (requests per minute). Default is 60 req/min.

When rate limited:
```json
{
  "detail": "Rate limit exceeded. Try again in X seconds."
}
```

---

## Running the API

### Development

```bash
.\python32\python.exe -m uvicorn api.main:app --reload --port 8000
```

### Production

```bash
.\python32\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## Extending the API

To add new endpoints, GlassTrax queries, or database models, see [EXTENDING.md](./EXTENDING.md).
