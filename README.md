<p align="center">
  <img src="assets/logo.svg" alt="GlassTrax Bridge" width="400">
</p>

<h1 align="center">GlassTrax Bridge</h1>

<p align="center">
A multi-tenant API platform for secure, read-only access to GlassTrax ERP data via Pervasive SQL.
</p>

## Features

- **REST API Server** - FastAPI-based API with OpenAPI documentation
- **Admin Portal** - React web interface for managing API keys and tenants
- **Settings UI** - Edit config.yaml from the portal (preserves comments)
- **Multi-Tenant Architecture** - Isolate access by application/tenant
- **API Key Authentication** - Secure, hashed key storage with bcrypt
- **API Key Expiration** - Automatic enforcement of key expiration dates
- **Access Logging** - Full audit trail with filtering and CSV export
- **Database Migrations** - Alembic-managed schema versioning
- **Agent Mode** - Docker deployment with Windows ODBC agent
- **Dark Mode** - Light/dark/system theme support in portal
- **Read-Only Access** - Safe querying without data modification risk

## Installation

### Prerequisites

- **Windows** (for GlassTrax ODBC access)
- **Python 3.11 32-bit** (required for Pervasive ODBC driver)
- **Node.js 18+** (for admin portal and docs)
- **Pervasive ODBC Client** installed and configured

### 1. Clone Repository

```powershell
git clone https://github.com/Codename-11/GlassTrax-Bridge.git
cd GlassTrax-Bridge
```

### 2. Set Up Python Environment

Download and extract 32-bit Python 3.11 to `python32/` directory, or use your system Python (must be 32-bit).

```powershell
# Install Python dependencies
python32\python.exe -m pip install -r requirements.txt
```

### 3. Configure Application

```powershell
# Copy example configs
copy config.example.yaml config.yaml
copy agent_config.example.yaml agent_config.yaml

# Edit config.yaml with your settings
notepad config.yaml
```

Key settings in `config.yaml`:
- `database.dsn` - Your ODBC Data Source Name (configured in Windows ODBC Administrator 32-bit)
- `database.friendly_name` - Display name for the UI
- `admin.password_hash` - Set a secure password hash for production

### 4. Initialize Database

```powershell
# Run database migrations
python32\python.exe -m alembic upgrade head
```

### 5. Start Development Server

```powershell
# One-click start (API + Portal + Docs)
.\run_dev.bat

# Or use npm
npm install
npm run dev
```

On first startup, an admin API key is auto-generated:

```
======================================================================
  INITIAL ADMIN API KEY GENERATED
======================================================================

  Key: gtb_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

  IMPORTANT: Save this key now! It will NOT be shown again.
  This key has full admin permissions.

======================================================================
```

### 6. Access the Application

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Admin Portal |
| http://localhost:5173/docs | User Documentation |
| http://localhost:5173/api/docs | API Reference (Swagger) |
| http://localhost:5173/api/v1/* | REST API endpoints |

## Authentication

### Admin Portal Login

Two authentication methods are supported:

1. **Username/Password** - Configure in `config.yaml`:
   ```yaml
   admin:
     username: "admin"
     # Generate: python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
     password_hash: "$2b$12$..."
   ```
   Default credentials (if no hash set): `admin` / `admin`

2. **API Key** - Use any admin API key (starting with `gtb_`) as the password

### API Authentication

All API endpoints require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: gtb_your_key_here" http://localhost:8000/api/v1/customers
```

## API Endpoints

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/health` | GET | Health check | None |
| `/api/v1/customers` | GET | List customers | API Key |
| `/api/v1/customers/{id}` | GET | Get customer | API Key |
| `/api/v1/orders` | GET | List orders | API Key |
| `/api/v1/orders/{id}` | GET | Get order | API Key |
| `/api/v1/admin/tenants` | GET/POST | Manage applications | Admin Key |
| `/api/v1/admin/api-keys` | GET/POST | Manage API keys | Admin Key |
| `/api/v1/admin/access-logs` | GET | View access logs | Admin Key |
| `/api/v1/admin/config` | GET/PATCH | View/update configuration | Admin Key |
| `/api/v1/admin/diagnostics` | GET | System diagnostics | Admin Key |
| `/api/v1/admin/login` | POST | Admin login (JWT) | None |

Full API documentation available at http://localhost:8000/api/docs

## Project Structure

