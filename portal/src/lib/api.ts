import axios, { AxiosError } from 'axios'

// In dev mode, Vite proxies /api and /health to localhost:8000
// In production, everything is served from the same origin
// Only use VITE_API_URL if explicitly set (for non-standard setups)
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Parse UTC timestamp from API (stored without 'Z' suffix)
export function parseUTCDate(dateString: string): Date {
  // API returns datetime in UTC but without 'Z' suffix
  // Append 'Z' to ensure JavaScript interprets it as UTC
  if (!dateString.endsWith('Z') && !dateString.includes('+')) {
    return new Date(dateString + 'Z')
  }
  return new Date(dateString)
}

// Format a UTC timestamp for display in local time
export function formatLocalTime(dateString: string): string {
  return parseUTCDate(dateString).toLocaleTimeString()
}

export function formatLocalDateTime(dateString: string): string {
  return parseUTCDate(dateString).toLocaleString()
}

export function formatLocalDate(dateString: string): string {
  return parseUTCDate(dateString).toLocaleDateString()
}

// Extract error message from API error response
export function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    // Try to get the detail from API response
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail)) {
      // Validation errors
      return detail.map((d: { msg?: string }) => d.msg || 'Validation error').join(', ')
    }
    // Fall back to status text or generic message
    if (error.response?.statusText) {
      return `${error.response.status}: ${error.response.statusText}`
    }
    if (error.message) {
      return error.message
    }
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'An unexpected error occurred'
}

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API Types
export interface Tenant {
  id: number
  name: string
  description: string | null
  contact_email: string | null
  is_active: boolean
  created_at: string
}

export interface APIKey {
  id: number
  tenant_id: number
  name: string
  description: string | null
  key_prefix: string
  permissions: string[]
  rate_limit: number
  is_active: boolean
  expires_at: string | null
  created_at: string
  last_used_at: string | null
  use_count: number
}

export interface AccessLog {
  id: number
  request_id: string
  api_key_id: number | null
  tenant_id: number | null
  key_prefix: string | null
  method: string
  path: string
  query_string: string | null
  status_code: number
  response_time_ms: number
  created_at: string
}

export interface CreateAPIKeyRequest {
  tenant_id: number
  name: string
  description?: string
  permissions: string[]
  rate_limit?: number
  expires_in_days?: number
}

export interface CreateAPIKeyResponse {
  id: number
  tenant_id: number
  name: string
  key_prefix: string
  key: string // The plaintext key - only shown once!
  permissions: string[]
  rate_limit: number
  expires_at: string | null
  created_at: string
}

// Paginated response wrapper
interface PaginatedResponse<T> {
  success: boolean
  data: T[]
  pagination: {
    page: number
    page_size: number
    total_items: number
    total_pages: number
    has_next: boolean
    has_previous: boolean
  }
}

interface APIResponse<T> {
  success: boolean
  data: T
  message?: string
}

// API Functions
export const tenantsApi = {
  list: () =>
    api.get<PaginatedResponse<Tenant>>('/api/v1/admin/tenants').then((r) => ({
      ...r,
      data: r.data.data, // Extract data array from paginated response
    })),
  create: (data: { name: string; description?: string; contact_email?: string }) =>
    api.post<APIResponse<Tenant>>('/api/v1/admin/tenants', data).then((r) => ({
      ...r,
      data: r.data.data,
    })),
  update: (
    id: number,
    data: { name?: string; description?: string; contact_email?: string; is_active?: boolean }
  ) =>
    api.patch<APIResponse<Tenant>>(`/api/v1/admin/tenants/${id}`, data).then((r) => ({
      ...r,
      data: r.data.data,
    })),
  delete: (id: number) => api.delete(`/api/v1/admin/tenants/${id}`),
  get: (id: number) =>
    api.get<APIResponse<Tenant>>(`/api/v1/admin/tenants/${id}`).then((r) => ({
      ...r,
      data: r.data.data,
    })),
}

export const apiKeysApi = {
  list: (tenantId?: number) =>
    api
      .get<PaginatedResponse<APIKey>>('/api/v1/admin/api-keys', {
        params: tenantId ? { tenant_id: tenantId } : undefined,
      })
      .then((r) => ({
        ...r,
        data: r.data.data,
      })),
  create: (data: CreateAPIKeyRequest) =>
    api.post<APIResponse<CreateAPIKeyResponse>>('/api/v1/admin/api-keys', data).then((r) => ({
      ...r,
      data: r.data.data,
    })),
  delete: (id: number) => api.delete(`/api/v1/admin/api-keys/${id}`),
  activate: (id: number) =>
    api.post<APIResponse<APIKey>>(`/api/v1/admin/api-keys/${id}/activate`).then((r) => ({
      ...r,
      data: r.data.data,
    })),
  deactivate: (id: number) =>
    api.post<APIResponse<APIKey>>(`/api/v1/admin/api-keys/${id}/deactivate`).then((r) => ({
      ...r,
      data: r.data.data,
    })),
}

export const accessLogsApi = {
  list: (params?: {
    tenant_id?: number
    api_key_id?: number
    limit?: number
    exclude_admin?: boolean
  }) =>
    api.get<PaginatedResponse<AccessLog>>('/api/v1/admin/access-logs', { params }).then((r) => ({
      ...r,
      data: r.data.data,
      pagination: r.data.pagination,
    })),
}

