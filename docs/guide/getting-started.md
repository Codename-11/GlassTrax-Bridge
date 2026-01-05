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

#### Step 2: Configure Docker Environment

On your Docker host, create a `.env` file:

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

Configure your `.env` file:

```env
# Enable agent mode
AGENT_ENABLED=true

# Windows machine IP running the agent
AGENT_URL=http://192.168.1.100:8001

# API key from agent first run (starts with gta_)
AGENT_KEY=gta_your_key_here

# Optional settings
PORT=3000
TZ=America/New_York
```

::: tip Finding Your Windows IP
Run `ipconfig` on Windows to find the IPv4 address (e.g., 192.168.1.100)
:::

#### Step 3: Start Docker

```bash
docker-compose up -d
```

#### Step 4: First Login

Access the portal at `http://localhost:3000`

**Default credentials:**
- Username: `admin`
- Password: `admin`

::: danger Change Default Password!
The default password is insecure. Change it immediately after first login:
1. Go to **Settings** in the portal
2. Scroll to **Admin Password**
3. Set a strong password
:::

Check the logs for the auto-generated admin API key:

```bash
docker logs glasstrax-bridge
```

Look for "INITIAL ADMIN API KEY GENERATED" - save this key!

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

## First-Time Setup

### Change Default Password

::: danger Security Warning
The default admin password is `admin`. Change it immediately!
:::

**Option 1: Via Portal (Recommended)**
1. Login to the portal
2. Go to **Settings** → **Admin Password**
3. Enter and confirm your new password

**Option 2: Via config.yaml**

Generate a bcrypt hash and add it to your config:

```bash
# Generate password hash
python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"

# Or using Docker
docker run --rm python:3.11-slim python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
```

Add the hash to `config.yaml`:

```yaml
admin:
  username: "admin"
  password_hash: "$2b$12$..."  # paste your hash here
```

### Save Your API Keys

Two types of API keys are generated on first run:

| Key Type | Prefix | Purpose |
|----------|--------|---------|
| Admin API Key | `gtb_` | Full API access, portal authentication |
| Agent API Key | `gta_` | Agent-to-API communication only |

Both are shown only once. Store them securely!

---

## Verify Installation

### Health Check

```bash
# Docker
curl http://localhost:3000/health

# Windows
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.2.0",
  "glasstrax_connected": true,
  "app_db_connected": true,
  "mode": "agent"
}
```

### Test API Access

```bash
curl -H "X-API-Key: gtb_your_admin_key" http://localhost:3000/api/v1/customers?limit=1
```

---

## Docker Compose Reference

Here's a complete `docker-compose.yml` example:

```yaml
version: '3.8'

services:
  glasstrax-bridge:
    image: ghcr.io/codename-11/glasstrax-bridge:latest
    container_name: glasstrax-bridge
    ports:
      - "${PORT:-3000}:80"
    volumes:
      - ./data:/app/data
    environment:
      - GLASSTRAX_AGENT_ENABLED=${AGENT_ENABLED:-false}
      - GLASSTRAX_AGENT_URL=${AGENT_URL:-http://host.docker.internal:8001}
      - GLASSTRAX_AGENT_KEY=${AGENT_KEY:-}
      - GLASSTRAX_AGENT_TIMEOUT=${AGENT_TIMEOUT:-30}
      - TZ=${TZ:-America/New_York}
    restart: unless-stopped
```

With `.env` file:

```env
AGENT_ENABLED=true
AGENT_URL=http://192.168.1.100:8001
AGENT_KEY=gta_your_key_here
PORT=3000
TZ=America/New_York
```

---

## Next Steps

- [Configure authentication](/guide/authentication)
- [Create your first application](/guide/applications)
- [Generate API keys](/guide/api-keys)
- [Agent Setup Guide](/guide/agent-setup)
- [Explore the API](/api/)
