# API Reference

GlassTrax Bridge provides a REST API for accessing GlassTrax ERP data.

## Base URL

The base URL depends on your deployment:

| Deployment | Base URL |
|------------|----------|
| Windows Production | `http://localhost:8000` |
| Docker | `http://localhost:3000` |
| Custom | Your configured URL |

## API Version

All endpoints are prefixed with `/api/v1`.

## Interactive Documentation

OpenAPI (Swagger) documentation is available at `/api/docs`:

- Windows: `http://localhost:8000/api/docs`
- Docker: `http://localhost:3000/api/docs`

## Endpoints Overview

### Public Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check (no auth required) |

### Data Endpoints

| Endpoint | Description | Permission |
|----------|-------------|------------|
| `GET /api/v1/customers` | List customers | `customers:read` |
| `GET /api/v1/customers/{id}` | Get customer | `customers:read` |
| `GET /api/v1/orders` | List orders | `orders:read` |
| `GET /api/v1/orders/{so_no}` | Get order details | `orders:read` |
| `GET /api/v1/orders/{so_no}/exists` | Check if order exists | `orders:read` |

::: tip Field Selection
The `GET /orders/{so_no}` endpoint supports field selection via the `fields` query parameter for sparse responses. See [Orders API](/api/orders) for details.
:::

### Admin Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/admin/login` | Authenticate and get JWT |
| `GET /api/v1/admin/tenants` | List applications |
| `POST /api/v1/admin/tenants` | Create application |
| `GET /api/v1/admin/api-keys` | List API keys |
| `POST /api/v1/admin/api-keys` | Create API key |
| `GET /api/v1/admin/access-logs` | View access logs |
| `GET /api/v1/admin/config` | Get configuration |
| `PATCH /api/v1/admin/config` | Update configuration |
| `GET /api/v1/admin/drivers` | List ODBC drivers |
| `POST /api/v1/admin/change-password` | Change admin password |
| `GET /api/v1/admin/diagnostics` | Run diagnostics |
| `POST /api/v1/admin/restart-server` | Restart server |
| `POST /api/v1/admin/reset-database` | Reset database |

## Response Format

All responses follow this structure:

```json
{
  "success": true,
  "data": { ... },
  "message": "Optional message",
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 100,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

## Error Responses

```json
{
  "detail": "Error message"
}
```

| Status | Description |
|--------|-------------|
| 400 | Bad request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
| 500 | Server error |

## Rate Limiting

Default: 60 requests per minute per API key.

When rate limited:
```json
{
  "detail": "Rate limit exceeded. Try again in X seconds."
}
```
