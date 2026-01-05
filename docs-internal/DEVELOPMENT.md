# GlassTrax Bridge - Development Guide

Quick reference for local development on Windows.

## Prerequisites

- **Pervasive ODBC Driver** - 32-bit client interface (required for GlassTrax access)
- **Node.js 18+** - For portal development
- **Git** - Version control

The 32-bit Python is bundled in `python32/` - no separate installation needed.

## Quick Start

### One-Click Development (Recommended)

```powershell
# Double-click or run from terminal:
.\run_dev.bat
```

This starts all services in a single terminal with color-coded output:
- `[API]` - FastAPI server with hot-reload (blue)
- `[Portal]` - React dev server (green)
- `[Docs]` - VitePress dev server (magenta)

Press `Ctrl+C` to stop all services.

### Alternative: npm run dev

```powershell
npm install     # First time only (installs concurrently)
npm run dev
```

### Manual Startup

**API Server:**
```powershell
.\python32\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

**Portal:**
```powershell
cd portal
npm install     # First time only
npm run dev
```

**VitePress Docs:**
```powershell
cd docs
npm install     # First time only
npm run dev
```

### URLs

**All services accessible from single port (5173):**

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Portal (main UI) |
| http://localhost:5173/docs | User Documentation |
| http://localhost:5173/api/docs | API Reference (Swagger) |
| http://localhost:5173/api/v1/* | REST API endpoints |
| http://localhost:5173/health | Health check |

Vite proxies `/api`, `/docs`, and `/health` to their respective backend services.
This matches the production URL structure.

> **Note:** Backend services also available directly for debugging:
> - API: http://localhost:8000
> - VitePress: http://localhost:5174

First run generates an admin API key - **save it!**

## First-Time Setup

### 1. Copy Configuration Files

```powershell
copy config.example.yaml config.yaml
copy agent_config.example.yaml agent_config.yaml
```

### 2. Edit Configuration

Edit `config.yaml` with your database DSN and settings.

### 3. Install Dependencies

```powershell
# Python dependencies
.\python32\python.exe -m pip install -r requirements.txt

# Node dependencies
npm install
```

### 4. Initialize Database

```powershell
.\python32\python.exe -m alembic upgrade head
```

## Configuration

### config.yaml

Main configuration file in project root:

```yaml
database:
  friendly_name: "TGI Database"  # Display name in UI
  dsn: "LIVE"                    # ODBC Data Source Name (configured in Windows ODBC Administrator)
  readonly: true                 # Safety: read-only access
  timeout: 30

application:
  timezone: "America/New_York"   # IANA timezone
  logging:
    level: "INFO"

admin:
  username: "admin"
  # password_hash: "..."     # bcrypt hash (optional)

