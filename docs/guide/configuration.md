# Configuration

GlassTrax Bridge is configured through `config.yaml` and environment variables.

## config.yaml

The main configuration file in the project root.

### Database Connection

GlassTrax Bridge connects via ODBC using a Data Source Name (DSN). Configure your DSN in Windows ODBC Data Source Administrator (32-bit), then reference it in `config.yaml`:

```yaml
database:
  friendly_name: "TGI Database"   # Display name in UI
  dsn: "LIVE"                     # ODBC Data Source Name
  readonly: true                  # Always read-only
  timeout: 30                     # Query timeout (seconds)
```

::: tip DSN Configuration
The DSN contains all connection details (server, driver, protocol). Configure it in:
**Control Panel → Administrative Tools → ODBC Data Sources (32-bit)**
:::

### Application Settings

```yaml
application:
  timezone: "America/New_York"  # IANA timezone

  logging:
    level: "INFO"           # DEBUG, INFO, WARNING, ERROR
    log_to_file: true
    log_to_console: true

  performance:
    query_timeout: 60       # Query timeout (seconds)
    fetch_size: 1000        # Rows per fetch
```

### Admin Authentication

```yaml
admin:
  username: "admin"
  # password_hash: "$2b$12$..."  # bcrypt hash (optional)
```

**Generate a password hash:**

<PasswordHasher />

::: details Command Line Options
```bash
# Using Python
python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"

# Using Docker
docker run --rm python:3.11-slim python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
```
:::

## Environment Variables

Override settings with environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GLASSTRAX_HOST` | `0.0.0.0` | API bind address |
| `GLASSTRAX_PORT` | `8000` | API port |
| `GLASSTRAX_DEBUG` | `false` | Debug mode |
| `GLASSTRAX_SECRET_KEY` | (random) | JWT signing key |

## Agent Settings

Configure connection to a Windows GlassTrax API Agent for Docker deployments:

```yaml
agent:
  enabled: false              # Enable agent mode
  url: "http://localhost:8001" # Agent URL
  api_key: ""                 # Agent API key
  timeout: 30                 # Request timeout (seconds)
```

### Agent Mode

When running Docker + Windows Agent (agent mode):

1. **Windows** runs a minimal agent with ODBC access to GlassTrax
2. **Docker** runs the full API and portal, querying GlassTrax via the agent

This allows everything except ODBC to run in containers while database queries are routed to the Windows agent.

**Setup:**

1. On Windows, start the agent:
   ```powershell
   .\agent\run_agent.bat
   ```
   Save the API key shown on first run!

2. Note your Windows IP address:
   ```powershell
   ipconfig
   # Look for IPv4 Address, e.g., 192.168.1.100
   ```

3. Configure `config.yaml` or use environment variables:
   ```yaml
   agent:
     enabled: true
     url: "http://192.168.1.100:8001"
     api_key: "gta_your_key_here"
     timeout: 30
   ```

4. Start Docker with agent configuration:
   ```bash
   AGENT_ENABLED=true \
   AGENT_URL=http://192.168.1.100:8001 \
   AGENT_KEY=gta_your_key_here \
   docker-compose up -d
   ```

You can also configure these settings in the portal's Settings page under "Data Source" → "Agent" mode.

::: tip
For detailed agent setup instructions, see [Agent Setup](/guide/agent-setup).
:::

## Timezone

Set your timezone in `config.yaml`:

```yaml
application:
  timezone: "America/New_York"
```

Common timezones:
- `America/New_York` - Eastern
- `America/Chicago` - Central
- `America/Denver` - Mountain
- `America/Los_Angeles` - Pacific
- `UTC` - Coordinated Universal Time

The timezone is displayed in the Diagnostics page under System Information.
