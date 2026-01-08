# Applications

Applications (also called tenants) are used to organize and isolate API keys.

## What are Applications?

An application represents a client system or integration that uses the API:

- A mobile app
- A third-party integration
- A reporting system
- A partner's system

Each application can have multiple API keys.

## Creating Applications

### Via Portal

1. Navigate to **Applications** page
2. Click **Create Application**
3. Enter name, description, and contact email
4. Click **Create**

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mobile App",
    "description": "iOS and Android apps",
    "contact_email": "dev@example.com"
  }'
```

## Managing Applications

You can edit, deactivate, or delete applications from the **Applications** page in the portal.

### Edit Application

Update name, description, contact email, or active status:

- Via portal: Click **Edit** on an application
- Via API:

```bash
curl -X PATCH http://localhost:8000/api/v1/admin/tenants/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description", "is_active": false}'
```

### Deactivate Application

Deactivating an application disables all its API keys without deleting them. This is useful for temporarily suspending access.

### Delete Application

::: danger
Deleting an application also deletes all its API keys! This cannot be undone.
:::

```bash
curl -X DELETE http://localhost:8000/api/v1/admin/tenants/1 \
  -H "Authorization: Bearer $TOKEN"
```

::: info System Application
The "System" application is created automatically and used for admin operations. It cannot be deleted or modified via the portal.
:::

## Best Practices

1. **One application per integration** - Makes it easy to track usage and revoke access
2. **Descriptive names** - Use names like "Partner XYZ Integration" not "App 1"
3. **Contact email** - Include a contact for each application
4. **Separate dev/prod** - Create separate applications for development and production
