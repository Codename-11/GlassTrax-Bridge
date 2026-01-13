# Development Patterns

Technical patterns and conventions for GlassTrax-Bridge development.

## Agent Mode Patterns

### CRITICAL: Keep Agent Schemas in Sync

The agent has its own copy of schemas (`agent/schemas.py`) that **must match** the API's copy (`api/services/agent_schemas.py`). If you add a field to one, add it to both!

**Files that must stay synchronized:**
- `agent/schemas.py` - Agent's schemas (what it accepts)
- `api/services/agent_schemas.py` - API's schemas (what it sends)

**Example bug**: Adding `additional_conditions` to `JoinClause` in glasstrax.py but not updating the agent's schema causes:
1. The field is silently dropped when serialized
2. JOINs become cartesian products (missing conditions)
3. Database hangs trying to process millions of rows
4. Agent appears unresponsive

**Rule**: When modifying any schema field used for agent communication, update BOTH files and test with an actual agent.

### JOIN Queries Require Explicit Columns

When querying via agent mode with JOINs, you **must** explicitly list columns. Using `columns=None` only selects from the main table alias.

```python
# WRONG - columns=None with JOIN misses joined table columns
result = await self.agent_client.query_table(
    table="sales_orders_headers",
    alias="h",
    columns=None,  # Only gets h.* - misses c.customer_name!
    joins=[JoinClause(table="customer", alias="c", ...)],
)

# RIGHT - explicitly list all needed columns including from joined table
header_columns = [
    "h.so_no", "h.customer_id", "h.order_date", "h.ship_date",
    "c.customer_name",  # From joined customer table
]
result = await self.agent_client.query_table(
    table="sales_orders_headers",
    alias="h",
    columns=header_columns,
    joins=[JoinClause(table="customer", alias="c", ...)],
)
```

**Reference**: `docs-internal/GLASSTRAX-DATABASE.md` for actual Pervasive column names.

### Agent Type Conversion

The agent's `_convert_value()` converts numeric strings to int/float for proper JSON types. This means fields like `customer_id` may arrive as integers even though they're stored as strings.

### pyodbc Thread Safety

**CRITICAL**: pyodbc has `threadsafety=1` meaning threads may share the module but NOT connections.

The agent uses threaded query execution for timeout protection. Each query thread must create its own connection:

```python
# WRONG - sharing connection across threads causes deadlocks
def _execute_sql(self, sql, params):
    conn = self._get_connection()  # Shared connection - BAD!
    cursor = conn.cursor()
    cursor.execute(sql, params)

# RIGHT - dedicated connection per thread
def _execute_sql(self, sql, params):
    conn = pyodbc.connect(conn_str, timeout=self.config.timeout)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        # ... fetch results
    finally:
        conn.close()
```

**Symptoms of thread-safety violation:**
- Queries timeout even though health check works
- Simple queries hang indefinitely
- Agent becomes unresponsive under load

### Query Timeout Configuration

The agent has a configurable query timeout (separate from connection timeout):

```yaml
# agent_config.yaml
database:
  timeout: 30          # Connection timeout (seconds)
  query_timeout: 60    # Max query execution time (seconds)
```

When a query exceeds `query_timeout`, it returns an error:
```json
{"success": false, "error": "Query timeout: exceeded 60s limit. This may indicate a missing JOIN condition or inefficient query."}
```

### Batched Queries (N+1 Avoidance)

When fetching related data for multiple records, use batched queries with `IN` clauses instead of N separate queries.

```python
# WRONG - N+1 pattern: one query per SO (causes timeouts)
for order in orders:
    processing = await self._get_processing_info_via_agent(order["so_no"])
    order["fab_details"] = processing.get("fab_details", [])

# RIGHT - batched: one query for ALL SOs
so_nos = [order["so_no"] for order in orders]
all_processing = await self._get_batch_processing_info_via_agent(so_nos)
for order in orders:
    proc = all_processing.get(order["so_no"], {}).get(order["line_no"], {})
    order["fab_details"] = proc.get("fab_details", [])
```

**Performance impact:**
- Before (N+1): `27s + (49s × N orders)` = timeout for 5+ orders
- After (batched): `27s + 49s` = ~20s regardless of order count

**Implementation:** Use `IN` clause with list of IDs:
```python
FilterCondition(column="p.so_no", operator="IN", value=so_nos)
```

### N+1 Pagination Pattern

For paginated endpoints where COUNT queries are expensive or unavailable, use the N+1 pattern to detect if more pages exist:

```python
# Fetch one extra record to detect more pages
result = await self.agent_client.query_table(
    ...
    limit=page_size + 1,  # Request one extra
    offset=offset,
)

# Check if we got the extra record
has_more = len(result.rows) > page_size
# Return only page_size records (discard probe record)
rows_to_process = result.rows[:page_size]

# Calculate total for pagination response
total = offset + len(rows_to_process) + (1 if has_more else 0)
```

**Why this works:**
- If we get `page_size + 1` records, we know there's at least one more → `has_next = True`
- If we get less, this is the last page → `has_next = False`
- No separate COUNT query needed
- Only one extra row fetched (minimal overhead)

## Architecture Philosophy

### Agent Stability

The agent is a **generic SQL query executor** - it should rarely need changes once stable.