agent:
  enabled: false             # Enable for Docker + Agent mode
  url: "http://localhost:8001"
  api_key: ""
  timeout: 30
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GLASSTRAX_HOST` | `0.0.0.0` | API bind address |
| `GLASSTRAX_PORT` | `8000` | API port |
| `GLASSTRAX_DEBUG` | `false` | Debug mode (enables hot reload) |

## Common Tasks

### Reset the Database

Delete `data/glasstrax_bridge.db` and restart the API - a new admin key will be generated.

Or use the Portal's Diagnostics page → Danger Zone → Reset Database.

### Generate a New API Key

Via Portal:
1. Login to Portal
2. Go to API Keys page
3. Click "New API Key"

Via API:
```bash
curl -X POST http://localhost:8000/api/v1/admin/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": 1, "name": "My Key", "permissions": ["customers:read"]}'
```

### Build Portal for Production

```powershell
cd portal
npm run build
# Output in portal/dist/
```

### Build VitePress Docs

```powershell
cd docs
npm run build
# Output in docs/.vitepress/dist/
```

## Project Structure

```
GlassTrax-Bridge/
├── api/                     # FastAPI backend
│   ├── main.py              # App entry point
│   ├── config.py            # Settings management
│   ├── database.py          # SQLite connection
│   ├── routers/             # API route handlers
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── middleware/          # Auth & request logging
│   └── services/            # GlassTrax data access
├── portal/                  # React admin portal
│   ├── src/
│   │   ├── pages/           # Route components
│   │   ├── components/      # UI components
│   │   └── lib/             # API client, utilities
│   └── package.json
├── docs/                    # VitePress documentation
│   ├── .vitepress/config.ts # VitePress config (base: /docs/)
│   ├── index.md             # Home page
│   └── guide/               # Guide pages
├── docs-internal/           # Internal documentation
├── data/                    # SQLite database (auto-created)
├── python32/                # Bundled 32-bit Python
├── docker/                  # Docker files
│   ├── Dockerfile
│   ├── nginx.conf
│   └── supervisord.conf
├── package.json             # Root scripts (npm run dev)
├── config.yaml              # Configuration file
├── docker-compose.yml       # Container orchestration
├── run_dev.bat              # One-click dev startup
├── run_prod.bat             # Windows production
├── agent/                   # GlassTrax API Agent (for Docker)
│   └── run_agent.bat        # Start agent
├── VERSION                  # Central version file
└── requirements.txt         # Python dependencies
```

## Troubleshooting

### "ODBC driver not found"

The Pervasive ODBC driver must be installed on Windows. Check:
1. ODBC Data Source Administrator (32-bit)
2. Verify "Pervasive ODBC Client Interface" is listed

### API returns 401 Unauthorized

- Check your API key is valid and active
- Verify the `X-API-Key` header (for API) or `Authorization: Bearer` (for portal)

### Portal can't connect to API

1. Make sure API is running on port 8000
2. Check CORS settings in `api/main.py`
3. Verify `VITE_API_URL` in portal environment

### Database locked (SQLite)

Only one process should write to SQLite at a time. If using multiple API instances, consider switching to PostgreSQL.

## Running Tests

```powershell
# API tests (if available)
.\python32\python.exe -m pytest api/tests/

# Portal tests
cd portal
npm test
```

## Database Migrations

The app uses Alembic for database schema migrations.

```powershell
# Check current version
python32\python.exe -m alembic current

# Apply pending migrations
python32\python.exe -m alembic upgrade head

# Create new migration after model changes
python32\python.exe -m alembic revision --autogenerate -m "Description"

# Rollback one migration
python32\python.exe -m alembic downgrade -1
```

For existing databases without Alembic tracking, stamp first:

```powershell
python32\python.exe -m alembic stamp head
```

See [EXTENDING.md](./EXTENDING.md#database-migrations) for detailed migration guide.

## Production on Windows

For production use on Windows (with GlassTrax ODBC access):

```powershell
.\run_prod.bat
```

This will:
1. Build the portal and VitePress docs
2. Start the API server serving everything on port 8000

| URL | Content |
|-----|---------|
| http://localhost:8000 | Portal |
| http://localhost:8000/docs | User documentation |
| http://localhost:8000/api/docs | Swagger/OpenAPI |
| http://localhost:8000/api/v1 | REST API |

## Docker Deployment

### Standalone Mode (no GlassTrax)

```powershell
docker-compose up --build
```

API runs in container but won't have GlassTrax ODBC access.

### Agent Mode (GlassTrax via Windows)

Best of both worlds: Docker runs full API + portal, Windows runs minimal agent for ODBC access.

**Step 1:** On Windows, start the GlassTrax API Agent:
```powershell
.\agent\run_agent.bat
```
Save the API key shown on first run!

**Step 2:** Find Windows IP:
```powershell
ipconfig
# Look for IPv4 Address, e.g., 192.168.1.100
```

**Step 3:** Start Docker with agent configuration:
```powershell
$env:AGENT_ENABLED="true"
$env:AGENT_URL="http://192.168.1.100:8001"
$env:AGENT_KEY="gta_your_key_here"
docker-compose up -d
```

Or on Linux/Mac:
```bash
AGENT_ENABLED=true AGENT_URL=http://192.168.1.100:8001 AGENT_KEY=gta_xxx docker-compose up -d
```

### Docker URLs

| URL | Content |
|-----|---------|
| http://localhost:3000 | Portal |
| http://localhost:3000/docs | User documentation |
| http://localhost:3000/api/v1 | API (queries via agent) |
| http://WINDOWS_IP:8001/health | Agent health check |

## Versioning

The project uses a central `VERSION` file in the project root.

### How It Works

| Component | How version is read |
|-----------|---------------------|
| API | `api/config.py` reads `VERSION` file at runtime |
| Portal | `package.json` (sync manually or run `npm run sync-version`) |
| Docs | `package.json` (sync manually or run `npm run sync-version`) |

### Updating the Version

1. Edit the `VERSION` file in the project root
2. Sync the package.json files:

```powershell
cd portal && npm run sync-version
cd ../docs && npm run sync-version
```

The API will automatically pick up the new version on restart.

## Building Agent Installer

The GlassTrax API Agent can be packaged as a standalone Windows installer with system tray support.

### Prerequisites

1. **Inno Setup 6** - Download from https://jrsoftware.org/isdl.php
2. **PowerShell 5.1+** - Included with Windows 10/11

### Build Steps

```powershell
# Build installer
.\build_agent.ps1

