# GlassTrax Agent Setup

The GlassTrax Agent is a minimal service that runs on Windows to provide ODBC access to the GlassTrax database. It allows Docker deployments to query GlassTrax data via HTTP.

## Prerequisites

- Windows with Pervasive SQL client installed
- 32-bit Python (bundled in `python32/`)
- ODBC DSN configured for GlassTrax database

## Quick Start

### 1. Start the Agent

```powershell
.\agent\run_agent.bat
```

On first run, the agent will:
1. Generate an API key and display it in the console
2. Save the key hash to `agent_config.yaml`
3. Start listening on port 8001

::: warning Important
Save the API key shown on first run! It will **NOT** be shown again.
:::

### 2. Configure Your Application

Use the generated API key to configure your Docker deployment or API:

```bash
AGENT_ENABLED=true \
AGENT_URL=http://YOUR_WINDOWS_IP:8001 \
AGENT_KEY=gta_your_key_here \
docker-compose up -d
```

## Install as Windows Service

For production deployments, install the agent as a Windows service using NSSM.

### Prerequisites

Download [NSSM](https://nssm.cc/) and place `nssm.exe` in your PATH or in the project root.

### Installation

```powershell
.\agent\install_service.bat
```

This creates a Windows service called `GlassTraxAgent` that:
- Starts automatically on boot
- Runs under the Local System account
- Logs to `data\agent.log`

### Uninstallation

```powershell
.\agent\uninstall_service.bat
```

### Manual Service Management

```powershell
# Start the service
net start GlassTraxAgent

# Stop the service
net stop GlassTraxAgent

# Check status
sc query GlassTraxAgent
```

## Configuration

The agent configuration is stored in `agent_config.yaml`:

```yaml
database:
  dsn: "LIVE"                # ODBC Data Source Name
  readonly: true             # Always true (safety)
  timeout: 30                # Query timeout in seconds

agent:
  port: 8001                 # Agent listen port
  api_key_hash: "..."        # bcrypt hash of API key (auto-generated)
  allowed_tables:            # Tables accessible via agent
    - customer
    - customer_contacts
    - delivery_routes
    - sales_orders_headers
    - sales_order_detail
```

### Allowed Tables

For security, the agent only allows queries to tables listed in `allowed_tables`. Add tables as needed:

```yaml
agent:
  allowed_tables:
    - customer
    - orders
    - orderdet
    - inventry
```

## API Endpoints

The agent exposes two endpoints:

### Health Check

```bash
GET /health
```

Returns agent status and database connectivity:

```json
{
  "status": "healthy",
  "version": "1.1.0",
  "pyodbc_installed": true,
  "database_connected": true,
  "dsn": "LIVE"
}
```

### Query Endpoint

```bash
POST /query
X-Agent-Key: gta_your_key_here
Content-Type: application/json
```

Request body:

```json
{
  "table": "customer",
  "columns": ["Customer_Number", "Company_Name"],
  "filters": [
    {"column": "Status", "operator": "=", "value": "A"}
  ],
  "limit": 100,
  "offset": 0
}
```

Response:

```json
{
  "success": true,
  "columns": ["Customer_Number", "Company_Name"],
  "rows": [
    ["001", "Acme Corp"],
    ["002", "Beta Inc"]
  ],
  "row_count": 2
}
```

## Security

### API Key Authentication

All requests to `/query` require the `X-Agent-Key` header with a valid API key.

The API key is generated on first run and stored as a bcrypt hash. To regenerate:

1. Stop the agent
2. Delete the `api_key_hash` line from `agent_config.yaml`
3. Restart the agent

### Table Allowlist

The agent only allows queries to tables listed in `allowed_tables`. This prevents access to sensitive tables not needed by the API.

### Network Security

- Run the agent on a private network
- Use firewall rules to allow only trusted hosts
- Consider using a VPN for cross-network access

## Troubleshooting

### Agent won't start

1. Check Python is available: `python32\python.exe --version`
2. Verify ODBC DSN exists: Control Panel → ODBC Data Sources (32-bit)
3. Check `agent_config.yaml` is valid YAML

### "Unauthorized" errors

1. Verify the API key matches what was generated
2. Check the key is sent in `X-Agent-Key` header
3. Try regenerating the key (delete hash from config)

### "Table not allowed" errors

Add the table name to `agent.allowed_tables` in `agent_config.yaml`

### Database connection errors

1. Verify ODBC DSN works: Test in ODBC Administrator
2. Check Pervasive client is running
3. Ensure 32-bit Python is used (64-bit won't work with 32-bit ODBC)

### Port already in use

Change the port in `agent_config.yaml`:

```yaml
agent:
  port: 8002
```

## Logs

- **Tray Mode**: Logs written to `%APPDATA%\GlassTrax Agent\agent.log`
- **Console Mode**: Logs appear in console
- **Service**: Logs written to `data\agent.log`

The log file is recreated each time the agent starts. Access it via the tray menu "View Log File" option.
