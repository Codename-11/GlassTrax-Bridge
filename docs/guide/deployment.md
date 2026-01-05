# Deployment

GlassTrax Bridge can be deployed using Docker (recommended) or run directly on Windows.

## Docker + Windows Agent (Recommended)

Best approach: Docker runs the API and portal, Windows runs a minimal agent for ODBC access.

### Step 1: Install Agent on Windows

Download `GlassTraxAPIAgent-X.X.X-Setup.exe` from [Releases](https://github.com/Codename-11/GlassTrax-Bridge/releases) and run the installer. Start the agent from the Start Menu or system tray.

On first run, an API key will be generated and displayed. **Save it!**

### Step 2: Start Docker with Agent Configuration

```bash
AGENT_ENABLED=true \
AGENT_URL=http://YOUR_WINDOWS_IP:8001 \
AGENT_KEY=gta_your_key_here \
docker-compose up -d
```

### Ports (Docker + Agent)

| URL | Content |
|-----|---------|
| `http://localhost:3000` | Admin Portal |
| `http://localhost:3000/api/v1/*` | REST API (queries via agent) |
| `http://localhost:3000/api/docs` | OpenAPI (Swagger) |
| `http://WINDOWS_IP:8001/health` | Agent health check |

Documentation: [GitHub Pages](https://codename-11.github.io/GlassTrax-Bridge/)

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

## Docker Standalone

For testing without GlassTrax database access:

```bash
docker pull ghcr.io/codename-11/glasstrax-bridge:latest
docker-compose up -d
```

Portal on `:3000` (no GlassTrax ODBC access)

## Windows All-in-One (Beta)

::: warning Beta Method
This method is available but considered beta. Docker + Agent is recommended for production.
:::

Run everything on a single port with one script:

```powershell
.\run_prod.bat
```

This builds the portal and serves everything on port 8000:

| URL | Content |
|-----|---------|
| http://localhost:8000 | Admin Portal |
| http://localhost:8000/api/v1 | REST API |
| http://localhost:8000/api/docs | OpenAPI (Swagger) |

Documentation: [GitHub Pages](https://codename-11.github.io/GlassTrax-Bridge/)

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
