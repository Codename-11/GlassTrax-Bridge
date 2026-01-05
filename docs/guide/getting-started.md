# Getting Started

This guide will help you set up and start using GlassTrax Bridge.

## Prerequisites

- **Docker** (recommended) or Windows with Python 3.11 32-bit
- **Windows Server** with GlassTrax installed (for ODBC access)
- **Pervasive ODBC Driver** (32-bit) configured on Windows

## Installation

### Docker + Windows Agent (Recommended)

The recommended deployment uses Docker for the API/portal with a Windows agent for ODBC access.

#### Step 1: Install the Windows Agent

On the Windows machine with GlassTrax ODBC access:

1. Download `GlassTraxAPIAgent-X.X.X-Setup.exe` from [Releases](https://github.com/Codename-11/GlassTrax-Bridge/releases)
2. Run the installer
3. Start the agent from the Start Menu or system tray
4. **Save the API key** shown on first run - you'll need it for Docker

The agent runs on port 8001 by default. Verify it's working:

```bash
curl http://localhost:8001/health
```

#### Step 2: Start Docker

On your Docker host (can be the same machine or different):

```bash
# Pull the latest image
docker pull ghcr.io/codename-11/glasstrax-bridge:latest

# Start with agent connection
AGENT_ENABLED=true \
AGENT_URL=http://YOUR_WINDOWS_IP:8001 \
AGENT_KEY=gta_your_key_here \
docker-compose up -d
```

Replace `YOUR_WINDOWS_IP` with the IP address of the Windows machine running the agent.

#### Step 3: Access the Application

- **Portal**: `http://localhost:3000`
- **API**: `http://localhost:3000/api/v1`
- **Swagger**: `http://localhost:3000/api/docs`

On first run, an admin API key is auto-generated and displayed in the Docker logs:

```bash
docker logs glasstrax-bridge
```

::: tip
Look for the "INITIAL ADMIN API KEY GENERATED" message. Save this key - it won't be shown again!
:::

---

### Windows All-in-One (Beta)

::: warning Beta Method
This method is available but considered beta. Docker + Agent is recommended for production.
:::

Run everything directly on Windows with full GlassTrax ODBC access.

#### 1. Clone or Extract the Project

```bash
git clone https://github.com/Codename-11/GlassTrax-Bridge.git
cd GlassTrax-Bridge
```

#### 2. Install Dependencies

```bash
# Python dependencies (using bundled 32-bit Python)
.\python32\python.exe -m pip install -r requirements.txt

# Node dependencies (for portal)
npm install
```

#### 3. Configure Application

First, set up your ODBC DSN in Windows ODBC Data Source Administrator (32-bit).

Then copy and edit the configuration:

```bash
copy config.example.yaml config.yaml
notepad config.yaml
```

Key settings in `config.yaml`:

```yaml
database:
  friendly_name: "TGI Database"
  dsn: "LIVE"         # ODBC Data Source Name
  readonly: true
  timeout: 30
```

#### 4. Initialize Database

```bash
.\python32\python.exe -m alembic upgrade head
```

#### 5. Start the Production Server

```bash
.\run_prod.bat
```

Access at:
- **Portal**: `http://localhost:8000`
- **API**: `http://localhost:8000/api/v1`
- **Swagger**: `http://localhost:8000/api/docs`

::: tip First Run
On first run, an admin API key is auto-generated and displayed. **Save this key!** It won't be shown again.
:::

---

## Verify Installation

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.1.0",
  "glasstrax_connected": true,
  "app_db_connected": true,
  "mode": "agent"
}
```

### Test API Access

```bash
curl -H "X-API-Key: gtb_your_admin_key" http://localhost:8000/api/v1/customers?limit=1
```

## Next Steps

- [Configure authentication](/guide/authentication)
- [Create your first application](/guide/applications)
- [Generate API keys](/guide/api-keys)
- [Agent Setup Guide](/guide/agent-setup)
- [Explore the API](/api/)
