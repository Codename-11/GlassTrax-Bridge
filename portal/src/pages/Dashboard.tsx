import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  tenantsApi,
  apiKeysApi,
  accessLogsApi,
  healthApi,
  formatLocalTime,
  formatLocalDate,
} from '@/lib/api'
import { ConnectionStatus } from '@/components/ui/status-indicator'

export function DashboardPage() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => healthApi.get(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then((r) => r.data),
  })

  const { data: apiKeys } = useQuery({
    queryKey: ['apiKeys'],
    queryFn: () => apiKeysApi.list().then((r) => r.data),
  })

  // Fetch recent logs for display (shows all traffic including admin)
  const { data: recentLogsResponse } = useQuery({
    queryKey: ['recentLogs'],
    queryFn: () => accessLogsApi.list({ limit: 10 }),
  })

  // Fetch stats with admin/health requests excluded for accurate client usage count
  const { data: clientStatsResponse } = useQuery({
    queryKey: ['clientStats'],
    queryFn: () => accessLogsApi.list({ limit: 1, exclude_admin: true }),
  })

  const recentLogs = recentLogsResponse?.data
  const totalClientRequests = clientStatsResponse?.pagination?.total_items ?? 0

  const stats = [
    { name: 'Applications', value: tenants?.length ?? 0 },
    { name: 'Active API Keys', value: apiKeys?.filter((k) => k.is_active).length ?? 0 },
    { name: 'Total API Keys', value: apiKeys?.length ?? 0 },
    { name: 'Client Requests', value: totalClientRequests },
  ]

  const getTenantName = (tenantId: number | null) => {
    if (!tenantId || !tenants) return null
    const tenant = tenants.find((t) => t.id === tenantId)
    return tenant?.name || null
  }

  return (
    <div className="space-y-6">
      {/* Header with Logo, Title, Version Badge */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <img src="/logo.svg" alt="GlassTrax Bridge" className="h-16 w-auto" />
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">Dashboard</h1>
              {health?.version && (
                <Badge variant="secondary" className="text-xs">
                  v{health.version}
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground">Overview of your GlassTrax Bridge API platform</p>
          </div>
        </div>

        {/* Database Connection Status */}
        {!healthLoading && health && (
          <Card className="border-none bg-transparent shadow-none">
            <CardContent className="p-0">
              <ConnectionStatus
                name={health.database_name}
                connected={health.glasstrax_connected}
                size="lg"
              />
            </CardContent>
          </Card>
        )}
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <Link to="/keys">
          <Button variant="default" className="gap-2">
            <KeyIcon className="h-4 w-4" />
            Create API Key
          </Button>
        </Link>
        <Link to="/tenants">
          <Button variant="outline" className="gap-2">
            <BuildingIcon className="h-4 w-4" />
            New Application
          </Button>
        </Link>
        <Link to="/logs">
          <Button variant="outline" className="gap-2">
            <ListIcon className="h-4 w-4" />
            View All Logs
          </Button>
        </Link>
        <a
          href="https://codename-11.github.io/GlassTrax-Bridge/"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button variant="outline" className="gap-2">
            <BookOpenIcon className="h-4 w-4" />
            Documentation
          </Button>
        </a>
        <a href="/api/docs" target="_blank" rel="noopener noreferrer">
          <Button variant="outline" className="gap-2">
            <CodeIcon className="h-4 w-4" />
            API Reference
          </Button>
        </a>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.name}>
            <CardHeader className="pb-2">
              <CardDescription>{stat.name}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Connection Status Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Database Connection</CardTitle>
              {health && (
                <ConnectionStatus
                  name={health.glasstrax_connected ? 'Online' : 'Offline'}
                  connected={health.glasstrax_connected}
                  showLabel={false}
                  size="sm"
                />
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Database</span>
                <span className="font-medium">{health?.database_name || 'Loading...'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Status</span>
                <span className={health?.glasstrax_connected ? 'text-green-600' : 'text-red-600'}>
                  {health?.glasstrax_connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">App Database</CardTitle>
              {health && (
                <ConnectionStatus
                  name={health.app_db_connected ? 'Online' : 'Offline'}
                  connected={health.app_db_connected}
                  showLabel={false}
                  size="sm"
                />
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Type</span>
                <span className="font-medium">SQLite</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Status</span>
                <span className={health?.app_db_connected ? 'text-green-600' : 'text-red-600'}>
                  {health?.app_db_connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent API Activity</CardTitle>
          <CardDescription>Last 10 API requests</CardDescription>
        </CardHeader>
        <CardContent>
          {recentLogs && recentLogs.length > 0 ? (
            <div className="space-y-2">
              {recentLogs.map((log) => {
                const tenantName = getTenantName(log.tenant_id)
                return (
                  <div
                    key={log.id}
                    className="flex items-center justify-between border-b py-2 last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${
                          log.status_code >= 400
                            ? 'bg-destructive/10 text-destructive'
                            : 'bg-green-500/10 text-green-600'
                        }`}
                      >
                        {log.status_code}
                      </span>
                      <span className="font-mono text-sm">
                        {log.method} {log.path}
                      </span>
                      {tenantName && (
                        <span className="bg-muted rounded px-2 py-0.5 text-xs">{tenantName}</span>
                      )}
                    </div>
                    <div className="text-muted-foreground flex items-center gap-4 text-sm">
                      {log.key_prefix && <span className="font-mono">{log.key_prefix}...</span>}
                      <span>{log.response_time_ms?.toFixed(0)}ms</span>
                      <span className="text-xs">
                        {formatLocalDate(log.created_at)} {formatLocalTime(log.created_at)}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-muted-foreground py-4 text-center">No recent activity</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// Icons
function KeyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
      />
    </svg>
  )
}

function BuildingIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
      />
    </svg>
  )
}

function ListIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
      />
    </svg>
  )
}

function BookOpenIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
      />
    </svg>
  )
}

function CodeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
      />
    </svg>
  )
}
