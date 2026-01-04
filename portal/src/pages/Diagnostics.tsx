import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { api, diagnosticsApi, getErrorMessage, type DiagnosticCheck } from '@/lib/api';
import { StatusIndicator } from '@/components/ui/status-indicator';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface ResetResponse {
  success: boolean;
  data: {
    tables_cleared: string[];
    message: string;
  };
  message: string;
}

interface RestartResponse {
  success: boolean;
  data: {
    message: string;
    restart_in_seconds: number;
  };
  message: string;
}

export function DiagnosticsPage() {
  const [confirmText, setConfirmText] = useState('');
  const [showResetResult, setShowResetResult] = useState<string[] | null>(null);
  const [showRestartConfirm, setShowRestartConfirm] = useState(false);
  const [isRestarting, setIsRestarting] = useState(false);

  const { data: diagnostics, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['diagnostics'],
    queryFn: () => diagnosticsApi.get().then((r) => r.data),
    refetchOnWindowFocus: false,
  });

  const resetMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post<ResetResponse>('/api/v1/admin/reset-database', {
        confirmation: confirmText,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setShowResetResult(data.data.tables_cleared);
      setConfirmText('');
      toast.success('Database reset complete', {
        description: 'Please restart the API server to generate a new admin key.',
        duration: 10000,
      });
    },
    onError: (error) => {
      toast.error('Failed to reset database', {
        description: getErrorMessage(error),
      });
    },
  });

  const handleRestart = async () => {
    setIsRestarting(true);
    setShowRestartConfirm(false);
    try {
      await api.post<RestartResponse>('/api/v1/admin/restart-server');
      toast.success('Server is restarting...', {
        description: 'The page will reconnect automatically.',
        duration: 5000,
      });
      // Wait for server to come back up and reload
      setTimeout(() => {
        const checkServer = setInterval(async () => {
          try {
            await api.get('/health');
            clearInterval(checkServer);
            setIsRestarting(false);
            toast.success('Server restarted successfully!');
            refetch();
          } catch {
            // Server still restarting, keep checking
          }
        }, 1000);
        // Stop checking after 30 seconds
        setTimeout(() => {
          clearInterval(checkServer);
          setIsRestarting(false);
          toast.error('Server restart timed out', {
            description: 'Please check if the server is running.',
          });
        }, 30000);
      }, 2000);
    } catch (error) {
      setIsRestarting(false);
      toast.error('Failed to restart server', {
        description: getErrorMessage(error),
      });
    }
  };

  const getOverallBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return <Badge className="bg-green-600 hover:bg-green-700 text-lg px-4 py-1">Healthy</Badge>;
      case 'degraded':
        return <Badge className="bg-yellow-500 hover:bg-yellow-600 text-lg px-4 py-1">Degraded</Badge>;
      case 'unhealthy':
        return <Badge variant="destructive" className="text-lg px-4 py-1">Unhealthy</Badge>;
      default:
        return <Badge variant="secondary" className="text-lg px-4 py-1">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">System Diagnostics</h1>
          <p className="text-muted-foreground">
            Check system health and connectivity status
          </p>
        </div>
        <Button onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? 'Running...' : 'Run Diagnostics'}
        </Button>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="py-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
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
              <CardDescription>
                {diagnostics.checks.length} checks completed
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {diagnostics.checks.map((check, index) => (
                <DiagnosticCheckCard key={index} check={check} />
              ))}
            </CardContent>
          </Card>

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
                    <span className="text-sm text-muted-foreground">Restart server?</span>
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
                        <span className="animate-spin mr-2">
                          <RefreshIcon className="h-4 w-4" />
                        </span>
                        Restarting...
                      </>
                    ) : (
                      <>
                        <RefreshIcon className="h-4 w-4 mr-2" />
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
                  <div key={key} className="flex justify-between py-2 border-b last:border-0">
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
              <CardDescription>
                Destructive actions that cannot be undone
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {showResetResult && (
                <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
                  <AlertTitle className="text-green-800 dark:text-green-200">
                    Database Reset Complete
                  </AlertTitle>
                  <AlertDescription className="mt-2">
                    <p className="text-green-700 dark:text-green-300 mb-2">
                      The following tables were cleared:
                    </p>
                    <ul className="list-disc list-inside text-sm text-green-600 dark:text-green-400">
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

              <div className="p-4 rounded-lg border border-red-500/30 bg-red-500/5">
                <h4 className="font-medium text-red-600 dark:text-red-400 mb-2">
                  Reset Application Database
                </h4>
                <p className="text-sm text-muted-foreground mb-4">
                  This will permanently delete all API keys, applications, and access logs.
                  A new admin key will be generated when you restart the server.
                </p>

                <div className="space-y-3">
                  <div>
                    <label className="text-sm text-muted-foreground block mb-1">
                      Type <code className="bg-muted px-1 rounded font-bold">RESET DATABASE</code> to confirm:
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
                        <span className="animate-spin mr-2">⏳</span>
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
            <div className="text-center text-muted-foreground">
              Click "Run Diagnostics" to check system health
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function DiagnosticCheckCard({ check }: { check: DiagnosticCheck }) {
  const getStatusBg = (status: string) => {
    switch (status) {
      case 'pass':
        return 'border-l-green-500 bg-green-500/5';
      case 'fail':
        return 'border-l-red-500 bg-red-500/5';
      case 'warning':
        return 'border-l-yellow-500 bg-yellow-500/5';
      default:
        return 'border-l-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass':
        return <CheckIcon className="h-5 w-5 text-green-600" />;
      case 'fail':
        return <XIcon className="h-5 w-5 text-red-600" />;
      case 'warning':
        return <AlertIcon className="h-5 w-5 text-yellow-600" />;
      default:
        return null;
    }
  };

  return (
    <div className={`border-l-4 rounded-r-lg p-4 ${getStatusBg(check.status)}`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{getStatusIcon(check.status)}</div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">{check.name}</h4>
            <Badge
              variant={check.status === 'pass' ? 'default' : check.status === 'fail' ? 'destructive' : 'secondary'}
              className={check.status === 'pass' ? 'bg-green-600' : check.status === 'warning' ? 'bg-yellow-500' : ''}
            >
              {check.status.toUpperCase()}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">{check.message}</p>
          {check.details && Object.keys(check.details).length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                Show details
              </summary>
              <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-x-auto">
                {JSON.stringify(check.details, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}

// Icons
function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function AlertIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  );
}

function DangerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  );
}
