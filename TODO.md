# GlassTrax Bridge - TODO

## Agent
- [ ] Allow agent to check for updates and install them. Include check for updates in the context menu of the agent tray icon.

Features and configuration options that are defined but not yet implemented.

## Not Yet Implemented

### Feature Flags (`config.yaml` → `features`)

These flags are exposed in the Settings UI but have no functional effect:

| Flag | Description | Implementation Notes |
|------|-------------|---------------------|
| `enable_caching` | Query result caching | Would cache GlassTrax query results to reduce database load. Consider Redis or in-memory LRU cache. |
| `enable_exports` | Data export functionality | Exports currently work regardless of this flag. Need to add gating logic to export endpoints. |

### Logging Configuration (`config.yaml` → `application.logging`)

Settings are defined but the middleware uses hardcoded values:

| Setting | Description | Current Behavior |
|---------|-------------|------------------|
| `level` | Log level (DEBUG, INFO, etc.) | Middleware uses INFO level |
| `log_to_file` | Enable file logging | Hardcoded to `True` in `api/middleware/logging.py:37` |
| `log_to_console` | Enable console logging | Hardcoded to `False` in `api/middleware/logging.py:37` |

**To implement:** Update `api/middleware/logging.py` to read settings from `config_service` and pass them to `setup_logger()`.

### Performance Settings (`config.yaml` → `application.performance`)

Settings are defined but not wired to actual query execution:

| Setting | Description | Implementation Notes |
|---------|-------------|---------------------|
| `query_timeout` | Query timeout in seconds | Should be passed to pyodbc connection/cursor |
| `fetch_size` | Rows to fetch at once | Should be used in `glasstrax.py` cursor operations |

**To implement:** Update `api/services/glasstrax.py` to read these settings and apply them to database operations.

## Future Considerations

1. **Wire up logging config** - Low effort, high value. Read config and pass to logger setup.
2. **Wire up performance settings** - Medium effort. Need to test timeout behavior with Pervasive.
3. **Implement caching** - Higher effort. Need to decide on caching strategy and invalidation.
4. **Gate exports behind flag** - Low effort once we decide what "exports" means (CSV download? API endpoints?).
