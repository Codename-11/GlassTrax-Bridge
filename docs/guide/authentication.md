# Authentication

GlassTrax Bridge supports multiple authentication methods.

## API Key Authentication

API keys are the primary method for authenticating API requests.

### Using API Keys

Include the key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: gtb_your-api-key-here" \
  http://localhost:8000/api/v1/customers
```

### Key Format

Production API keys start with `gtb_` followed by 32 random characters:

```
gtb_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6
```

Keys are bcrypt-hashed in the database. The full key is only shown once at creation.

## JWT Authentication

The admin portal uses JWT tokens for authentication.

### Getting a Token

```bash
curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

Response:
```json
{
  "success": true,
  "data": {
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 86400
  }
}
```

### Using JWT Tokens

Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1Qi..." \
  http://localhost:8000/api/v1/admin/tenants
```

## First-Run Admin Key

On first startup, an admin API key is automatically generated and displayed in the console:

```
======================================================================
  INITIAL ADMIN API KEY GENERATED
======================================================================

  Key: gtb_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

  IMPORTANT: Save this key now! It will NOT be shown again.
  This key has full admin permissions.

======================================================================
```

::: warning Save This Key!
The admin key is only shown once. If lost, you'll need to create a new one via the database or reset the database.
:::

## Admin Password

Configure the admin password in `config.yaml`:

```yaml
admin:
  username: "admin"
  password_hash: "$2b$12$..."  # bcrypt hash
```

Generate a hash:
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
```

::: danger Default Password
The default password is `admin`. Change this immediately in production!
:::