# Clean build from scratch
.\build_agent.ps1 -Clean

# Build without compiling installer (for testing)
.\build_agent.ps1 -SkipInstaller

# Or use the batch wrapper
BUILD_AGENT.bat
```

The script will:
1. Download Python 3.11 32-bit embeddable package
2. Enable pip and install agent dependencies
3. Copy agent source files
4. Generate Inno Setup script
5. Compile the installer

Output: `dist/GlassTraxAPIAgent-X.X.X-Setup.exe`

### Agent Run Modes

| Mode | Flag | Description |
|------|------|-------------|
| Tray | `--tray` | System tray with start/stop controls (default for EXE) |
| Service | `--service` | Background service for NSSM |
| Console | `--console` | Console output for debugging |

### Tray Icon States

| State | Color | Description |
|-------|-------|-------------|
| Running | Green | Agent is running and healthy |
| Stopped | Red | Agent is stopped |
| Error | Yellow | Agent encountered an error |

### Agent Configuration & Logs

When installed, the agent stores configuration and logs in `%APPDATA%\GlassTrax API Agent\`:
- `agent_config.yaml` - Configuration file
- `agent.log` - Log file (recreated on each run)

Access via tray menu: "Open Config Folder" or "View Log File".

## CI/CD Workflows

GitHub Actions workflows in `.github/workflows/`:

### Release Workflow (`release.yml`)

Triggered on version tags (`v*.*.*`):

1. Validates VERSION file matches tag
2. Builds Windows Agent installer
3. Builds and pushes Docker image to ghcr.io
4. Creates GitHub Release with artifacts

```powershell
# Trigger a release
echo "1.2.0" > VERSION
cd portal && npm run sync-version
cd ../docs && npm run sync-version
git add -A && git commit -m "chore: release v1.2.0"
git tag v1.2.0
git push origin main --tags
```

### Docs Workflow (`docs.yml`)

Triggered on changes to `docs/` on main branch:

1. Builds VitePress with GitHub Pages base URL
2. Deploys to GitHub Pages

**Live docs:** https://codename-11.github.io/GlassTrax-Bridge/

> **Note:** GitHub Pages uses base URL `/GlassTrax-Bridge/` while the bundled app uses `/docs/`. The VitePress config reads `VITEPRESS_BASE` env var to handle this.

### Regenerating Icons

```powershell
.\python32\python.exe agent\icons\generate_icons.py
```

## VS Code Setup

Recommended extensions:
- Python (Microsoft)
- Pylance
- ESLint
- Tailwind CSS IntelliSense
- Volar (Vue - for VitePress)

`.vscode/settings.json`:
```json
{
  "python.pythonPath": "./python32/python.exe",
  "python.analysis.typeCheckingMode": "basic",
  "editor.formatOnSave": true
}
```
