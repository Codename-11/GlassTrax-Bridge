# Permissions

API keys are granted specific permissions that control what resources they can access.

## Permission Format

Permissions follow the format `resource:action`:

```
customers:read
orders:write
admin:*
```

## Available Permissions

### Data Permissions

| Permission | Description |
|------------|-------------|
| `customers:read` | Read customer data |
| `customers:write` | Modify customer data (future) |
| `orders:read` | Read order data |
| `orders:write` | Modify order data (future) |

### Admin Permissions

| Permission | Description |
|------------|-------------|
| `admin:*` | Full admin access |

### Wildcards

| Permission | Description |
|------------|-------------|
| `*:*` | Superuser - all permissions |
| `customers:*` | All customer operations |

## Assigning Permissions

When creating an API key, specify permissions as an array:

```json
{
  "permissions": ["customers:read", "orders:read"]
}
```

## Checking Permissions

The API automatically checks permissions on each request:

```
GET /api/v1/customers  →  Requires: customers:read
GET /api/v1/orders     →  Requires: orders:read
GET /api/v1/admin/*    →  Requires: admin:*
```

If a key lacks the required permission, a 403 Forbidden response is returned:

```json
{
  "detail": "Permission denied: customers:read required"
}
```

## Best Practices

1. **Least privilege** - Only grant permissions that are needed
2. **Separate keys** - Use different keys for different purposes
3. **Avoid wildcards** - Don't use `*:*` except for admin keys
4. **Review regularly** - Periodically audit key permissions
