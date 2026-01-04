# GlassTrax-Bridge

Multi-tenant REST API platform for read-only access to GlassTrax ERP (Pervasive SQL) with a React admin portal.

## Critical Rules

- **Read-only access to GlassTrax** - NEVER suggest changes that could modify the GlassTrax database
- **Two databases**: GlassTrax (Pervasive, read-only) + App DB (SQLite, read-write)
- **32-bit Python required** - Uses bundled `python32/` for Pervasive ODBC compatibility
- **Windows-only for full functionality** - Pervasive ODBC driver is Windows-only

## Versioning

**Single source of truth:** `VERSION` file in project root

| Component | How version is read |
|-----------|---------------------|
| API | `api/config.py` → `get_version()` reads `VERSION` at runtime |
| Portal | `portal/package.json` → run `npm run sync-version` |
| Docs | `docs/package.json` → run `npm run sync-version` |

To update version:
```powershell
echo "1.1.0" > VERSION
cd portal && npm run sync-version
cd ../docs && npm run sync-version
```

## Quick Start (Windows)

```powershell
# One-click development (API + Portal + Docs in single terminal)
.\run_dev.bat

# Or use npm directly
npm install && npm run dev
```

**All services accessible from single port (5173):**

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Portal (main UI) |
| http://localhost:5173/docs | User Documentation |
| http://localhost:5173/api/docs | API Reference (Swagger) |
| http://localhost:5173/api/v1/* | REST API endpoints |
| http://localhost:5173/health | Health check |

Vite proxies `/api`, `/docs`, and `/health` to their respective backend services.
Uses `concurrently` for color-coded output. `Ctrl+C` stops all.

## Production Deployment

### Windows (recommended for GlassTrax ODBC)

```powershell
.\run_prod.bat
```

Everything on port 8000: Portal `/`, Docs `/docs`, API `/api/v1`, Swagger `/api/docs`

### Docker Standalone

```powershell
docker-compose up -d
```

Port 3000: Portal `/`, Docs `/docs`, API `/api/v1` (no GlassTrax access)

### Docker + Windows Agent (Agent Mode)

```powershell
# Windows: start the GlassTrax Agent (handles ODBC)
.\agent\run_agent.bat

# Docker host: configure to use agent
AGENT_ENABLED=true AGENT_URL=http://192.168.1.100:8001 AGENT_KEY=gta_xxx docker-compose up -d
```

Port 3000: Portal + API with GlassTrax access via agent

### GlassTrax Agent Only (Windows)

```powershell
# Start agent for Docker/external API to connect
.\agent\run_agent.bat

# Or install as Windows Service (NSSM)
.\agent\install_service.bat
```

Runs minimal agent on port 8001 with ODBC access

### Agent Installer (Standalone EXE)

