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
