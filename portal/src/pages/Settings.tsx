import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  configApi,
  adminApi,
  dsnsApi,
  testDsnApi,
  testAgentApi,
  getErrorMessage,
  type ConfigData,
} from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'

// Deep comparison helper
function deepEqual(obj1: unknown, obj2: unknown): boolean {
  if (obj1 === obj2) return true
  if (typeof obj1 !== 'object' || typeof obj2 !== 'object') return false
  if (obj1 === null || obj2 === null) return false

  const keys1 = Object.keys(obj1 as object)
  const keys2 = Object.keys(obj2 as object)

  if (keys1.length !== keys2.length) return false

  for (const key of keys1) {
    if (
      !deepEqual((obj1 as Record<string, unknown>)[key], (obj2 as Record<string, unknown>)[key])
    ) {
      return false
    }
  }
  return true
}

// Deep clone helper
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj))
}

export function SettingsPage() {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<ConfigData | null>(null)
  const [originalData, setOriginalData] = useState<ConfigData | null>(null)
  const [showRestartAlert, setShowRestartAlert] = useState(false)
  const [restartRequiredFields, setRestartRequiredFields] = useState<string[]>([])

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // DSN test state
  const [dsnTestResult, setDsnTestResult] = useState<{
    success: boolean
    message: string
    tables_found?: number
  } | null>(null)

  // Agent test state
  const [agentTestResult, setAgentTestResult] = useState<{
    connected: boolean
    message: string
    agent_version?: string
    database_connected?: boolean
  } | null>(null)

  const {
    data: config,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['config'],
    queryFn: () => configApi.get().then((r) => r.data),
    refetchOnWindowFocus: false,
  })

  // Fetch available DSNs
  const { data: dsnsData } = useQuery({
    queryKey: ['dsns'],
    queryFn: () => dsnsApi.list().then((r) => r.data),
    refetchOnWindowFocus: false,
  })

  // Test DSN mutation
  const testDsnMutation = useMutation({
    mutationFn: (dsn: string) => testDsnApi.test({ dsn, readonly: true }),
    onSuccess: (response) => {
      const result = response.data
      setDsnTestResult({
        success: result.success,
        message: result.message,
        tables_found: result.tables_found,
      })
      if (result.success) {
        toast.success('DSN Test Passed', { description: result.message })
      } else {
        toast.error('DSN Test Failed', { description: result.message })
      }
    },
    onError: (error) => {
      setDsnTestResult({
        success: false,
        message: getErrorMessage(error),
      })
      toast.error('DSN Test Failed', { description: getErrorMessage(error) })
    },
  })

  // Test Agent mutation
  const testAgentMutation = useMutation({
    mutationFn: (params: { url: string; api_key: string }) =>
      testAgentApi.test({ url: params.url, api_key: params.api_key, timeout: 30 }),
    onSuccess: (response) => {
      const result = response.data
      setAgentTestResult({
        connected: result.connected,
        message: result.message,
        agent_version: result.agent_version,
        database_connected: result.database_connected,
      })
      if (result.connected) {
        toast.success('Agent Connection Successful', { description: result.message })
      } else {
        toast.error('Agent Connection Failed', { description: result.message })
      }
    },
    onError: (error) => {
      setAgentTestResult({
        connected: false,
        message: getErrorMessage(error),
      })
      toast.error('Agent Connection Failed', { description: getErrorMessage(error) })
    },
  })

  // Initialize form data when config loads
  useEffect(() => {
    if (config && !formData) {
      setFormData(deepClone(config))
      setOriginalData(deepClone(config))
    }
  }, [config, formData])

  // Track dirty state
  const isDirty = formData && originalData ? !deepEqual(formData, originalData) : false

  // Warn before leaving with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault()
        e.returnValue = ''
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isDirty])

  const saveMutation = useMutation({
    mutationFn: (data: Partial<ConfigData>) => configApi.update(data),
    onSuccess: (response) => {
      const result = response.data
      if (result.restart_required) {
        setShowRestartAlert(true)
        setRestartRequiredFields(result.restart_required_fields)
        toast.warning('Configuration saved', {
          description: 'Some changes require a server restart to take effect.',
        })
      } else {
        toast.success('Configuration saved', {
          description: `${result.changed_fields.length} field(s) updated.`,
        })
      }
      // Update original data to match saved state
      setOriginalData(deepClone(formData))
      queryClient.invalidateQueries({ queryKey: ['config'] })
      queryClient.invalidateQueries({ queryKey: ['health'] })
    },
    onError: (error) => {
      toast.error('Failed to save configuration', {
        description: getErrorMessage(error),
      })
    },
  })

  const passwordMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      adminApi.changePassword(data),
    onSuccess: () => {
      toast.success('Password changed', {
        description: 'Your password has been updated successfully.',
      })
      // Clear password fields
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    },
    onError: (error) => {
      toast.error('Failed to change password', {
        description: getErrorMessage(error),
      })
    },
  })

  const handleSave = () => {
    if (formData) {
      saveMutation.mutate(formData)
    }
  }

  const handleReset = () => {
    if (originalData) {
      setFormData(deepClone(originalData))
    }
  }

  const handlePasswordChange = () => {
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters')
      return
    }
    passwordMutation.mutate({
      current_password: currentPassword,
      new_password: newPassword,
    })
  }

  // Form update helpers
  const updateDatabase = useCallback((field: keyof ConfigData['database'], value: unknown) => {
    setFormData((prev) =>
      prev
        ? {
            ...prev,
            database: { ...prev.database, [field]: value },
          }
        : null
    )
  }, [])

  const updateApplication = useCallback((field: string, value: unknown) => {
    setFormData((prev) => {
      if (!prev) return null
      const parts = field.split('.')
      if (parts.length === 1) {
        return {
          ...prev,
          application: { ...prev.application, [field]: value },
        }
      } else if (parts[0] === 'logging') {
        return {
          ...prev,
          application: {
            ...prev.application,
            logging: { ...prev.application.logging, [parts[1]]: value },
          },
        }
      } else if (parts[0] === 'performance') {
        return {
          ...prev,
          application: {
            ...prev.application,
            performance: { ...prev.application.performance, [parts[1]]: value },
          },
        }
      }
      return prev
    })
  }, [])

  const updateFeatures = useCallback((field: keyof ConfigData['features'], value: boolean) => {
    setFormData((prev) =>
      prev
        ? {
            ...prev,
            features: { ...prev.features, [field]: value },
          }
        : null
    )
  }, [])

  const updateAdmin = useCallback((field: keyof ConfigData['admin'], value: string) => {
    setFormData((prev) =>
      prev
        ? {
            ...prev,
            admin: { ...prev.admin, [field]: value },
          }
        : null
    )
  }, [])

  const updateAgent = useCallback((field: keyof ConfigData['agent'], value: unknown) => {
    setFormData((prev) =>
      prev
        ? {
            ...prev,
            agent: { ...prev.agent, [field]: value },
          }
        : null
    )
  }, [])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground">Loading configuration...</p>
        </div>
        <Card>
          <CardContent className="py-8">
            <div className="text-center">
              <div className="border-primary mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-b-2"></div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !formData) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground">Configure application settings</p>
        </div>
        <Card>
          <CardContent className="py-8">
            <div className="text-center text-red-500">
              Failed to load configuration: {getErrorMessage(error)}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with save button */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground">
            Configure application settings
            <span className="mx-2">·</span>
            <a
              href="https://codename-11.github.io/GlassTrax-Bridge/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary inline-flex items-center gap-1 hover:underline"
            >
              <BookOpenIcon className="h-3.5 w-3.5" />
              View Documentation
            </a>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isDirty && (
            <Badge
              variant="outline"
              className="border-yellow-500/50 bg-yellow-500/10 text-yellow-600"
            >
              Unsaved Changes
            </Badge>
          )}
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={!isDirty || saveMutation.isPending}
          >
            Reset
          </Button>
          <Button onClick={handleSave} disabled={!isDirty || saveMutation.isPending}>
            {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {/* Restart Alert */}
      {showRestartAlert && (
        <Alert className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
          <AlertTriangleIcon className="h-4 w-4 text-yellow-600" />
          <AlertTitle className="text-yellow-800 dark:text-yellow-200">Restart Required</AlertTitle>
          <AlertDescription className="text-yellow-700 dark:text-yellow-300">
            The following changes require a server restart to take effect:{' '}
            <span className="font-mono text-sm">{restartRequiredFields.join(', ')}</span>
            <div className="mt-2">
              <Button variant="outline" size="sm" onClick={() => setShowRestartAlert(false)}>
                Dismiss
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Data Source Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DatabaseIcon className="h-5 w-5" />
            Data Source
            <Badge
              variant={formData.agent.enabled ? 'default' : 'secondary'}
              className="ml-2 text-xs"
            >
              {formData.agent.enabled ? 'Remote Agent' : 'Direct ODBC'}
            </Badge>
          </CardTitle>
          <CardDescription>
            Configure how the API connects to the GlassTrax database
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Display Name - applies to both modes */}
          <div className="max-w-md space-y-2">
            <Label htmlFor="friendly_name">Display Name</Label>
            <Input
              id="friendly_name"
              value={formData.database.friendly_name}
              onChange={(e) => updateDatabase('friendly_name', e.target.value)}
              placeholder="e.g., TGI Database"
            />
            <p className="text-muted-foreground text-xs">Shown in the dashboard</p>
          </div>

          <Separator />

          {/* Connection Mode Toggle */}
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-0.5">
              <Label className="text-base">Connection Mode</Label>
              <p className="text-muted-foreground text-sm">
                {formData.agent.enabled
                  ? 'Using remote Windows agent for database queries'
                  : 'Direct ODBC connection to local database'}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span
                className={`text-sm ${!formData.agent.enabled ? 'font-medium' : 'text-muted-foreground'}`}
              >
                Direct
              </span>
              <Switch
                checked={formData.agent.enabled}
                onCheckedChange={(checked) => {
                  updateAgent('enabled', checked)
                  // Clear test results when switching modes
                  setDsnTestResult(null)
                  setAgentTestResult(null)
                }}
              />
              <span
                className={`text-sm ${formData.agent.enabled ? 'font-medium' : 'text-muted-foreground'}`}
              >
                Agent
              </span>
            </div>
          </div>

          {/* Direct ODBC Settings */}
          {!formData.agent.enabled && (
            <div className="space-y-4 rounded-lg border border-dashed p-4">
              <div className="flex items-center gap-2">
                <DatabaseIcon className="h-4 w-4" />
                <h4 className="font-medium">Direct ODBC Connection</h4>
              </div>
              <p className="text-muted-foreground text-xs">
                Connect directly to GlassTrax via ODBC. Requires the API to run on Windows with
                Pervasive ODBC drivers installed.
              </p>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="dsn">
                    ODBC Data Source Name (DSN)
                    <Badge variant="outline" className="ml-2 text-xs">
                      Restart Required
                    </Badge>
                  </Label>
                  <div className="flex gap-2">
                    <Select
                      value={formData.database.dsn}
                      onValueChange={(value) => {
                        updateDatabase('dsn', value)
                        setDsnTestResult(null)
                      }}
                    >
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select DSN" />
                      </SelectTrigger>
                      <SelectContent>
                        {dsnsData?.dsns.map((dsn) => (
                          <SelectItem key={dsn.name} value={dsn.name}>
                            <div className="flex items-center gap-2">
                              <span>{dsn.name}</span>
                              {dsn.is_pervasive && (
                                <span className="text-xs font-medium text-green-600">
                                  (Pervasive)
                                </span>
                              )}
                            </div>
                          </SelectItem>
                        ))}
                        {formData.database.dsn &&
                          dsnsData?.dsns &&
                          !dsnsData.dsns.find((d) => d.name === formData.database.dsn) && (
                            <SelectItem value={formData.database.dsn}>
                              {formData.database.dsn} (current)
                            </SelectItem>
                          )}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => testDsnMutation.mutate(formData.database.dsn)}
                      disabled={!formData.database.dsn || testDsnMutation.isPending}
                    >
                      {testDsnMutation.isPending ? 'Testing...' : 'Test'}
                    </Button>
                  </div>
                  <p className="text-muted-foreground text-xs">
                    {dsnsData?.architecture && (
                      <span className="font-medium">{dsnsData.architecture} DSNs. </span>
                    )}
                    {dsnsData?.pervasive_dsns.length
                      ? `${dsnsData.pervasive_dsns.length} Pervasive DSN(s) found.`
                      : 'No Pervasive DSNs found.'}
                  </p>
                  {dsnTestResult && (
                    <div
                      className={`rounded p-2 text-xs ${
                        dsnTestResult.success
                          ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300'
                          : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300'
                      }`}
                    >
                      {dsnTestResult.success ? '✓' : '✗'} {dsnTestResult.message}
                      {dsnTestResult.tables_found !== undefined && (
                        <span className="ml-1">({dsnTestResult.tables_found} tables)</span>
                      )}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timeout">Connection Timeout (seconds)</Label>
                  <Input
                    id="timeout"
                    type="number"
                    min={1}
                    max={300}
                    value={formData.database.timeout}
                    onChange={(e) => updateDatabase('timeout', parseInt(e.target.value) || 30)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Remote Agent Settings */}
          {formData.agent.enabled && (
            <div className="space-y-4 rounded-lg border border-dashed p-4">
              <div className="flex items-center gap-2">
                <ServerIcon className="h-4 w-4" />
                <h4 className="font-medium">Remote Agent Connection</h4>
              </div>
              <p className="text-muted-foreground text-xs">
                Connect to a Windows-hosted GlassTrax API Agent. Required when running in Docker or
                on non-Windows systems.
              </p>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="agent_url">Agent URL</Label>
                  <Input
                    id="agent_url"
                    value={formData.agent.url}
                    onChange={(e) => updateAgent('url', e.target.value)}
                    placeholder="http://192.168.1.100:8001"
                  />
                  <p className="text-muted-foreground text-xs">
                    Full URL of the Windows machine running the agent
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="agent_key">Agent API Key</Label>
                  <Input
                    id="agent_key"
                    type="password"
                    value={formData.agent.api_key}
                    onChange={(e) => updateAgent('api_key', e.target.value)}
                    placeholder="gta_..."
                  />
                  <p className="text-muted-foreground text-xs">
                    API key from agent console on first run
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="agent_timeout">Request Timeout (seconds)</Label>
                  <Input
                    id="agent_timeout"
                    type="number"
                    min={1}
                    max={300}
                    value={formData.agent.timeout}
                    onChange={(e) => updateAgent('timeout', parseInt(e.target.value) || 30)}
                  />
                </div>
              </div>

              <div className="pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setAgentTestResult(null)
                    testAgentMutation.mutate({
                      url: formData.agent.url,
                      api_key: formData.agent.api_key,
                    })
                  }}
                  disabled={
                    !formData.agent.url || !formData.agent.api_key || testAgentMutation.isPending
                  }
                >
                  {testAgentMutation.isPending ? 'Testing...' : 'Test Connection'}
                </Button>
              </div>

              {agentTestResult && (
                <Alert variant={agentTestResult.connected ? 'default' : 'destructive'}>
                  {agentTestResult.connected ? (
                    <CheckCircleIcon className="h-4 w-4" />
                  ) : (
                    <XCircleIcon className="h-4 w-4" />
                  )}
                  <AlertTitle>
                    {agentTestResult.connected ? 'Connected' : 'Connection Failed'}
                  </AlertTitle>
                  <AlertDescription>
                    {agentTestResult.message}
                    {agentTestResult.agent_version && (
                      <span className="mt-1 block text-xs">
                        Agent version: {agentTestResult.agent_version}
                      </span>
                    )}
                  </AlertDescription>
                </Alert>
              )}

              <Separator />

              <div className="text-muted-foreground text-sm">
                <p className="mb-2 font-medium">Agent Setup:</p>
                <ol className="list-inside list-decimal space-y-1 text-xs">
                  <li>
                    On Windows, start the agent:{' '}
                    <code className="bg-muted rounded px-1 py-0.5">.\agent\run_agent.bat</code>
                  </li>
                  <li>Copy the API key shown on first run</li>
                  <li>Enter the agent URL and API key above</li>
                </ol>
                <p className="mt-2">
                  <a
                    href="https://codename-11.github.io/GlassTrax-Bridge/guide/agent-setup.html"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary inline-flex items-center gap-1 hover:underline"
                  >
                    <BookOpenIcon className="h-3 w-3" />
                    View agent setup documentation
                  </a>
                </p>
              </div>
            </div>
          )}

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <Label>Read-Only Mode</Label>
                <Badge variant="secondary" className="text-xs">
                  Enforced
                </Badge>
              </div>
              <p className="text-muted-foreground text-xs">
                GlassTrax Bridge is designed for read-only access to protect your ERP data.
              </p>
            </div>
            <Switch checked={formData.database.readonly} disabled={true} />
          </div>
        </CardContent>
      </Card>

      {/* Application Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <SettingsIcon className="h-5 w-5" />
            Application Settings
          </CardTitle>
          <CardDescription>General application configuration</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <Input
                id="timezone"
                value={formData.application.timezone}
                onChange={(e) => updateApplication('timezone', e.target.value)}
                placeholder="America/New_York"
              />
              <p className="text-muted-foreground text-xs">IANA timezone name</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="log_level">Log Level</Label>
              <Select
                value={formData.application.logging.level}
                onValueChange={(value) => updateApplication('logging.level', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select log level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="DEBUG">DEBUG</SelectItem>
                  <SelectItem value="INFO">INFO</SelectItem>
                  <SelectItem value="WARNING">WARNING</SelectItem>
                  <SelectItem value="ERROR">ERROR</SelectItem>
                  <SelectItem value="CRITICAL">CRITICAL</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="query_timeout">Query Timeout (seconds)</Label>
              <Input
                id="query_timeout"
                type="number"
                min={10}
                max={600}
                value={formData.application.performance.query_timeout}
                onChange={(e) =>
                  updateApplication('performance.query_timeout', parseInt(e.target.value) || 60)
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="fetch_size">Fetch Size (rows)</Label>
              <Input
                id="fetch_size"
                type="number"
                min={100}
                max={10000}
                value={formData.application.performance.fetch_size}
                onChange={(e) =>
                  updateApplication('performance.fetch_size', parseInt(e.target.value) || 1000)
                }
              />
            </div>
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Log to File</Label>
              <p className="text-muted-foreground text-xs">Write logs to file system</p>
            </div>
            <Switch
              checked={formData.application.logging.log_to_file}
              onCheckedChange={(checked) => updateApplication('logging.log_to_file', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Log to Console</Label>
              <p className="text-muted-foreground text-xs">Output logs to console</p>
            </div>
            <Switch
              checked={formData.application.logging.log_to_console}
              onCheckedChange={(checked) => updateApplication('logging.log_to_console', checked)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Feature Flags */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlagIcon className="h-5 w-5" />
            Feature Flags
          </CardTitle>
          <CardDescription>Enable or disable optional features</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Enable Caching</Label>
              <p className="text-muted-foreground text-xs">
                Cache query results for improved performance
              </p>
            </div>
            <Switch
              checked={formData.features.enable_caching}
              onCheckedChange={(checked) => updateFeatures('enable_caching', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Enable Exports</Label>
              <p className="text-muted-foreground text-xs">Allow data export functionality</p>
            </div>
            <Switch
              checked={formData.features.enable_exports}
              onCheckedChange={(checked) => updateFeatures('enable_exports', checked)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Admin Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserIcon className="h-5 w-5" />
            Admin Settings
          </CardTitle>
          <CardDescription>Portal authentication settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="max-w-md space-y-2">
            <Label htmlFor="admin_username">Admin Username</Label>
            <Input
              id="admin_username"
              value={formData.admin.username}
              onChange={(e) => updateAdmin('username', e.target.value)}
              placeholder="admin"
            />
          </div>

          <Separator />

          <div className="space-y-4">
            <div>
              <h4 className="flex items-center gap-2 text-sm font-medium">
                <KeyIcon className="h-4 w-4" />
                Change Password
              </h4>
              <p className="text-muted-foreground mt-1 text-xs">
                Update your admin portal password
              </p>
            </div>

            <div className="grid max-w-md gap-4">
              <div className="space-y-2">
                <Label htmlFor="current_password">Current Password</Label>
                <Input
                  id="current_password"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="new_password">New Password</Label>
                <Input
                  id="new_password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password (min 6 characters)"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm_password">Confirm New Password</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                />
                {confirmPassword && newPassword !== confirmPassword && (
                  <p className="text-xs text-red-500">Passwords do not match</p>
                )}
              </div>

              <Button
                onClick={handlePasswordChange}
                disabled={
                  !currentPassword ||
                  !newPassword ||
                  !confirmPassword ||
                  newPassword !== confirmPassword ||
                  newPassword.length < 6 ||
                  passwordMutation.isPending
                }
                className="w-fit"
              >
                {passwordMutation.isPending ? 'Changing...' : 'Change Password'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Icons
function DatabaseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
      />
    </svg>
  )
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  )
}

function FlagIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"
      />
    </svg>
  )
}

function UserIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
      />
    </svg>
  )
}

function AlertTriangleIcon({ className }: { className?: string }) {
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

function ServerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
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

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}

function XCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  )
}
