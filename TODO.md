# GlassTrax Bridge - TODO

## Agent
- [ ] Allow agent to check for updates and install them. Include check for updates in the context menu of the agent tray icon. Allow disabling updates in the config.

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

## API Enhancement: TGI Web Apps Integration

Enhancements needed to support TGI Web Apps remake form autofill and order validation.

### Phase 1: Enhanced Order Line Details (COMPLETED)
- [x] Add glass product fields to order line response:
  - `overall_thickness` - from `sales_order_detail`
  - `pattern` - from `sales_order_detail`
  - `block_size` - computed from `"{size_1} x {size_2}"`
- [x] Add `has_fab` boolean - check if `so_processing` has FAB process_group
- [x] Add `edgework` string - description from `processing_charges` where process_group='EDGE'
- [x] Update `agent_config.yaml` to allow: `so_processing`, `processing_charges`, `inventory_items`

### Phase 2: Field Selection (COMPLETED)
- [x] Add `fields` query parameter to `/orders/{so_no}` endpoint
- [x] Allow sparse responses: `?fields=so_no,customer_name,line_items`
- [x] Support nested fields: `?fields=line_items.item_description,line_items.overall_thickness`
- [x] Maintain API key permissions at endpoint level (not field level)

### Phase 3: Order Validation Endpoint (COMPLETED)
- [x] Add `GET /api/v1/orders/{so_no}/exists` - lightweight validation
- [x] Return: `{ exists, so_no, customer_id, customer_name, customer_po_no, job_name, status }`

### Data Model Reference

**Processing tables needed:**
- `so_processing` (928K rows) - links order lines to processing operations
- `processing_charges` (345 rows) - defines process types (CUT, EDGE, FAB, SHAPE, TEMP)

**Query to get fab/edgework:**
```sql
SELECT p.so_no, p.so_line_no, pc.process_group, pc.description
FROM so_processing p
JOIN processing_charges pc ON p.process_id = pc.processing_id
WHERE p.so_no = ? AND p.so_line_no = ?
  AND pc.process_group IN ('FAB', 'EDGE')
```

See `docs-internal/GLASSTRAX-DATABASE.md` for full schema reference.

## Future Considerations

1. **Wire up logging config** - Low effort, high value. Read config and pass to logger setup.
2. **Wire up performance settings** - Medium effort. Need to test timeout behavior with Pervasive.
3. **Implement caching** - Higher effort. Need to decide on caching strategy and invalidation.
4. **Gate exports behind flag** - Low effort once we decide what "exports" means (CSV download? API endpoints?).
5. **Custom API base URL** - Add optional `api.base_url` config for reverse proxy/custom port setups. Currently uses `window.location.origin` which works for same-origin deployments but not for external sharing or custom paths.
6. **API key expiration** - Add optional expiration date to API keys. UI for setting expiration on create/edit, background job or middleware check to reject expired keys, and notification/warning when keys are nearing expiration.