**Agent changes only when:**
- New tables needed → Add to `allowed_tables` in agent_config.yaml
- New query capabilities → Schema changes (e.g., `additional_conditions` for JOINs)
- Bug fixes (e.g., thread safety)

**Bridge API is where business logic lives:**
- New endpoints and data transformations
- Pagination, filtering, response shaping
- Business rules and validation

**The agent is intentionally "dumb"** - it executes queries and returns raw data. All intelligence (batching, caching, transformation) belongs in the Bridge API.

## Pydantic Schema Patterns

### CoercedStr for Agent Compatibility

Use `CoercedStr` and `CoercedStrOrNone` types for fields that may receive int values from the agent:

```python
from typing import Annotated
from pydantic import BaseModel, BeforeValidator

def _coerce_str(v):
    """Coerce int/float to string for database fields."""
    if v is None:
        return None
    return str(v).strip() if not isinstance(v, str) else v.strip()

CoercedStr = Annotated[str, BeforeValidator(_coerce_str)]
CoercedStrOrNone = Annotated[str | None, BeforeValidator(_coerce_str)]

class OrderResponse(BaseModel):
    customer_id: CoercedStr  # Accepts int 1610, converts to "1610"
    customer_po_no: CoercedStrOrNone = None
    pay_type: CoercedStrOrNone = None
```

**When to use**: Any string field that might be numeric in the database (IDs, codes, PO numbers).

## Testing Patterns

### pyodbc Mocking

pyodbc is Windows-only and not available in CI. Tests mock it via `tests/mocks/mock_pyodbc.py`:

```python
@pytest.fixture
def mock_pyodbc():
    """Mock pyodbc module for testing."""
    mock = MagicMock()
    mock.connect.return_value = MockConnection()
    return mock

# In tests
with patch("agent.query.pyodbc", mock_pyodbc):
    service = QueryService()
```

### FastAPI Dependency Override

Override GlassTraxService in integration tests:

```python
@pytest.fixture
def mock_glasstrax_service():
    service = MagicMock(spec=GlassTraxService)
    service.get_customers.return_value = [...]
    return service

@pytest.fixture
def client(mock_glasstrax_service):
    app.dependency_overrides[get_glasstrax_service] = lambda: mock_glasstrax_service
    yield TestClient(app)
    app.dependency_overrides.clear()
```

### Portal MSW Mocking

Portal tests use MSW (Mock Service Worker) for API mocking:

```typescript
// src/__tests__/mocks/handlers.ts
export const handlers = [
  http.get('/api/v1/customers', () => {
    return HttpResponse.json({ items: [...], total: 10 })
  }),
]
```

### In-Memory SQLite

Each test gets an isolated in-memory database:

```python
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
```

## CI/CD Patterns

### Release Workflow

Tests run in parallel before builds:

```
validate → test-api    ─┐
         → test-agent  ─┼→ build-agent  ─┐
         → test-portal ─┘   build-docker ┴→ release
```

All three test jobs must pass before builds start.

### Pre-Commit Checks

Always run before committing:

```powershell
npm run test                    # All tests
ruff check api/ agent/ --fix    # Python linting
cd portal && npm run format     # Prettier
```

## Configuration Patterns

### Hot-Reload Config

Config changes via the Settings page are hot-reloaded without restart (except DSN):

```python
# config_service.py handles reloading
config_service.reload()

# Use properties for dynamic access in singletons
@property
def _api_key(self) -> str:
    return get_config().get("API_KEY", "")
```

### Config Validation

Pydantic validates config.yaml before saving:

```python
# api/config_schema.py
class DatabaseConfig(BaseModel):
    dsn: str
    readonly: bool = True  # Enforced
    timeout: int = Field(default=30, ge=1, le=120)
```

## Date Handling

### GlassTrax Date Format

Dates in Pervasive are stored as `CHAR(8)` in `YYYYMMDD` format:

```python
def parse_glasstrax_date(date_val: str | int | None) -> date | None:
    """Convert GlassTrax YYYYMMDD to date object."""
    if not date_val:
        return None
    date_str = str(date_val)  # Agent may return as int
    if len(date_str) != 8 or date_str == "18991230":  # Null date
        return None
    try:
        return date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    except (ValueError, TypeError):
        return None
```

## API Key Patterns

### Key Prefixes

- `gtb_` - Main API keys (stored in SQLite)
- `gta_` - Agent API keys (stored in agent_config.yaml)

### Key Generation

```python
def generate_key(prefix: str = "gtb_", length: int = 32) -> str:
    """Generate a secure API key with prefix."""
    random_part = secrets.token_urlsafe(length)
    return f"{prefix}{random_part}"
```

## Error Handling

### Agent Error Messages

Include actionable info in agent validation errors:

```python
def _validate_table(self, table: str) -> None:
    if table.lower() not in [t.lower() for t in self.config.allowed_tables]:
        raise ValueError(
            f"Table '{table}' is not in agent's allowed_tables. "
            f"Add '{table}' to agent_config.yaml and restart the agent. "
            f"Current allowed tables: {self.config.allowed_tables}"
        )
```

### Defensive Type Conversion

Handle mixed types from agent:

```python
total_qty = 0
for item in line_items:
    if item.get("order_qty"):
        try:
            total_qty += float(item["order_qty"])
        except (TypeError, ValueError):
            pass  # Skip invalid values
```
