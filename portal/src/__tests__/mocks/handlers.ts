import { http, HttpResponse } from 'msw'

// Sample mock data
const mockTenants = [
  {
    id: 1,
    name: 'Test Tenant',
    description: 'Test tenant for automated testing',
    contact_email: 'test@example.com',
    is_active: true,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 2,
    name: 'Production App',
    description: 'Main production application',
    contact_email: 'prod@example.com',
    is_active: true,
    created_at: '2024-01-10T08:00:00Z',
    updated_at: '2024-01-10T08:00:00Z',
  },
]

const mockApiKeys = [
  {
    id: 1,
    tenant_id: 1,
    name: 'Development Key',
    description: 'For development testing',
    key_prefix: 'gtb_dev12345',
    permissions: ['customers:read', 'orders:read'],
    rate_limit: 60,
    is_active: true,
    created_at: '2024-01-15T10:00:00Z',
    last_used_at: '2024-01-16T14:30:00Z',
    use_count: 150,
  },
  {
    id: 2,
    tenant_id: 1,
    name: 'Admin Key',
    description: 'Full access key',
    key_prefix: 'gtb_admin123',
    permissions: ['*:*'],
    rate_limit: 1000,
    is_active: true,
    created_at: '2024-01-15T10:00:00Z',
    last_used_at: null,
    use_count: 0,
  },
]

const mockAccessLogs = [
  {
    id: 1,
    request_id: 'req-123',
    api_key_id: 1,
    tenant_id: 1,
    key_prefix: 'gtb_dev12345',
    method: 'GET',
    path: '/api/v1/customers',
    query_string: 'page=1',
    client_ip: '192.168.1.100',
    user_agent: 'axios/1.13.2',
    status_code: 200,
    response_time_ms: 45,
    created_at: '2024-01-16T14:30:00Z',
  },
]

const mockHealth = {
  status: 'healthy',
  version: '1.2.0',
  database_name: 'GlassTrax Test',
  glasstrax_connected: true,
  app_db_connected: true,
  mode: 'direct',
}

const mockConfig = {
  database: {
    friendly_name: 'GlassTrax Test Database',
    dsn: 'TEST',
    readonly: true,
    timeout: 30,
  },
  application: {
    timezone: 'America/New_York',
    logging: {
      level: 'INFO',
      log_to_file: false,
      log_to_console: true,
    },
    performance: {
      query_timeout: 30,
      fetch_size: 1000,
    },
  },
  features: {
    enable_caching: true,
    enable_exports: false,
  },
  agent: {
    enabled: false,
    url: 'http://localhost:8001',
    api_key: '',
    timeout: 30,
  },
  admin: {
    username: 'admin',
  },
}

const mockDiagnostics = {
  overall_status: 'healthy',
  checks: [
    { name: 'App Database', status: 'pass', message: 'Connected' },
    { name: 'GlassTrax Database', status: 'pass', message: 'Connected via DSN: TEST' },
    { name: 'Configuration', status: 'pass', message: 'Valid' },
  ],
  system_info: {
    python_version: '3.11.0',
    platform: 'Windows',
    api_version: '1.2.0',
  },
}

