# Extending GlassTrax Bridge

Developer guide for adding new API endpoints, GlassTrax queries, and database models.

## Table of Contents

1. [Adding GlassTrax Endpoints](#adding-glasstrax-endpoints)
2. [Adding App Database Models](#adding-app-database-models)
3. [Database Migrations](#database-migrations)
4. [Agent Mode Considerations](#agent-mode-considerations)
5. [Permission System](#permission-system)
6. [Testing New Endpoints](#testing-new-endpoints)

---

## Adding GlassTrax Endpoints

To expose new GlassTrax data via the API, you need to modify **4-5 files**.

### Example: Adding an Inventory Endpoint

#### Step 1: Create Schema (`api/schemas/inventory.py`)

Define Pydantic models for request/response validation:

```python
"""
Inventory Schemas

Pydantic models for inventory data validation and serialization.
Based on GlassTrax 'inventry' table.
"""

from typing import Optional
from pydantic import BaseModel, Field


class InventoryListResponse(BaseModel):
    """Simplified inventory item for list views"""

    item_id: str = Field(..., max_length=15, description="Item ID")
    description: str
    unit_of_measure: Optional[str] = None
    qty_on_hand: Optional[float] = None
    qty_committed: Optional[float] = None
    qty_available: Optional[float] = None
    unit_price: Optional[float] = None

    class Config:
        from_attributes = True


class InventoryResponse(InventoryListResponse):
    """Full inventory item with all details"""

    category: Optional[str] = None
    vendor_id: Optional[str] = None
    reorder_point: Optional[float] = None
    last_cost: Optional[float] = None
    average_cost: Optional[float] = None

    class Config:
        from_attributes = True
```

#### Step 2: Add Service Method (`api/services/glasstrax.py`)

Add methods to `GlassTraxService` class:

```python
# In GlassTraxService class

# ========================================
# Inventory Methods
# ========================================

async def get_inventory(
    self,
    search: str | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """
    Get inventory items with optional filtering.

    Returns:
        Tuple of (items list, total count)
    """
    if self.is_agent_mode:
        return await self._get_inventory_via_agent(
            search=search, category=category, page=page, page_size=page_size
        )
    else:
        return self._get_inventory_direct(
            search=search, category=category, page=page, page_size=page_size
        )

def _get_inventory_direct(
    self,
    search: str | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Direct ODBC query for inventory"""
    cursor = self._get_cursor()

    # Build WHERE clause
    conditions = []
    params = []

    if search:
        conditions.append("(item_id LIKE ? OR description LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    if category:
        conditions.append("category = ?")
        params.append(category)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Count query
    count_sql = f"SELECT COUNT(*) FROM inventry WHERE {where_clause}"
    cursor.execute(count_sql, params)
    total = cursor.fetchone()[0]

    # Data query with pagination
    offset = (page - 1) * page_size
    sql = f"""
        SELECT TOP {page_size} SKIP {offset}
            item_id, description, unit_of_measure,
            qty_on_hand, qty_committed, unit_price
        FROM inventry
        WHERE {where_clause}
        ORDER BY item_id
    """
    cursor.execute(sql, params)

    columns = [col[0].lower() for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return rows, total

async def _get_inventory_via_agent(
    self,
    search: str | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Query inventory via agent"""
    from api.services.agent_client import FilterCondition, QueryRequest

    filters = []
    if search:
        filters.append(FilterCondition(
            column="item_id", operator="LIKE", value=f"%{search}%"
        ))
    if category:
        filters.append(FilterCondition(
            column="category", operator="=", value=category
        ))

    request = QueryRequest(
        table="inventry",
        columns=["item_id", "description", "unit_of_measure",
                 "qty_on_hand", "qty_committed", "unit_price"],
        filters=filters,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    response = await self.agent_client.query(request)

    if not response.success:
        raise RuntimeError(f"Agent query failed: {response.error}")

    # Convert rows to dicts
    items = [dict(zip(response.columns, row)) for row in response.rows]

    # Get count (separate query or use row_count)
    return items, response.row_count
```

#### Step 3: Create Router (`api/routers/inventory.py`)

```python
"""
Inventory API Endpoints

Provides REST endpoints for inventory data access:
- GET /inventory - List inventory items with pagination
- GET /inventory/{item_id} - Get single item details
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.schemas.inventory import InventoryListResponse, InventoryResponse
from api.schemas.responses import PaginatedResponse, PaginationMeta, APIResponse
from api.middleware import get_api_key, APIKeyInfo
from api.middleware.auth import require_permission
from api.middleware.rate_limit import limiter
from api.dependencies import get_glasstrax_service
from api.services.glasstrax import GlassTraxService

router = APIRouter()

# Create permission dependency
require_inventory_read = require_permission("inventory:read")


def get_api_key_identifier(request: Request) -> str:
    """Get rate limit key from API key header"""
    api_key = request.headers.get("X-API-Key", "anonymous")
    return f"key:{api_key[:12]}" if api_key else "anonymous"


@router.get(
    "",
    response_model=PaginatedResponse[InventoryListResponse],
    summary="List inventory items",
    description="Retrieve a paginated list of inventory items",
)
@limiter.limit("60/minute", key_func=get_api_key_identifier)
async def list_inventory(
    request: Request,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_inventory_read),
    service: GlassTraxService = Depends(get_glasstrax_service),
    search: Optional[str] = Query(None, description="Search by item ID or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[InventoryListResponse]:
    """List inventory items with pagination and filtering"""
    try:
        items_data, total = await service.get_inventory(
            search=search,
            category=category,
            page=page,
            page_size=page_size,
        )

        items = [
            InventoryListResponse(
                item_id=i.get("item_id", "").strip(),
                description=i.get("description", "").strip() if i.get("description") else "",
                unit_of_measure=i.get("unit_of_measure"),
                qty_on_hand=i.get("qty_on_hand"),
                qty_committed=i.get("qty_committed"),
                qty_available=(i.get("qty_on_hand") or 0) - (i.get("qty_committed") or 0),
                unit_price=i.get("unit_price"),
            )
            for i in items_data
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse(
            success=True,
            data=items,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
```

#### Step 4: Register Router

**`api/routers/__init__.py`:**

```python
from .customers import router as customers_router
from .orders import router as orders_router
from .keys import router as keys_router
from .inventory import router as inventory_router  # Add this

__all__ = ["customers_router", "orders_router", "keys_router", "inventory_router"]
```

**`api/main.py`:**

```python
from api.routers import customers_router, orders_router, keys_router, inventory_router

# ... existing router includes ...

app.include_router(
    inventory_router,
    prefix=f"{settings.api_prefix}/inventory",
    tags=["Inventory"],
)
```

#### Step 5: Register Permission

**`api/middleware/auth.py`:**

```python
# Add at the end with other convenience dependencies
require_inventory_read = require_permission("inventory:read")
require_inventory_write = require_permission("inventory:write")
```

**`api/middleware/__init__.py`:**

```python
from .auth import (
    # ... existing imports ...
    require_inventory_read,
    require_inventory_write,
)

__all__ = [
    # ... existing exports ...
    "require_inventory_read",
    "require_inventory_write",
]
```

#### Step 6: Update Documentation

**`docs-internal/API.md`:** Add endpoint documentation

**`api/schemas/responses.py`:** Ensure permission is documented

---

## Adding App Database Models

The app database (SQLite) stores API keys, tenants, and logs. To add new tables:

### Example: Adding a Webhook Model

#### Step 1: Create Model (`api/models/webhook.py`)

```python
"""
Webhook Model

Stores webhook configurations for event notifications.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from api.database import Base


class Webhook(Base):
    """Webhook configuration for a tenant"""

    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(100), nullable=True)  # For signature verification
    events = Column(Text, nullable=False)  # JSON array of event types
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered_at = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)

    # Relationships
    tenant = relationship("Tenant", back_populates="webhooks")

    def __repr__(self):
        return f"<Webhook(id={self.id}, name='{self.name}')>"
```

#### Step 2: Update Tenant Model (if relationship needed)

```python
# In api/models/tenant.py, add:
webhooks = relationship("Webhook", back_populates="tenant", cascade="all, delete-orphan")
```

#### Step 3: Register Model

**`api/models/__init__.py`:**

```python
from api.models.webhook import Webhook

__all__ = [
    "Tenant",
    "APIKey",
    "AccessLog",
    "Webhook",  # Add this
    "generate_api_key",
]
```

**`api/database.py`:** The model is auto-discovered via `init_db()` when imported.

---

## Database Migrations

GlassTrax Bridge uses Alembic for database schema migrations. This ensures safe, versioned schema changes in production.

### Quick Reference

```powershell
# Check current database version
python32\python.exe -m alembic current

# View migration history
python32\python.exe -m alembic history

# Apply all pending migrations
python32\python.exe -m alembic upgrade head

# Rollback one migration
python32\python.exe -m alembic downgrade -1

# Create new migration (auto-detect model changes)
python32\python.exe -m alembic revision --autogenerate -m "Add webhooks table"

# Create empty migration (manual)
python32\python.exe -m alembic revision -m "Custom changes"
```

### For Existing Databases

If you have a database created before Alembic was set up, stamp it with the current revision:

```powershell
python32\python.exe -m alembic stamp head
```

This tells Alembic the database is already at the latest schema.

### Startup Migration Check

The API checks for pending migrations on startup. If migrations are needed, you'll see:

```
======================================================================
  PENDING DATABASE MIGRATIONS
======================================================================

  Current version: 0001
  Latest version:  0002

  Run migrations with:

    python32\python.exe -m alembic upgrade head
======================================================================
```

### Creating Migrations

When you add or modify models:

1. **Make model changes** in `api/models/`
2. **Import new models** in `api/models/__init__.py` AND `migrations/env.py`
3. **Generate migration**:
   ```powershell
   python32\python.exe -m alembic revision --autogenerate -m "Add webhooks table"
   ```
4. **Review the migration** in `migrations/versions/`
5. **Apply migration**:
   ```powershell
   python32\python.exe -m alembic upgrade head
   ```

### Migration Best Practices

1. **Backup first** - Always backup `data/glasstrax_bridge.db` before migrations
2. **Test locally** - Run migrations on a copy of production data
3. **Review autogenerate** - Auto-generated migrations may need manual tweaks
4. **Version control** - Commit migration files to git
5. **Rollback plan** - Test `alembic downgrade -1` before deploying

### SQLite Limitations

SQLite has limited `ALTER TABLE` support. Alembic uses batch mode to work around this:

- Column additions work normally
- Column removals, renames, and type changes use table recreation
- This is handled automatically by `render_as_batch=True` in `migrations/env.py`

### File Structure

```
migrations/
├── env.py              # Alembic environment (imports models)
├── script.py.mako      # Migration template
├── README.md           # Migration docs
└── versions/           # Migration files
    ├── 20260104_0001_initial_schema.py
    └── ...
```

### Production Deployment

Include migrations in your deployment process:

```powershell
# 1. Backup database
copy data\glasstrax_bridge.db data\glasstrax_bridge.db.bak

# 2. Run migrations
python32\python.exe -m alembic upgrade head

# 3. Start application
.\run_prod.bat
```

### Legacy: Simple Migration Alternative

For environments where Alembic isn't available, manual migrations can be used:

```python
# api/migrations.py

from sqlalchemy import text
from api.database import engine

MIGRATIONS = [
    # (version, description, sql)
    (1, "Initial schema", None),  # Handled by create_all
    (2, "Add webhooks table", """
        CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            url VARCHAR(500) NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        )
    """),
    (3, "Add failure_count to webhooks", """
        ALTER TABLE webhooks ADD COLUMN failure_count INTEGER DEFAULT 0
    """),
]


def get_current_version() -> int:
    """Get current schema version"""
    with engine.connect() as conn:
        try:
            result = conn.execute(text(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            ))
            row = result.fetchone()
            return row[0] if row else 0
        except Exception:
            return 0


def run_migrations():
    """Run pending migrations"""
    current = get_current_version()
    print(f"Current schema version: {current}")

    with engine.connect() as conn:
        # Ensure version table exists
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()

        for version, description, sql in MIGRATIONS:
            if version > current and sql:
                print(f"Applying migration {version}: {description}")
                conn.execute(text(sql))
                conn.execute(text(
                    "INSERT INTO schema_version (version) VALUES (:v)"
                ), {"v": version})
                conn.commit()

    print(f"Schema version: {get_current_version()}")
```

---

## Agent Mode Considerations

When adding new GlassTrax tables/queries, update the agent configuration:

### 1. Add Table to Allowed List

**`agent_config.yaml`:**

```yaml
agent:
  port: 8001
  api_key_hash: "..."
  allowed_tables:
    - customer
    - customer_contacts
    - delivery_routes
    - sales_orders_headers
    - sales_order_detail
    - inventry          # Add new table
    - inventory_trans   # Add related tables
```

### 2. Implement Agent Mode in Service

Ensure your service method supports both modes:

```python
async def get_inventory(self, ...):
    if self.is_agent_mode:
        return await self._get_inventory_via_agent(...)
    else:
        return self._get_inventory_direct(...)
```

### 3. Test Both Modes

```powershell
# Test direct mode (Windows with ODBC)
.\run_dev.bat
# Visit http://localhost:5173/api/docs

# Test agent mode
# Terminal 1: Start agent
.\agent\run_agent.bat

# Terminal 2: Start API with agent enabled
# Set agent.enabled: true in config.yaml
.\run_dev.bat
```

---

## Permission System

Permissions follow `resource:action` format.

### Available Patterns

| Pattern | Description |
|---------|-------------|
| `customers:read` | Read customer data |
| `customers:write` | Modify customer data |
| `inventory:read` | Read inventory data |
| `admin:*` | All admin operations |
| `*:*` | Superuser (all permissions) |

### Adding New Permissions

1. **Define the permission** in your router:
   ```python
   require_inventory_read = require_permission("inventory:read")
   ```

2. **Use in endpoint**:
   ```python
   @router.get("/")
   async def list_items(
       _: None = Depends(require_inventory_read),
   ):
   ```

3. **Document in API.md**:
   ```markdown
   | `inventory:read` | Read inventory data |
   ```

4. **Create API keys with permission**:
   ```json
   {
     "permissions": ["inventory:read", "customers:read"]
   }
   ```

---

## Testing New Endpoints

### Manual Testing

```powershell
# Start development server
.\run_dev.bat

# Test with curl (use your API key)
curl -H "X-API-Key: gtb_your_key" http://localhost:5173/api/v1/inventory
curl -H "X-API-Key: gtb_your_key" "http://localhost:5173/api/v1/inventory?search=glass&page_size=5"
```

### Swagger UI

Visit `http://localhost:5173/api/docs` and use the "Authorize" button with your API key.

### Adding Unit Tests

Create `api/tests/test_inventory.py`:

```python
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_list_inventory_unauthorized():
    """Test that inventory endpoint requires auth"""
    response = client.get("/api/v1/inventory")
    assert response.status_code == 401

def test_list_inventory_with_key(test_api_key):
    """Test inventory list with valid key"""
    response = client.get(
        "/api/v1/inventory",
        headers={"X-API-Key": test_api_key}
    )
    assert response.status_code == 200
    assert "data" in response.json()
```

---

## Checklist: Adding a New Endpoint

- [ ] Create schema file (`api/schemas/{resource}.py`)
- [ ] Add service methods (`api/services/glasstrax.py`)
- [ ] Implement both direct and agent mode queries
- [ ] Create router file (`api/routers/{resource}.py`)
- [ ] Register router in `api/routers/__init__.py`
- [ ] Include router in `api/main.py`
- [ ] Add permission dependency (`api/middleware/auth.py`)
- [ ] Export permission in `api/middleware/__init__.py`
- [ ] Add table to agent's `allowed_tables` (`agent_config.yaml`)
- [ ] Document endpoint in `docs-internal/API.md`
- [ ] Add tests (optional but recommended)
- [ ] Test in both direct and agent mode

---

## GlassTrax Table Reference

Common tables in GlassTrax (Pervasive SQL):

| Table | Description | Key Fields |
|-------|-------------|------------|
| `customer` | Customer master | customer_id (PK) |
| `customer_contacts` | Contact info | customer_id, contact_no |
| `delivery_routes` | Route definitions | route_id (PK) |
| `sales_orders_headers` | Order headers | order_number (PK) |
| `sales_order_detail` | Order line items | order_number, line_no |
| `inventry` | Inventory items | item_id (PK) |
| `inventory_trans` | Stock transactions | transaction_id |
| `vendor` | Vendor master | vendor_id (PK) |
| `purchase_orders` | PO headers | po_number (PK) |

**Date format:** `YYYYMMDD` stored as `CHAR(8)`
**Null date:** `18991230` represents null/empty date

Use `parse_glasstrax_date()` from `api/services/glasstrax.py` for date conversion.
