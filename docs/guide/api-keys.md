# API Keys

API keys are the primary authentication mechanism for the GlassTrax Bridge API.

## Key Format

Production API keys follow this format:

```
gtb_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

- Prefix: `gtb_` (GlassTrax Bridge)
- Random: 32 alphanumeric characters
- Total length: 36 characters

## Creating API Keys

::: tip Application Required
Before creating an API key, you must first [register an application](/guide/applications). API keys are always associated with an application, which allows you to organize and manage access by project or service.
:::

### Via Portal

1. Navigate to **API Keys** page
2. Click **Create API Key**
3. Select an application
4. Enter a name and description
5. Select permissions
6. Set rate limit (optional)
7. Set expiration date (optional)
8. Click **Create**

::: warning One-Time Display
The full API key is only shown once. Copy it immediately!
:::

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/admin/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "name": "Production Key",
    "permissions": ["customers:read", "orders:read"],
    "rate_limit": 60
  }'
```

## Managing Keys

### Activate/Deactivate

Toggle a key's status without deleting it:

```bash
# Deactivate
curl -X POST http://localhost:8000/api/v1/admin/api-keys/1/deactivate \
  -H "Authorization: Bearer $TOKEN"

# Activate
curl -X POST http://localhost:8000/api/v1/admin/api-keys/1/activate \
  -H "Authorization: Bearer $TOKEN"
```

### Delete (Revoke)

Permanently delete a key:

```bash
curl -X DELETE http://localhost:8000/api/v1/admin/api-keys/1 \
  -H "Authorization: Bearer $TOKEN"
```

## Rate Limiting

Each key has a configurable rate limit (requests per minute).

- Default: 60 req/min
- Maximum: Configurable per key

When exceeded, requests receive a 429 response.

## Expiration

Keys can be set to expire automatically:

```json
{
  "expires_at": "2026-12-31T23:59:59"
}
```

Expired keys return a 401 error with message indicating expiration.
