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

![Dashboard](/screenshots/glasstrax_bridge_main_dashboard.png)

### API Keys

Create and manage API keys:

- **Create Key**: Generate new keys with specific permissions
- **Activate/Deactivate**: Toggle key status without deleting
- **Delete**: Permanently revoke keys

::: warning Key Display
The full API key is only shown once at creation. Copy it immediately!
:::

![API Keys](/screenshots/glasstrax_bridge_api_keys_layout.png)

### Applications

Organize your API keys by application or integration.

![Applications](/screenshots/glasstrax_bridge_applications_layout.png)

### Access Logs

Real-time view of all API requests with:

- Request method and path
- Response status (color-coded)
- Response time
- API key used

Auto-refreshes every 5 seconds.

![Access Logs](/screenshots/glasstrax_bridge_access_layout.png)

### Settings

Configure GlassTrax Bridge from the portal:

- **Data Source** - Choose between Direct ODBC or Remote Agent mode, configure connection settings
- **Admin credentials** - Change admin password
- **Application settings** - Timezone and logging options
- **API Access** - View API base URL and documentation links

![Settings](/screenshots/glasstrax_bridge_settings_layout.png)

### Diagnostics

System health monitoring:

- Python environment check
- ODBC driver detection
- GlassTrax database connectivity
- API endpoint testing

**Server Controls:**
- Restart Server button
- Database Reset (danger zone)

![Diagnostics](/screenshots/glasstrax_bridge_diag_layout.png)