// Health check types
export interface HealthData {
  status: 'healthy' | 'degraded' | 'unhealthy'
  version: string
  database_name: string
  glasstrax_connected: boolean
  app_db_connected: boolean
}

export const healthApi = {
  get: () => api.get<HealthData>('/health').then((r) => r.data),
}

// Diagnostics types
export interface DiagnosticCheck {
  name: string
  status: 'pass' | 'fail' | 'warning'
  message: string
  details?: Record<string, unknown>
}

export interface DiagnosticsData {
  overall_status: 'healthy' | 'degraded' | 'unhealthy'
  checks: DiagnosticCheck[]
  system_info: Record<string, string | boolean>
}

export const diagnosticsApi = {
  get: () =>
    api.get<APIResponse<DiagnosticsData>>('/api/v1/admin/diagnostics').then((r) => ({
      ...r,
      data: r.data.data,
    })),
}

// Configuration types
export interface ConfigData {
  database: {
    friendly_name: string
    dsn: string
    readonly: boolean
    timeout: number
  }
  application: {
    timezone: string
    logging: {
      level: string
      log_to_file: boolean
      log_to_console: boolean
    }
    performance: {
      query_timeout: number
      fetch_size: number
    }
  }
  features: {
    enable_caching: boolean
    enable_exports: boolean
  }
  caching: {
    fabs_ttl_minutes: number
    max_cached_dates: number
  }
  admin: {
    username: string
  }
  agent: {
    enabled: boolean
    url: string
    api_key: string
    timeout: number
  }
}

export interface ConfigUpdateResponse {
  changed_fields: string[]
  restart_required: boolean
  restart_required_fields: string[]
  message: string
}

export const configApi = {
  get: () =>
    api.get<APIResponse<ConfigData>>('/api/v1/admin/config').then((r) => ({
      ...r,
      data: r.data.data,
    })),
  update: (data: Partial<ConfigData>) =>
    api.patch<APIResponse<ConfigUpdateResponse>>('/api/v1/admin/config', data).then((r) => ({
      ...r,
      data: r.data.data,
    })),
}

// DSN types
export interface DSNInfo {
  name: string
  driver: string
  is_pervasive: boolean
}

export interface DSNsData {
  dsns: DSNInfo[]
  pervasive_dsns: string[]
  architecture: string
}

export const dsnsApi = {
  list: () =>
    api.get<APIResponse<DSNsData>>('/api/v1/admin/dsns').then((r) => ({
      ...r,
      data: r.data.data,
    })),
}

// Test DSN types
export interface TestDSNRequest {
  dsn: string
  readonly?: boolean
}

export interface TestDSNResponse {
  success: boolean
  dsn: string
  message: string
  tables_found?: number
  sample_tables?: string[]
}

export const testDsnApi = {
  test: (data: TestDSNRequest) =>
    api.post<APIResponse<TestDSNResponse>>('/api/v1/admin/test-dsn', data).then((r) => ({
      ...r,
      data: r.data.data,
    })),
}

// Test Agent types
export interface TestAgentRequest {
  url: string
  api_key: string
  timeout?: number
}

export interface TestAgentResponse {
  connected: boolean
  url: string
  message: string
  agent_version?: string
  database_connected?: boolean
  authenticated?: boolean
}

export const testAgentApi = {
  test: (data: TestAgentRequest) =>
    api.post<APIResponse<TestAgentResponse>>('/api/v1/admin/test-agent', data).then((r) => ({
      ...r,
      data: r.data.data,
    })),
}

// Password change types
export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export interface ChangePasswordResponse {
  message: string
}

export const adminApi = {
  changePassword: (data: ChangePasswordRequest) =>
    api
      .post<APIResponse<ChangePasswordResponse>>('/api/v1/admin/change-password', data)
      .then((r) => ({
        ...r,
        data: r.data.data,
      })),
}

// Cache types
export interface CacheStatusResponse {
  enabled: boolean
  entries: number
  total_hits: number
  total_misses: number
  oldest_entry: string | null
  newest_entry: string | null
  cached_dates: string[]
  hit_rate: number | null
}

export interface CacheInvalidateResponse {
  success: boolean
  message: string
  cleared_count?: number
}

export const cacheApi = {
  getStatus: () =>
    api.get<APIResponse<CacheStatusResponse>>('/api/v1/admin/cache/status').then((r) => ({
      ...r,
      data: r.data.data,
    })),
  invalidateDate: (date: string) =>
    api
      .delete<APIResponse<CacheInvalidateResponse>>(`/api/v1/admin/cache/fabs/${date}`)
      .then((r) => ({
        ...r,
        data: r.data.data,
      })),
  clearAll: () =>
    api.delete<APIResponse<CacheInvalidateResponse>>('/api/v1/admin/cache/fabs').then((r) => ({
      ...r,
      data: r.data.data,
    })),
}

// Speed test types
export interface SpeedTestResult {
  timestamp: string
  health_check_ms: number
  simple_query_ms: number | null
  total_ms: number
  mode: string
  glasstrax_connected: boolean
  error: string | null
}

export const speedTestApi = {
  run: () =>
    api.post<APIResponse<SpeedTestResult>>('/api/v1/admin/diagnostics/speedtest').then((r) => ({
      ...r,
      data: r.data.data,
    })),
}
