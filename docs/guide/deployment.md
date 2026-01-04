# Deployment

GlassTrax Bridge can be deployed using Docker or run directly on Windows.

## Docker Deployment

### Prerequisites

- Docker and Docker Compose installed
- Access to the GlassTrax-Bridge repository

### Quick Start

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

### Ports

In Docker standalone mode, nginx routes all traffic through port 3000:

| URL | Content |
|-----|---------|
| `http://localhost:3000` | Admin Portal |
| `http://localhost:3000/docs` | User Documentation |
| `http://localhost:3000/api/v1/*` | REST API |
| `http://localhost:3000/api/docs` | OpenAPI (Swagger) |

::: info
Port 8000 (uvicorn) is internal to the container. All external access is through port 3000 via nginx.
:::

### Container Architecture

The single container runs multiple services managed by supervisord:

```
┌─────────────────────────────────────────────┐
│            Docker Container                  │
│            (port 3000 exposed)               │
├─────────────────────────────────────────────┤
│  nginx (reverse proxy)                       │
│    /           → React Portal (static)       │
│    /docs       → VitePress Docs (static)     │
│    /api/*      → uvicorn (internal:8000)     │
│    /health     → uvicorn (internal:8000)     │
├─────────────────────────────────────────────┤
│  uvicorn (internal, not exposed)             │
│    /api/v1/*   → REST API                    │
│    /api/docs   → OpenAPI (Swagger)           │
│    /health     → Health Check                │
└─────────────────────────────────────────────┘
```

### Data Persistence

The SQLite database is stored in a volume mount:

```yaml
volumes:
  - ./data:/app/data
```

### Configuration

Mount your `config.yaml` to customize settings:

```yaml
volumes:
  - ./config.yaml:/app/config.yaml:ro
```

### Environment Variables

Configure via docker-compose.yml:

```yaml
environment:
  - TZ=America/Chicago
```

::: tip
The portal uses relative URLs by default, so `VITE_API_URL` is only needed for non-standard setups.
:::

## Windows Deployment

For full GlassTrax connectivity, run directly on Windows with the Pervasive ODBC driver.

### Option 1: All-in-One (Recommended)

Run everything on a single port with one script:

```powershell
.\run_prod.bat
```

This builds the portal and docs, then serves everything on port 8000:

| URL | Content |
|-----|---------|
| http://localhost:8000 | Admin Portal |
| http://localhost:8000/docs | User Documentation |
| http://localhost:8000/api/v1 | REST API |
| http://localhost:8000/api/docs | OpenAPI (Swagger) |

### Option 2: Agent Only (for Docker)

If Docker handles the portal and API, but you need Windows for ODBC access:

```powershell
.\agent\run_agent.bat
```

This starts the GlassTrax Agent on port 8001. See [Agent Setup](/guide/agent-setup) for details.

## Docker + Windows Agent Mode

Best of both worlds: Docker runs the full API and portal, Windows runs a minimal agent for ODBC access.

### Step 1: Start Agent on Windows

```powershell
.\agent\run_agent.bat
```

On first run, an API key will be generated and displayed. **Save it!**

### Step 2: Find Your Windows IP

```powershell
ipconfig
# Look for IPv4 Address, e.g., 192.168.1.100
```

### Step 3: Start Docker with Agent Configuration

```bash
AGENT_ENABLED=true \
AGENT_URL=http://192.168.1.100:8001 \
AGENT_KEY=gta_your_key_here \
docker-compose up -d
```

Or on PowerShell:
```powershell
$env:AGENT_ENABLED="true"
$env:AGENT_URL="http://192.168.1.100:8001"
$env:AGENT_KEY="gta_your_key_here"
docker-compose up -d
```

### Agent Mode URLs

| URL | Content |
|-----|---------|
| http://localhost:3000 | Portal (Docker) |
| http://localhost:3000/docs | User Docs (Docker) |
| http://localhost:3000/api/v1/* | API (Docker, queries via agent) |
| http://WINDOWS_IP:8001/health | Agent health (direct) |

The Docker API server connects to the Windows agent for GlassTrax database queries.

## Health Checks

The container includes built-in health checks:

```bash
# Check API health
curl http://localhost:8000/health

# Check nginx
curl http://localhost:3000/nginx-health
```

## Updating

To update to a new version:

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs
```

### Can't connect to GlassTrax

The Pervasive ODBC driver is Windows-only. Options:
1. Run the API directly on Windows
2. Use Agent Mode - run the agent on Windows, API in Docker
3. Configure Pervasive for network access

### Agent connection failing

1. Verify agent is running: `curl http://WINDOWS_IP:8001/health`
2. Check API key is correct in Docker environment
3. Ensure Windows firewall allows port 8001
4. Verify network connectivity between Docker and Windows

### Database locked

Only run one instance of the API against the SQLite database. For multiple instances, consider PostgreSQL.