```
GlassTrax-Bridge/
├── api/                      # FastAPI application
│   ├── main.py               # Application entry point
│   ├── config.py             # Settings management
│   ├── routers/              # API endpoints
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # GlassTrax data access
│   ├── middleware/           # Auth & request logging
│   └── utils/                # Shared utilities
├── agent/                    # GlassTrax Agent (for Docker deployments)
│   ├── run_agent.bat         # Start agent manually
│   └── install_service.bat   # Install as Windows Service
├── portal/                   # React admin portal (Vite + shadcn)
│   └── src/
│       ├── components/       # UI components
│       ├── pages/            # Route pages
│       └── lib/              # API client, auth
├── docs/                     # VitePress user documentation
├── docs-internal/            # Internal developer docs
├── migrations/               # Alembic database migrations
│   ├── versions/             # Migration scripts
│   └── env.py                # Migration environment
├── docker/                   # Docker configuration
├── config.example.yaml       # Configuration template
├── agent_config.example.yaml # Agent configuration template
├── alembic.ini               # Alembic configuration
├── VERSION                   # Central version file
├── run_dev.bat               # One-click dev startup
├── run_prod.bat              # Windows production
└── requirements.txt          # Python dependencies
```

## Database Migrations

GlassTrax Bridge uses Alembic for database schema management.

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

The API checks for pending migrations on startup and displays a warning if updates are needed.

## Production Deployment

### Windows (with GlassTrax ODBC)

```powershell
.\run_prod.bat
```

Builds and serves everything on port 8000:
- Portal at `/`
- User Docs at `/docs`
- API at `/api/v1`
- Swagger at `/api/docs`

### Docker Standalone

```bash
docker-compose up -d
```

Portal on `:3000` (no GlassTrax ODBC access - use Agent Mode)

### Docker + Windows Agent (Agent Mode)

Best option: Docker runs full API + portal, Windows runs minimal agent for ODBC access.

**Step 1: On Windows** - Start the GlassTrax Agent:
```powershell
.\agent\run_agent.bat
```
Save the API key shown on first run!

**Step 2: On Docker host** - Configure agent connection:
```bash
AGENT_ENABLED=true \
AGENT_URL=http://192.168.1.100:8001 \
AGENT_KEY=gta_your_key_here \
docker-compose up -d
```

### Agent Installer (Recommended)

For easier deployment, download the standalone Windows installer from [Releases](https://github.com/Codename-11/GlassTrax-Bridge/releases):

- Includes 32-bit Python runtime (no Python installation needed)
- System tray application with start/stop controls
- Optional auto-start on Windows boot

```powershell
# Or build the installer locally (requires Inno Setup 6)
.\build_agent.ps1
```

### Docker Images

Pull from GitHub Container Registry:

```bash
# Latest version
docker pull ghcr.io/codename-11/glasstrax-bridge:latest

# Specific version
docker pull ghcr.io/codename-11/glasstrax-bridge:1.0.0
```

## Versioning

Version is managed via the `VERSION` file in project root.

```powershell
# Update version
echo "1.1.0" > VERSION

# Sync to package.json files
cd portal && npm run sync-version
cd ../docs && npm run sync-version
```

## Development

See [docs-internal/DEVELOPMENT.md](docs-internal/DEVELOPMENT.md) for detailed local development guide.

### One-Click Development

```powershell
.\run_dev.bat
```

Starts all services in a single terminal with color-coded output.

## Documentation

- [Development Guide](docs-internal/DEVELOPMENT.md) - Local setup and workflows
- [API Reference](docs-internal/API.md) - REST API endpoints
- [Portal Guide](docs-internal/PORTAL.md) - Admin portal usage
- [Extending Guide](docs-internal/EXTENDING.md) - Adding endpoints and migrations
- VitePress Docs: Run `cd docs && npm run dev`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Driver not found | Install Pervasive ODBC client, verify with `pyodbc.drivers()` |
| Connection timeout | Increase `timeout` in config.yaml |
| API key invalid | Verify key is active and not expired |
| CORS errors | Check API server is running on expected port |
| Migration errors | Run `alembic upgrade head`, check `alembic current` |

## Security Notes

- **Change default password** - Set `password_hash` in config.yaml for production
- **Secure API keys** - Keys are shown only once when created
- **Key expiration** - Expired keys are automatically rejected
- **Read-only database** - All GlassTrax connections are read-only by design
- **Config files gitignored** - `config.yaml` and `agent_config.yaml` contain secrets

## License

Internal use only.
