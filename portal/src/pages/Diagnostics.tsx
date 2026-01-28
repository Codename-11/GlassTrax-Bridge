import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  api,
  diagnosticsApi,
  healthApi,
  cacheApi,
  speedTestApi,
  configApi,
  getErrorMessage,
  type DiagnosticCheck,
  type SpeedTestResult,
} from '@/lib/api'
import { StatusIndicator } from '@/components/ui/status-indicator'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface ResetResponse {
  success: boolean
  data: {
    tables_cleared: string[]
    message: string
  }
  message: string
}

interface RestartResponse {
  success: boolean
  data: {
    message: string
    restart_in_seconds: number
  }
  message: string
}

export function DiagnosticsPage() {
  const queryClient = useQueryClient()
  const [confirmText, setConfirmText] = useState('')
  const [showResetResult, setShowResetResult] = useState<string[] | null>(null)
  const [showRestartConfirm, setShowRestartConfirm] = useState(false)
  const [isRestarting, setIsRestarting] = useState(false)
  const [speedTestResult, setSpeedTestResult] = useState<SpeedTestResult | null>(null)

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => healthApi.get(),
    refetchInterval: 30000,
  })

  const { data: config } = useQuery({
    queryKey: ['config'],
    queryFn: () => configApi.get().then((r) => r.data),
    refetchOnWindowFocus: false,
  })

  const { data: cacheStatus, refetch: refetchCache } = useQuery({
    queryKey: ['cacheStatus'],
    queryFn: () => cacheApi.getStatus().then((r) => r.data),
    refetchOnWindowFocus: false,
    enabled: config?.features.enable_caching ?? false,
  })

  const {
    data: diagnostics,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['diagnostics'],
    queryFn: () => diagnosticsApi.get().then((r) => r.data),
    refetchOnWindowFocus: false,
  })

  const resetMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post<ResetResponse>('/api/v1/admin/reset-database', {
        confirmation: confirmText,
      })
      return response.data
    },
    onSuccess: (data) => {
      setShowResetResult(data.data.tables_cleared)
      setConfirmText('')
      toast.success('Database reset complete', {
        description: 'Please restart the API server to generate a new admin key.',
        duration: 10000,
      })
    },
    onError: (error) => {
      toast.error('Failed to reset database', {
        description: getErrorMessage(error),
      })
    },
  })

  const speedTestMutation = useMutation({
    mutationFn: () => speedTestApi.run().then((r) => r.data),
    onSuccess: (data) => {
      setSpeedTestResult(data)
      if (data.error) {
        toast.error('Speed test completed with errors', { description: data.error })
      } else {
        toast.success('Speed test completed', {
          description: `Total: ${data.total_ms}ms`,
        })
      }
    },
    onError: (error) => {
      toast.error('Speed test failed', { description: getErrorMessage(error) })
    },
  })

  const clearCacheMutation = useMutation({
    mutationFn: () => cacheApi.clearAll().then((r) => r.data),
    onSuccess: (data) => {
      toast.success('Cache cleared', { description: data.message })
      refetchCache()
      queryClient.invalidateQueries({ queryKey: ['cacheStatus'] })
    },
    onError: (error) => {
      toast.error('Failed to clear cache', { description: getErrorMessage(error) })
    },
  })

  const handleRestart = async () => {
    setIsRestarting(true)
    setShowRestartConfirm(false)
    try {
      await api.post<RestartResponse>('/api/v1/admin/restart-server')
      toast.success('Server is restarting...', {
        description: 'The page will reconnect automatically.',
        duration: 5000,
      })
      // Wait for server to come back up and reload
      setTimeout(() => {
        const checkServer = setInterval(async () => {
          try {
            await api.get('/health')
            clearInterval(checkServer)
            setIsRestarting(false)
            toast.success('Server restarted successfully!')
            refetch()
          } catch {
            // Server still restarting, keep checking
          }
        }, 1000)
        // Stop checking after 30 seconds
        setTimeout(() => {
          clearInterval(checkServer)
          setIsRestarting(false)
          toast.error('Server restart timed out', {
            description: 'Please check if the server is running.',
          })
        }, 30000)
      }, 2000)
    } catch (error) {
      setIsRestarting(false)
      toast.error('Failed to restart server', {
        description: getErrorMessage(error),
      })
    }
  }

  const getOverallBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return <Badge className="bg-green-600 px-4 py-1 text-lg hover:bg-green-700">Healthy</Badge>
      case 'degraded':
        return (
          <Badge className="bg-yellow-500 px-4 py-1 text-lg hover:bg-yellow-600">Degraded</Badge>
        )
      case 'unhealthy':
        return (
          <Badge variant="destructive" className="px-4 py-1 text-lg">
            Unhealthy
          </Badge>
        )
      default:
        return (
          <Badge variant="secondary" className="px-4 py-1 text-lg">
            {status}
          </Badge>
        )
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">System Diagnostics</h1>
            {health?.version && (
              <Badge variant="secondary" className="text-xs">
                v{health.version}
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground">Check system health and connectivity status</p>
        </div>
        <Button onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? 'Running...' : 'Run Diagnostics'}
        </Button>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="py-8">
            <div className="text-center">
              <div className="border-primary mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-b-2"></div>
              <p className="text-muted-foreground">Running diagnostics...</p>
            </div>
          </CardContent>
        </Card>
      ) : diagnostics ? (
        <>
          {/* Overall Status */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Overall Status</CardTitle>
                  <CardDescription>System health summary</CardDescription>
                </div>
                {getOverallBadge(diagnostics.overall_status)}
              </div>
            </CardHeader>
          </Card>

          {/* Diagnostic Checks */}
          <Card>
            <CardHeader>
              <CardTitle>Diagnostic Checks</CardTitle>
              <CardDescription>{diagnostics.checks.length} checks completed</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {diagnostics.checks.map((check, index) => (
                <DiagnosticCheckCard key={index} check={check} />
              ))}
            </CardContent>
          </Card>

          {/* Speed Test */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <BoltIcon className="h-5 w-5" />
                    Speed Test
                  </CardTitle>
                  <CardDescription>Measure database query latency</CardDescription>
                </div>
                <Button
                  onClick={() => speedTestMutation.mutate()}
                  disabled={speedTestMutation.isPending}
                >
                  {speedTestMutation.isPending ? 'Running...' : 'Run Speed Test'}
                </Button>
              </div>
            </CardHeader>
            {speedTestResult && (
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-lg border p-3">
                    <div className="text-muted-foreground text-xs">Health Check</div>
                    <div className="text-2xl font-bold">{speedTestResult.health_check_ms}ms</div>
                  </div>
                  <div className="rounded-lg border p-3">
                    <div className="text-muted-foreground text-xs">Simple Query</div>
                    <div className="text-2xl font-bold">
                      {speedTestResult.simple_query_ms !== null
                        ? `${speedTestResult.simple_query_ms}ms`
                        : 'N/A'}
                    </div>
                  </div>
                  <div className="rounded-lg border p-3">
                    <div className="text-muted-foreground text-xs">Total</div>
                    <div className="text-2xl font-bold text-green-600">{speedTestResult.total_ms}ms</div>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  <Badge variant="outline">Mode: {speedTestResult.mode}</Badge>
                  <Badge variant={speedTestResult.glasstrax_connected ? 'default' : 'destructive'}>
                    {speedTestResult.glasstrax_connected ? 'Connected' : 'Disconnected'}
                  </Badge>
                  {speedTestResult.error && (
                    <Badge variant="destructive">{speedTestResult.error}</Badge>
                  )}
                </div>
              </CardContent>
            )}
          </Card>

          {/* Cache Status */}
          {config?.features.enable_caching && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <CacheIcon className="h-5 w-5" />
                      Cache Status
                    </CardTitle>
                    <CardDescription>FAB order cache statistics</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => refetchCache()}>
                      Refresh
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => clearCacheMutation.mutate()}
                      disabled={clearCacheMutation.isPending || !cacheStatus?.cache.entries}
                    >
                      {clearCacheMutation.isPending ? 'Clearing...' : 'Clear Cache'}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {cacheStatus ? (
                  <>
                    <div className="grid gap-4 md:grid-cols-4">
                      <div className="rounded-lg border p-3">
                        <div className="text-muted-foreground text-xs">Cached Entries</div>
                        <div className="text-2xl font-bold">{cacheStatus.cache.entries}</div>
                        <div className="text-muted-foreground text-xs">
                          max {cacheStatus.config.max_entries}
                        </div>
                      </div>
                      <div className="rounded-lg border p-3">
                        <div className="text-muted-foreground text-xs">TTL</div>
                        <div className="text-2xl font-bold">{cacheStatus.config.ttl_minutes}</div>
                        <div className="text-muted-foreground text-xs">minutes</div>
                      </div>
                      <div className="rounded-lg border p-3">
                        <div className="text-muted-foreground text-xs">Cache Hits</div>
                        <div className="text-2xl font-bold text-green-600">
                          {cacheStatus.cache.total_hits}
                        </div>
                      </div>
                      <div className="rounded-lg border p-3">
                        <div className="text-muted-foreground text-xs">Cache Misses</div>
                        <div className="text-2xl font-bold text-amber-600">
                          {cacheStatus.cache.total_misses}
                        </div>
                      </div>
                    </div>
                    {cacheStatus.cache.cached_dates.length > 0 && (
                      <div className="mt-4">
                        <div className="text-muted-foreground mb-2 text-xs">Cached Dates</div>
                        <div className="flex flex-wrap gap-2">
                          {cacheStatus.cache.cached_dates.map((date) => (
                            <Badge key={date} variant="secondary">
                              {date}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    {cacheStatus.cache.total_hits + cacheStatus.cache.total_misses > 0 && (
                      <div className="mt-4">
                        <div className="text-muted-foreground text-xs">
                          Hit Rate:{' '}
                          {Math.round(
                            (cacheStatus.cache.total_hits /
                              (cacheStatus.cache.total_hits + cacheStatus.cache.total_misses)) *
                              100
                          )}
                          %
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-muted-foreground text-sm">Loading cache status...</div>
                )}
              </CardContent>
            </Card>
          )}

          {/* System Info */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>System Information</CardTitle>
                  <CardDescription>Runtime environment details</CardDescription>
                </div>
                {showRestartConfirm ? (
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-sm">Restart server?</span>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleRestart}
                      disabled={isRestarting}
                    >
                      Yes, Restart
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowRestartConfirm(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => setShowRestartConfirm(true)}
                    disabled={isRestarting}
                  >
                    {isRestarting ? (
                      <>
                        <span className="mr-2 animate-spin">
                          <RefreshIcon className="h-4 w-4" />
                        </span>
                        Restarting...
                      </>
                    ) : (
                      <>
                        <RefreshIcon className="mr-2 h-4 w-4" />
                        Restart Server
                      </>
                    )}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 md:grid-cols-2">
                {Object.entries(diagnostics.system_info).map(([key, value]) => (
                  <div key={key} className="flex justify-between border-b py-2 last:border-0">
                    <span className="text-muted-foreground capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    {key === 'database_connected' ? (
                      <StatusIndicator
                        status={value ? 'online' : 'offline'}
                        label={value ? 'Connected' : 'Disconnected'}
                        size="sm"
                      />
                    ) : (
                      <span className="font-mono text-sm">{String(value)}</span>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className="border-red-500/50">
            <CardHeader>
              <div className="flex items-center gap-2">
                <DangerIcon className="h-5 w-5 text-red-500" />
                <CardTitle className="text-red-500">Danger Zone</CardTitle>
              </div>
              <CardDescription>Destructive actions that cannot be undone</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {showResetResult && (
                <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
                  <AlertTitle className="text-green-800 dark:text-green-200">
                    Database Reset Complete
                  </AlertTitle>
                  <AlertDescription className="mt-2">
                    <p className="mb-2 text-green-700 dark:text-green-300">
                      The following tables were cleared:
                    </p>
                    <ul className="list-inside list-disc text-sm text-green-600 dark:text-green-400">
                      {showResetResult.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                    <p className="mt-3 font-medium text-green-800 dark:text-green-200">
                      Please restart the API server to generate a new admin key.
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="mt-2"
                      onClick={() => setShowResetResult(null)}
                    >
                      Dismiss
                    </Button>
                  </AlertDescription>
                </Alert>
              )}

              <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4">
                <h4 className="mb-2 font-medium text-red-600 dark:text-red-400">
                  Reset Application Database
                </h4>
                <p className="text-muted-foreground mb-4 text-sm">
                  This will permanently delete all API keys, applications, and access logs. A new
                  admin key will be generated when you restart the server.
                </p>

                <div className="space-y-3">
                  <div>
                    <label className="text-muted-foreground mb-1 block text-sm">
                      Type <code className="bg-muted rounded px-1 font-bold">RESET DATABASE</code>{' '}
                      to confirm:
                    </label>
                    <Input
                      value={confirmText}
                      onChange={(e) => setConfirmText(e.target.value)}
                      placeholder="Type confirmation phrase..."
                      className="max-w-sm font-mono"
                      disabled={resetMutation.isPending}
                    />
                  </div>

                  <Button
                    variant="destructive"
                    onClick={() => resetMutation.mutate()}
                    disabled={confirmText !== 'RESET DATABASE' || resetMutation.isPending}
                  >
                    {resetMutation.isPending ? (
                      <>
                        <span className="mr-2 animate-spin">⏳</span>
                        Resetting...
                      </>
                    ) : (
                      'Reset Database'
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="py-8">
            <div className="text-muted-foreground text-center">
              Click "Run Diagnostics" to check system health
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function DiagnosticCheckCard({ check }: { check: DiagnosticCheck }) {
  const getStatusBg = (status: string) => {
    switch (status) {
      case 'pass':
        return 'border-l-green-500 bg-green-500/5'
      case 'fail':
        return 'border-l-red-500 bg-red-500/5'
      case 'warning':
        return 'border-l-yellow-500 bg-yellow-500/5'
      default:
        return 'border-l-gray-500'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass':
        return <CheckIcon className="h-5 w-5 text-green-600" />
      case 'fail':
        return <XIcon className="h-5 w-5 text-red-600" />
      case 'warning':
        return <AlertIcon className="h-5 w-5 text-yellow-600" />
      default:
        return null
    }
  }

  return (
    <div className={`rounded-r-lg border-l-4 p-4 ${getStatusBg(check.status)}`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{getStatusIcon(check.status)}</div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">{check.name}</h4>
            <Badge
              variant={
                check.status === 'pass'
                  ? 'default'
                  : check.status === 'fail'
                    ? 'destructive'
                    : 'secondary'
              }
              className={
                check.status === 'pass'
                  ? 'bg-green-600'
                  : check.status === 'warning'
                    ? 'bg-yellow-500'
                    : ''
              }
            >
              {check.status.toUpperCase()}
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1 text-sm">{check.message}</p>
          {check.details && Object.keys(check.details).length > 0 && (
            <details className="mt-2">
              <summary className="text-muted-foreground hover:text-foreground cursor-pointer text-xs">
                Show details
              </summary>
              <pre className="bg-muted mt-2 overflow-x-auto rounded p-2 text-xs">
                {JSON.stringify(check.details, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  )
}

// Icons
function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  )
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}

function AlertIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  )
}

function DangerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  )
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      />
    </svg>
  )
}

function BoltIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 10V3L4 14h7v7l9-11h-7z"
      />
    </svg>
  )
}

function CacheIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
      />
    </svg>
  )
}
