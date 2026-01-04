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

### List Applications

```bash
curl http://localhost:8000/api/v1/admin/tenants \
  -H "Authorization: Bearer $TOKEN"
```

### Update Application

```bash
curl -X PATCH http://localhost:8000/api/v1/admin/tenants/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description"}'
```

### Delete Application

::: danger
Deleting an application also deletes all its API keys!
:::

```bash
curl -X DELETE http://localhost:8000/api/v1/admin/tenants/1 \
  -H "Authorization: Bearer $TOKEN"
```

## Best Practices

1. **One application per integration** - Makes it easy to track usage and revoke access
2. **Descriptive names** - Use names like "Partner XYZ Integration" not "App 1"
3. **Contact email** - Include a contact for each application
4. **Separate dev/prod** - Create separate applications for development and production
