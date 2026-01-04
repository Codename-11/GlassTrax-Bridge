# Admin Portal

The GlassTrax Bridge Admin Portal provides a web-based interface for managing the API.

## Overview

The portal allows you to:

- **Manage API Keys** - Create, activate, deactivate, and revoke keys
- **Manage Applications** - Organize keys by application/integration
- **View Access Logs** - Real-time view of API activity
- **Run Diagnostics** - Check system health and connectivity
- **Server Management** - Restart server and reset database

## Accessing the Portal

### Start the Portal

```bash
cd portal
npm install
npm run dev
```

The portal runs at `http://localhost:5173`

### Login

Use one of these methods:

1. **Username/Password**: `admin` / your configured password
2. **API Key**: Enter `admin` as username and your API key as password

::: tip Default Password
The default password is `admin`. You should change this in `config.yaml`.
:::

## Pages

### Dashboard

Overview of your GlassTrax Bridge instance:

- Total applications
- Active/total API keys
- Recent API requests

### API Keys

Create and manage API keys:

- **Create Key**: Generate new keys with specific permissions
- **Activate/Deactivate**: Toggle key status without deleting
- **Delete**: Permanently revoke keys

::: warning Key Display
The full API key is only shown once at creation. Copy it immediately!
:::

### Applications

Organize your API keys by application or integration.

### Access Logs

Real-time view of all API requests with:

- Request method and path
- Response status (color-coded)
- Response time
- API key used

Auto-refreshes every 5 seconds.

### Diagnostics

System health monitoring:

- Python environment check
- ODBC driver detection
- GlassTrax database connectivity
- API endpoint testing

**Server Controls:**
- Restart Server button
- Database Reset (danger zone)
