# Testing Guide

This document describes the testing infrastructure for GlassTrax-Bridge.

## Overview

The project uses three testing frameworks:

| Component | Framework | Coverage Tool |
|-----------|-----------|---------------|
| API | pytest + pytest-asyncio | pytest-cov |
| Agent | pytest + pytest-asyncio | pytest-cov |
| Portal | Vitest + React Testing Library | @vitest/coverage-v8 |

## Running Tests

### All Tests

```powershell
# Run all test suites
npm run test

# Run with coverage reports
npm run test:coverage
```

### API Tests

```powershell
# Run API tests
npm run test:api

# With coverage
npm run test:api:cov

# Direct pytest
python32\python.exe -m pytest tests/ -v
```

### Agent Tests

```powershell
# Run agent tests
npm run test:agent

# With coverage
npm run test:agent:cov

# Direct pytest
python32\python.exe -m pytest agent/tests/ -v
```

### Portal Tests

```powershell
cd portal

# Run once
npm run test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage

# Visual UI
npm run test:ui
```

## Test Structure

### API Tests (`tests/`)

```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── fixtures/
│   ├── __init__.py
│   ├── data.py           # Sample test data
│   └── factories.py      # Model factory functions
├── mocks/
│   ├── __init__.py
│   ├── mock_pyodbc.py    # pyodbc mock for cross-platform testing
│   └── mock_agent_client.py  # AgentClient mock
├── unit/
│   ├── test_glasstrax_service.py
│   ├── test_auth_middleware.py
│   ├── test_api_key_model.py
│   └── test_config_service.py
└── integration/
    ├── test_customers_router.py
    ├── test_orders_router.py
    ├── test_admin_tenants_router.py
    └── test_admin_keys_router.py
```

### Agent Tests (`agent/tests/`)

```
agent/tests/
├── __init__.py
├── conftest.py           # Agent fixtures
├── mocks/
│   ├── __init__.py
│   └── mock_pyodbc.py    # pyodbc mock
├── test_query_service.py # SQL building and validation
├── test_auth.py          # X-Agent-Key authentication
└── test_main.py          # Endpoint tests
```

### Portal Tests (`portal/src/`)

```
portal/src/
├── __tests__/
│   ├── mocks/
│   │   ├── handlers.ts   # MSW request handlers
│   │   └── server.ts     # MSW server setup
│   └── test-utils.tsx    # Custom render with providers
├── lib/__tests__/
│   └── api.test.ts       # API utility tests
└── pages/__tests__/
    ├── Dashboard.test.tsx
    ├── ApiKeys.test.tsx
    └── Settings.test.tsx
```

## Key Fixtures

### API Fixtures (`tests/conftest.py`)

```python
# Database fixtures
test_engine    # In-memory SQLite engine
test_db        # Session with tables created

# Client fixtures
client                     # TestClient with DB override
client_with_mock_glasstrax # TestClient with mocked GlassTrax

# Auth fixtures
test_tenant     # Test tenant model
test_api_key    # (APIKey, plaintext) tuple
admin_api_key   # Admin key with *:* permission
auth_headers    # {"X-API-Key": "gtb_..."}
admin_headers   # Admin headers

# Service mocks
mock_glasstrax_service  # Mocked GlassTraxService
mock_agent_client       # Mocked AgentClient
```

### Usage Example

```python
def test_list_customers(
    client_with_mock_glasstrax,
    auth_headers,
    mock_glasstrax_service
):
    # Configure mock return value
    mock_glasstrax_service.get_customers = AsyncMock(
        return_value=([{"customer_id": "CUST01"}], 1)
    )

    # Make request
    response = client_with_mock_glasstrax.get(
        "/api/v1/customers",
        headers=auth_headers
    )

    assert response.status_code == 200
```

## Mocking Strategies

### pyodbc Mocking

pyodbc is Windows-only and requires the Pervasive ODBC driver. Tests mock it at the module level:

```python
# tests/mocks/mock_pyodbc.py
class MockCursor:
    def __init__(self, data, columns):
        self._data = data
        self.description = [(col, ...) for col in columns]

    def execute(self, sql, params=None):
        return self

    def fetchall(self):
        return self._data

class MockConnection:
    def cursor(self):
        return MockCursor(...)

def create_mock_pyodbc(customers=None, orders=None):
    mock = MagicMock()
    mock.Error = Exception
    mock.connect = lambda *args, **kwargs: MockConnection()
    return mock
```

### GlassTraxService Override

Use FastAPI dependency injection to replace the service:

```python
def client_with_mock_glasstrax(test_db, mock_glasstrax_service):
    def override_glasstrax():
        yield mock_glasstrax_service

    app.dependency_overrides[get_glasstrax_service] = override_glasstrax
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
```

### MSW for Portal

Mock Service Worker intercepts all fetch/axios requests:

```typescript
// portal/src/__tests__/mocks/handlers.ts
export const handlers = [
  http.get("/health", () => {
    return HttpResponse.json({
      status: "healthy",
      version: "1.2.0",
    });
  }),

  http.get("/api/v1/admin/tenants", () => {
    return HttpResponse.json({
      success: true,
      data: mockTenants,
      pagination: { ... },
    });
  }),
];
```

## Adding New Tests

### API Unit Test

1. Create file in `tests/unit/test_<module>.py`
2. Import fixtures from conftest
3. Use `@pytest.mark.asyncio` for async tests

```python
import pytest
from unittest.mock import MagicMock

class TestMyFeature:
    def test_sync_function(self):
        result = my_function()
        assert result == expected

    @pytest.mark.asyncio
    async def test_async_function(self):
        result = await my_async_function()
        assert result == expected
```

### API Integration Test

1. Create file in `tests/integration/test_<router>_router.py`
2. Use `client_with_mock_glasstrax` for routes needing GlassTrax
3. Configure mock return values per test

```python
class TestMyEndpoint:
    def test_requires_auth(self, client):
        response = client.get("/api/v1/my-endpoint")
        assert response.status_code == 401

    def test_returns_data(
        self,
        client_with_mock_glasstrax,
        auth_headers,
        mock_glasstrax_service
    ):
        mock_glasstrax_service.my_method = AsyncMock(return_value=data)

        response = client_with_mock_glasstrax.get(
            "/api/v1/my-endpoint",
            headers=auth_headers
        )

        assert response.status_code == 200
```

### Portal Component Test

1. Create file in `portal/src/pages/__tests__/<Page>.test.tsx`
2. Use custom render from test-utils
3. Add MSW handlers if needed

```typescript
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@/__tests__/test-utils";
import MyPage from "../MyPage";

describe("MyPage", () => {
  it("displays data after loading", async () => {
    render(<MyPage />);

    await waitFor(() => {
      expect(screen.getByText(/expected text/i)).toBeInTheDocument();
    });
  });
});
```

## CI Integration

Tests run automatically on push and PR via `.github/workflows/test.yml`:

1. **api-tests**: Python 3.11, pytest with coverage
2. **agent-tests**: Python 3.11, pytest with coverage
3. **portal-tests**: Node 20, Vitest with coverage

All jobs must pass for the PR to be mergeable.

## Coverage Goals

| Component | Target |
|-----------|--------|
| API routers | 80%+ |
| API middleware | 90%+ |
| API models | 90%+ |
| Agent query service | 85%+ |
| Portal API client | 80%+ |
| Portal pages | 70%+ |
