# GlassTrax-Bridge

Multi-tenant REST API platform for read-only access to GlassTrax ERP (Pervasive SQL) with a React admin portal.

## Critical Rules

- **Read-only access to GlassTrax** - NEVER suggest changes that could modify the GlassTrax database
- **Two databases**: GlassTrax (Pervasive, read-only) + App DB (SQLite, read-write)
- **32-bit Python required** - Uses bundled `python32/` for Pervasive ODBC compatibility
- **Windows-only for full functionality** - Pervasive ODBC driver is Windows-only

## Internal Documentation

Reference these docs for detailed information:

| Document | Purpose |
|----------|---------|
| `docs-internal/PATTERNS.md` | Development patterns (agent mode, testing, type coercion) |
| `docs-internal/GLASSTRAX-DATABASE.md` | Pervasive schema, column names, SQL quirks |
| `docs-internal/EXTENDING.md` | Adding endpoints, models, migrations |
| `docs-internal/TESTING.md` | Test infrastructure and mocking |
| `docs-internal/API.md` | API architecture details |
| `docs-internal/PORTAL.md` | Portal component patterns |

**Always reference `GLASSTRAX-DATABASE.md` for actual Pervasive column names when writing queries.**

## Versioning

**Single source of truth:** `VERSION` file in project root

```powershell
# Update version
echo "1.1.0" > VERSION
cd portal && npm run sync-version
cd ../docs && npm run sync-version
```

## Quick Start

```powershell
# Development (API + Portal)
npm install && npm run dev

# All services at http://localhost:5173
```

## Pre-Commit Checklist

**CRITICAL: Run before EVERY commit to avoid CI failures:**

```powershell
npm run test                    # All tests must pass
ruff check api/ agent/ --fix    # Python linting
cd portal && npm run format     # Portal formatting
```

## Production Deployment

### Docker + Windows Agent (Recommended)

```powershell
# Windows: install Agent from Releases
# Docker: configure agent connection
AGENT_ENABLED=true AGENT_URL=http://192.168.1.100:8001 AGENT_KEY=gta_xxx docker-compose up -d
```

### Release Process

```powershell
# 1. Update version
echo "1.1.0" > VERSION
cd portal && npm run sync-version && cd ../docs && npm run sync-version && cd ..

# 2. Commit and tag
git add -A && git commit -m "chore: release v1.1.0"
git tag v1.1.0 && git push origin master --tags
```

Release workflow runs tests in parallel, then builds agent installer + Docker image.

## Project Structure

```
GlassTrax-Bridge/
├── api/                      # FastAPI backend
│   ├── services/glasstrax.py # GlassTrax data access
│   └── schemas/              # Pydantic models (use CoercedStr for agent compat)
├── agent/                    # Windows ODBC agent
├── portal/                   # React admin portal
├── docs/                     # VitePress user docs
├── docs-internal/            # Developer docs (PATTERNS.md, etc.)
├── tests/                    # API tests
└── tools/inspect_dsn.py      # Database schema explorer
```

## Configuration

**Location:** `data/config.yaml` (auto-created, Docker volume)

```yaml
database:
  dsn: "LIVE"           # ODBC DSN
  readonly: true        # CRITICAL: Always true

agent:
  enabled: false        # Enable for Docker deployment
  url: "http://localhost:8001"
  api_key: ""           # gta_... prefix
```

## Key Reminders

### Agent Mode
- When `agent.enabled=true`, API queries Windows agent via HTTP
- Agent keys use `gta_` prefix (vs `gtb_` for main API)
- **JOIN queries require explicit column lists** - see `docs-internal/PATTERNS.md`

### Pydantic Schemas
- Use `CoercedStr` type for fields that may arrive as int from agent
- See `api/schemas/order.py` for examples

### Testing
- pyodbc mocked in CI (Windows-only)
- See `docs-internal/TESTING.md` for patterns

### Database
- Use `tools\inspect.bat` to explore GlassTrax schema
- Dates stored as `YYYYMMDD` strings, may arrive as int from agent
- All `CHAR` fields are space-padded - always `.strip()`

### Migrations
```powershell
python32\python.exe -m alembic upgrade head
```

### Documentation
- User docs: https://codename-11.github.io/GlassTrax-Bridge/
- Keep `docs-internal/` updated with patterns and architecture changes