Download from [Releases](https://github.com/Codename-11/GlassTrax-Bridge/releases) or build locally:

```powershell
# Build installer (requires Inno Setup 6)
.\build_agent.ps1

# Or use the batch wrapper
BUILD_AGENT.bat
```

The installer includes:
- 32-bit Python runtime (for Pervasive ODBC)
- System tray application with start/stop controls
- Auto-start on Windows boot (optional)

## Building Releases

### Local Agent Build

```powershell
# Build installer
.\build_agent.ps1

# Clean build from scratch
.\build_agent.ps1 -Clean

# Build without compiling installer (for testing)
.\build_agent.ps1 -SkipInstaller
```

Output: `dist/GlassTraxAgent-X.X.X-Setup.exe`

### Automated Releases (GitHub Actions)

Push a version tag to trigger the release workflow:

```powershell
# Update VERSION file
echo "1.1.0" > VERSION

# Sync versions to package.json files
cd portal && npm run sync-version
cd ../docs && npm run sync-version

# Commit and tag
git add -A
git commit -m "chore: release v1.1.0"
git tag v1.1.0
git push origin main --tags
```

The workflow (`.github/workflows/release.yml`) will:
1. Validate VERSION file matches tag
2. Build Windows Agent installer
3. Build and push Docker image to ghcr.io
4. Create GitHub Release with EXE artifact

### Docker Images

Pull from GitHub Container Registry:

```bash
# Latest
docker pull ghcr.io/codename-11/glasstrax-bridge:latest

# Specific version
docker pull ghcr.io/codename-11/glasstrax-bridge:1.1.0
```

## Project Structure

```
GlassTrax-Bridge/
├── VERSION                   # Central version file
├── CLAUDE.md                 # Claude context (this file)
├── README.md                 # Project documentation
├── config.yaml               # Database & app configuration
├── agent_config.yaml         # Agent configuration (Windows)
├── pyproject.toml            # Python project config (ruff, pyright, pytest)
├── requirements.txt          # Python dependencies
├── api/                      # FastAPI backend
│   ├── main.py               # App entry point
│   ├── config.py             # Settings (reads VERSION)
│   ├── config_schema.py      # Pydantic config validation
│   ├── database.py           # SQLite connection
│   ├── routers/              # API endpoints
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── middleware/           # Auth & request logging
│   ├── services/             # GlassTrax data access + agent_client
│   └── utils/                # Shared utilities (logger)
├── agent/                    # GlassTrax Agent (Windows ODBC)
│   ├── main.py               # Agent FastAPI app
│   ├── cli.py                # CLI entry point (--tray/--service/--console)
│   ├── tray_app.py           # System tray application (pystray)
│   ├── config.py             # Agent configuration
│   ├── query.py              # ODBC query execution
│   ├── auth.py               # API key authentication
│   ├── schemas.py            # Request/response models
│   ├── icons/                # Tray icons (.ico files)
│   ├── requirements_agent.txt # Minimal deps for standalone build
│   ├── run_agent.bat         # Manual startup script
│   ├── install_service.bat   # NSSM service installation
│   └── uninstall_service.bat # NSSM service removal
├── portal/                   # React admin portal (Vite + shadcn)
│   ├── .prettierrc           # Prettier config
│   └── src/
│       ├── pages/            # Dashboard, APIKeys, Tenants, Logs, Settings
│       ├── components/       # UI components
│       └── lib/              # API client, auth utilities
├── docs/                     # VitePress user documentation
├── docs-internal/            # Internal markdown docs
├── migrations/               # Alembic database migrations
│   ├── env.py                # Migration environment
│   ├── versions/             # Migration scripts
│   └── README.md             # Migration guide
├── data/                     # SQLite database (gitignored)
├── python32/                 # Bundled 32-bit Python for ODBC
├── docker/                   # Docker configuration
│   ├── Dockerfile            # Single container build
│   ├── nginx.conf            # Portal + docs routing
│   └── supervisord.conf      # Process management
├── alembic.ini               # Alembic configuration
├── docker-compose.yml        # Container orchestration
├── run_dev.bat               # Development startup
├── run_prod.bat              # Production build & run
├── build_agent.ps1           # Agent installer build script
├── BUILD_AGENT.bat           # Build wrapper
├── .github/workflows/        # GitHub Actions
│   └── release.yml           # Automated release workflow
├── build/                    # Build output (gitignored)
├── dist/                     # Installer output (gitignored)
└── .build_cache/             # Python embed cache (gitignored)
```

## Configuration

### config.yaml

```yaml
database:
  friendly_name: "TGI Database"    # Shown in UI
  dsn: "LIVE"                      # ODBC Data Source Name (configured in Windows ODBC Administrator)
  readonly: true                    # CRITICAL: Always true
  timeout: 30

application:
  timezone: "America/New_York"      # IANA timezone

admin:
  username: "admin"
  # password_hash: "..."            # bcrypt hash (optional)

agent:
  enabled: false                    # Enable agent mode for Docker deployment
  url: "http://localhost:8001"      # GlassTrax Agent URL
  api_key: ""                       # Agent API key (gta_...)
  timeout: 30                       # Request timeout for agent queries
```

## API Authentication

### On First Run
An admin API key is auto-generated and displayed in console. **Save it!**

### API Keys
- Prefix: `gtb_XXXXXXXXXXXX...`
- Header: `X-API-Key: <key>`
- Stored: bcrypt-hashed in SQLite

### Portal Auth
- JWT Bearer token after login
- Login with admin username/password OR API key as password

## Key API Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | None | Health check + version + mode |
| `GET /api/v1/customers` | API Key | List customers |
| `GET /api/v1/orders` | API Key | List orders |
| `GET /api/v1/admin/tenants` | Admin | Manage applications |
| `GET /api/v1/admin/api-keys` | Admin | Manage API keys |
| `GET /api/v1/admin/access-logs` | Admin | View request logs |
| `GET/PATCH /api/v1/admin/config` | Admin | View/update config.yaml |
| `GET /api/v1/admin/dsns` | Admin | List available ODBC DSNs |
| `POST /api/v1/admin/test-dsn` | Admin | Test DSN connection |
| `POST /api/v1/admin/test-agent` | Admin | Test agent connection |
| `POST /api/v1/admin/change-password` | Admin | Change admin password |
| `GET /api/v1/admin/diagnostics` | Admin | System health checks |
| `POST /api/v1/admin/restart-server` | Admin | Restart API server |
| `POST /api/v1/admin/reset-database` | Admin | Reset app database |

## UI Components

Portal uses custom status indicators with animated pulse effects:
- `StatusIndicator` - Blinking dot for online/offline/warning states
- `ConnectionStatus` - Database connection display with friendly name

Located in: `portal/src/components/ui/status-indicator.tsx`

## Settings Page

The portal has a Settings page (`/settings`) that allows editing config.yaml:
- Uses `ruamel.yaml` to preserve comments and formatting
- **Pydantic validation** via `api/config_schema.py` before saving
- Tracks dirty state with unsaved changes warning
- Indicates which fields require server restart (e.g., DSN changes)
- **DSN dropdown** - Lists available ODBC DSNs from system, highlights Pervasive DSNs
- **Test DSN button** - Tests connection before saving, shows table count
- **Read-Only Mode** - Enforced and disabled in UI (protects ERP data)
- **Password change** - Update admin password via `/admin/change-password`
- **Agent settings** - Configure GlassTrax Agent connection (url, api_key, timeout)
- **Test Agent button** - Tests agent connection before saving
- **Docs link** - Quick access to VitePress documentation
- Excludes sensitive fields (password_hash)

## Development Tooling

```powershell
# Python linting/formatting (configured in pyproject.toml)
ruff check api/ --fix    # Lint and auto-fix
ruff format api/         # Format code

# Portal formatting
cd portal && npm run format        # Format with Prettier
cd portal && npm run format:check  # Check formatting
cd portal && npm run lint          # ESLint
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI + Uvicorn |
| App DB | SQLite + SQLAlchemy |
| GlassTrax | Pervasive SQL via pyodbc (32-bit) |
| Portal | React 19 + Vite + shadcn/ui + TanStack Query |
| Docs | VitePress |
| Container | Docker + nginx + supervisord |

## Notes for Claude

1. **Always use `python32/`** - The bundled 32-bit Python is required for Pervasive ODBC (Windows direct mode)
2. **Check VERSION file** - Version is centralized, not hardcoded
3. **Portal uses TanStack Query** - Data fetching with automatic caching/refetching
4. **Status indicators animate** - Use CSS `animate-ping` for pulse effect
5. **Docker is single-container** - nginx + uvicorn managed by supervisord
6. **VitePress base: '/docs/'** - Served at /docs on both dev (via proxy) and prod (nginx)
7. **Root package.json** - Has `npm run dev` using concurrently for all services
8. **Diagnostics page** - Has server restart and database reset functionality
9. **friendly_name in config.yaml** - Displayed in Dashboard connection status
10. **api/utils/ contains logger** - `setup_logger` imported by API middleware
11. **Documentation** - Always keep it up to date for both internal and user-facing documentation
12. **TODO.md** - Keep it up to date with current features and TODOs. Leverage it for new features and TODOs.
13. **Config validation** - `api/config_schema.py` validates config.yaml; `config_service.py` handles hot-reload
14. **Prettier for portal** - Run `npm run format` in portal/ before committing
15. **Vite proxy** - Dev server proxies `/api`, `/docs`, `/health` so all URLs work from port 5173
16. **API base URL** - Portal uses relative URLs (empty base), Vite proxies in dev, same-origin in prod
17. **ruff for API** - Run `ruff check api/ --fix` and `ruff format api/` before committing
18. **Agent mode** - When `agent.enabled=true`, API uses `AgentClient` to query Windows agent via HTTP
19. **GlassTrax Agent** - Minimal FastAPI app in `agent/` that handles ODBC queries on Windows
20. **Agent API key prefix** - Agent keys use `gta_` prefix (vs `gtb_` for main API)
21. **pyodbc optional** - Not available in Docker; API gracefully handles missing pyodbc in agent mode
22. **Extending the API** - See `docs-internal/EXTENDING.md` for adding new endpoints, models, and migrations
23. **Alembic migrations** - Run `python32\python.exe -m alembic upgrade head` after pulling changes
24. **Existing databases** - Stamp with `alembic stamp head` before first migration run
25. **New models** - Import in `api/models/__init__.py` AND `migrations/env.py` for autogenerate
26. **Agent CLI modes** - `--tray` (default EXE), `--service` (NSSM), `--console` (debug)
27. **Agent tray icons** - Store in `agent/icons/` as .ico files (64x64), generated via `generate_icons.py`
28. **Build cache** - `.build_cache/` stores downloaded Python embed (gitignored)
29. **Inno Setup 6** - Required for building installer, download from jrsoftware.org
30. **Release workflow** - Push `vX.X.X` tag to trigger build + release on GitHub Actions
31. **Docker registry** - Images published to `ghcr.io/codename-11/glasstrax-bridge`
32. **Agent version** - Reads from VERSION file dynamically (not hardcoded)