// API Handlers
export const handlers = [
  // Health check
  http.get('/health', () => {
    return HttpResponse.json(mockHealth)
  }),

  // Login
  http.post('/api/v1/admin/login', async ({ request }) => {
    const body = (await request.json()) as { username: string; password: string }

    if (body.username === 'admin' && body.password === 'password') {
      return HttpResponse.json({
        success: true,
        data: {
          token: 'mock-jwt-token-12345',
          token_type: 'bearer',
          expires_in: 3600,
          is_default_password: false,
        },
      })
    }

    return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
  }),

  // Tenants
  http.get('/api/v1/admin/tenants', () => {
    return HttpResponse.json({
      success: true,
      data: mockTenants,
      pagination: {
        page: 1,
        page_size: 20,
        total_items: mockTenants.length,
        total_pages: 1,
        has_next: false,
        has_previous: false,
      },
    })
  }),

  http.get('/api/v1/admin/tenants/:id', ({ params }) => {
    const tenant = mockTenants.find((t) => t.id === Number(params.id))
    if (!tenant) {
      return HttpResponse.json({ detail: 'Tenant not found' }, { status: 404 })
    }
    return HttpResponse.json({
      success: true,
      data: tenant,
    })
  }),

  http.post('/api/v1/admin/tenants', async ({ request }) => {
    const body = (await request.json()) as { name: string; description?: string }
    const newTenant = {
      id: mockTenants.length + 1,
      name: body.name,
      description: body.description || '',
      contact_email: '',
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json({ success: true, data: newTenant }, { status: 201 })
  }),

  // API Keys
  http.get('/api/v1/admin/api-keys', () => {
    return HttpResponse.json({
      success: true,
      data: mockApiKeys,
      pagination: {
        page: 1,
        page_size: 20,
        total_items: mockApiKeys.length,
        total_pages: 1,
        has_next: false,
        has_previous: false,
      },
    })
  }),

  http.post('/api/v1/admin/api-keys', async ({ request }) => {
    const body = (await request.json()) as {
      tenant_id: number
      name: string
      permissions?: string[]
    }
    const newKey = {
      id: mockApiKeys.length + 1,
      tenant_id: body.tenant_id,
      name: body.name,
      key_prefix: 'gtb_new12345',
      permissions: body.permissions || ['customers:read'],
      rate_limit: 60,
      is_active: true,
      created_at: new Date().toISOString(),
      key: 'gtb_newly_created_key_abc123def456', // Only shown on creation
    }
    return HttpResponse.json({ success: true, data: newKey }, { status: 201 })
  }),

  // Access Logs
  http.get('/api/v1/admin/access-logs', () => {
    return HttpResponse.json({
      success: true,
      data: mockAccessLogs,
      pagination: {
        page: 1,
        page_size: 20,
        total_items: mockAccessLogs.length,
        total_pages: 1,
        has_next: false,
        has_previous: false,
      },
    })
  }),

  // Config
  http.get('/api/v1/admin/config', () => {
    return HttpResponse.json({
      success: true,
      data: mockConfig,
    })
  }),

  http.patch('/api/v1/admin/config', async ({ request }) => {
    const updates = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({
      success: true,
      message: 'Configuration updated',
      data: { ...mockConfig, ...updates },
    })
  }),

  // Diagnostics
  http.get('/api/v1/admin/diagnostics', () => {
    return HttpResponse.json({
      success: true,
      data: mockDiagnostics,
    })
  }),

  // DSNs
  http.get('/api/v1/admin/dsns', () => {
    return HttpResponse.json({
      success: true,
      data: {
        dsns: [
          { name: 'TEST', driver: 'Pervasive ODBC', is_pervasive: true },
          { name: 'LIVE', driver: 'Pervasive ODBC', is_pervasive: true },
        ],
        pervasive_dsns: ['TEST', 'LIVE'],
        architecture: '32bit',
      },
    })
  }),

  // Test DSN
  http.post('/api/v1/admin/test-dsn', async ({ request }) => {
    const body = (await request.json()) as { dsn: string }
    return HttpResponse.json({
      success: true,
      message: `Successfully connected to ${body.dsn}`,
      data: { table_count: 42 },
    })
  }),

  // Test Agent
  http.post('/api/v1/admin/test-agent', () => {
    return HttpResponse.json({
      success: true,
      message: 'Agent connection successful',
      data: { version: '1.2.0', status: 'healthy' },
    })
  }),

  // Change Password
  http.post('/api/v1/admin/change-password', () => {
    return HttpResponse.json({
      success: true,
      message: 'Password changed successfully',
    })
  }),
]
