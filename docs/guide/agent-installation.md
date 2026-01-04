# Agent Installation

The GlassTrax Agent is a Windows application that provides ODBC access to your GlassTrax database. It's required when running GlassTrax Bridge in Docker.

## Download

Download the latest installer from the [GitHub Releases](https://github.com/Codename-11/GlassTrax-Bridge/releases) page.

Look for `GlassTraxAgent-X.X.X-Setup.exe`.

## Installation

1. Run the installer as Administrator
2. Follow the installation wizard
3. Choose optional settings:
   - **Create desktop shortcut** - Quick access from desktop
   - **Start automatically with Windows** - Agent runs on boot

### Upgrading

To upgrade to a newer version:
1. Download the new installer
2. Run it - the installer will automatically:
   - Stop the running agent
   - Upgrade files in place
   - Preserve your configuration (stored in AppData)
3. The agent will launch automatically after upgrade

::: tip Configuration Preserved
Your `agent_config.yaml` and API key are stored in `%APPDATA%\GlassTrax Agent\` and are not affected by upgrades or reinstalls.
:::

## First Run

When the agent starts for the first time, it will:

1. Create `agent_config.yaml` with default settings
2. Generate a secure API key
3. Display the API key in a notification

::: warning Save Your API Key
The API key is shown only once on first run. Save it securely - you'll need it to connect from Docker or other systems.
:::

## Configuration

The agent configuration file is located at:
- **Installed (Tray Mode)**: `%APPDATA%\GlassTrax Agent\agent_config.yaml`
- **Manual/Development**: Same directory as the agent files

The configuration is stored in AppData to avoid permission issues with Program Files.

### Key Settings

```yaml
database:
  dsn: "LIVE"          # Your ODBC Data Source Name
  readonly: true       # Always keep this true!
  timeout: 30

agent:
  port: 8001
  allowed_tables:
    - customer
    - customer_contacts
    - sales_orders_headers
    - sales_order_detail
```

### Configuring Your DSN

1. Open **ODBC Data Source Administrator (32-bit)**
2. Add or verify your Pervasive DSN
3. Update `dsn` in the config file to match

## System Tray

The agent runs in the Windows system tray with these controls:

| Menu Item | Description |
|-----------|-------------|
| **Start/Stop Agent** | Toggle the agent on/off |
| **Open Health Check** | View health status in browser |
| **Open API Docs** | View Swagger documentation |
| **Open Config Folder** | Open the configuration directory |
| **View Log File** | Open the agent log file |
| **Exit** | Stop agent and exit |

### Tray Icon States

| Color | State |
|-------|-------|
| 🟢 Green | Agent is running |
| 🔴 Red | Agent is stopped |
| 🟡 Yellow | Error occurred |

## Connecting from Docker

Once the agent is running, configure your Docker deployment:

```bash
AGENT_ENABLED=true \
AGENT_URL=http://YOUR_WINDOWS_IP:8001 \
AGENT_KEY=gta_your_key_here \
docker-compose up -d
```

Replace:
- `YOUR_WINDOWS_IP` - The Windows machine's IP address (run `ipconfig`)
- `gta_your_key_here` - The API key from first run

## Verifying the Connection

### Check Agent Health

Open in browser: `http://localhost:8001/health`

Expected response:
```json
{
  "status": "healthy",
  "version": "1.1.0",
  "pyodbc_installed": true,
  "database_connected": true,
  "dsn": "LIVE"
}
```

### Test from Docker

```bash
curl http://YOUR_WINDOWS_IP:8001/health
```

## Running as a Windows Service

For production, you can install the agent as a Windows Service:

### Using NSSM (Recommended)

1. Download [NSSM](https://nssm.cc/download)
2. Run the install script:

```powershell
.\agent\install_service.bat
```

### Service Commands

```powershell
# Start service
sc start GlassTraxAgent

# Stop service
sc stop GlassTraxAgent

# Remove service
.\agent\uninstall_service.bat
```

## Troubleshooting

### Agent won't start

1. Check that port 8001 is not in use
2. Verify ODBC DSN is configured correctly
3. Check the log file: `%APPDATA%\GlassTrax Agent\agent.log`
4. Run in console mode for detailed errors:
   - Use "GlassTrax Agent (Console)" from Start Menu
   - Or run: `"C:\Program Files\GlassTrax Agent\python\python.exe" -m agent.cli --console`

### Database connection failed

1. Test the DSN in ODBC Administrator
2. Ensure GlassTrax server is accessible
3. Check firewall settings

### Docker can't connect

1. Verify agent is running (check tray icon)
2. Check Windows Firewall allows port 8001
3. Ensure Docker host can reach Windows IP

### Reset API Key

Delete the `api_key_hash` line from `agent_config.yaml` and restart the agent. A new key will be generated.

## Firewall Configuration

If Docker is on a different machine, allow inbound connections:

```powershell
# Allow port 8001 through Windows Firewall
netsh advfirewall firewall add rule name="GlassTrax Agent" dir=in action=allow protocol=TCP localport=8001
```
