# GlassTrax API Agent

Windows service that provides ODBC access to GlassTrax ERP via the Bridge API.

## Overview

The agent runs on Windows machines with access to the GlassTrax Pervasive SQL database via ODBC. It exposes a REST API that the main Bridge API calls to query data.

## Architecture

```
agent/
├── __init__.py          # Version from VERSION file
├── main.py              # FastAPI application
├── tray_app.py          # System tray application
├── config.py            # Configuration management
├── auth.py              # API key authentication
├── query.py             # Query service (ODBC)
├── updater.py           # Auto-update functionality
└── icons/               # Tray icons
```

## Auto-Updater

The agent includes automatic update checking and installation via GitHub Releases.

### Configuration

| Setting | Value |
|---------|-------|
| GitHub Owner | `codename-11` |
| GitHub Repo | `GlassTrax-Bridge` |
| Asset Pattern | `*-Setup.exe`, `*_setup.exe`, `*-Installer.exe` |
| Check Delay | 15 seconds after startup |

### How It Works

1. **Startup Check**: 15 seconds after the agent starts, it queries the GitHub Releases API for the latest release
2. **Version Comparison**: Compares current version (from `VERSION` file) with latest release tag
3. **Notification**: If an update is available, shows a system notification and updates the tray menu
4. **Download**: User can trigger download from the tray menu
5. **Install**: Installer is launched automatically after download completes

### Tray Menu Items

| Menu Item | Description |
|-----------|-------------|
| `Check for Updates` / `Update Available!` | Manual check (text changes when update found) |
| `Download Update` | Only visible when update available |
| `View Release Notes` | Opens GitHub releases page in browser |

### UpdateChecker Class

```python
from agent.updater import UpdateChecker, ReleaseInfo

# Create checker with callbacks
checker = UpdateChecker(
    on_update_available=lambda info: print(f"Update: {info.version}"),
    on_check_complete=lambda has_update: print(f"Done: {has_update}"),
    on_download_complete=lambda path: print(f"Downloaded: {path}"),
    on_download_failed=lambda err: print(f"Failed: {err}"),
)

# Async check (non-blocking, with delay)
checker.check_async(delay=15)

# Sync check (blocking)
release = checker.check_sync()
if release:
    print(f"New version: {release.version}")
    checker.download_update()
```

### Version Parsing

Supports multiple version formats:

| Format | Example |
|--------|---------|
| With prefix | `v1.2.3` |
| Without prefix | `1.2.3` |
| Prerelease | `1.2.3-beta`, `1.2.3-rc.1` |

Version comparison rules:
- Stable releases (`1.2.3`) are higher than prereleases (`1.2.3-beta`)
- Prereleases are compared alphabetically (`alpha` < `beta` < `rc`)

### ReleaseInfo Fields

```python
@dataclass
class ReleaseInfo:
    version: str          # "1.7.0" (without v prefix)
    tag_name: str         # "v1.7.0"
    name: str             # Release title
    body: str             # Release notes (markdown)
    html_url: str         # GitHub release page URL
    asset_url: str | None # Download URL for installer
    asset_name: str | None # Installer filename
    published_at: str     # ISO timestamp
```

### Error Handling

The updater handles errors gracefully:

- **Network timeout**: Logged as warning, update check fails silently
- **No releases found**: Logged as info, no notification shown
- **No installer asset**: Download fails with notification
- **Download error**: Notification shown with error message

### Logging

Update-related events are logged to `agent.log`:

```
01/17/26 - 01:00 PM - INFO - Checking for updates (current: v1.6.14)
01/17/26 - 01:00 PM - INFO - Update available: v1.7.0 (current: v1.6.14)
01/17/26 - 01:01 PM - INFO - Downloading update: GlassTrax-Agent-1.7.0-Setup.exe
01/17/26 - 01:01 PM - INFO - Download complete: C:\Users\...\Temp\GlassTrax-Agent-1.7.0-Setup.exe
01/17/26 - 01:01 PM - INFO - Installer launched, exiting agent...
```

## Configuration

Agent configuration is stored in `%APPDATA%\GlassTrax-Agent\agent_config.yaml`.

| Setting | Default | Description |
|---------|---------|-------------|
| `port` | `8001` | HTTP port |
| `dsn` | `LIVE` | ODBC DSN name |
| `api_key` | (generated) | API key for authentication |
| `allowed_tables` | (list) | Tables accessible via query endpoint |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check (no auth required) |
| `POST /query` | Execute query (requires `X-API-Key` header) |

## Development

### Running Locally

```powershell
# From project root
python32\python.exe -m agent.tray_app
```

### Running Tests

```powershell
python32\python.exe -m pytest agent/tests/ -v
```

### Building Installer

The installer is built automatically by GitHub Actions when a version tag is pushed:

```powershell
git tag v1.7.0
git push origin --tags
```

The release workflow creates `GlassTrax-Agent-X.X.X-Setup.exe` and uploads it to the GitHub release.
