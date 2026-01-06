import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  apiKeysApi,
  tenantsApi,
  getErrorMessage,
  type APIKey,
  type CreateAPIKeyRequest,
} from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

export function ApiKeysPage() {
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newKeyResult, setNewKeyResult] = useState<{ key: APIKey; plaintext: string } | null>(null)

  const { data: apiKeys, isLoading } = useQuery({
    queryKey: ['apiKeys'],
    queryFn: () => apiKeysApi.list().then((r) => r.data),
  })

  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then((r) => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (data: CreateAPIKeyRequest) => apiKeysApi.create(data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] })
      const created = response.data
      setNewKeyResult({
        key: {
          id: created.id,
          tenant_id: created.tenant_id,
          name: created.name,
          key_prefix: created.key_prefix,
          permissions: created.permissions,
          rate_limit: created.rate_limit,
          is_active: true,
          expires_at: created.expires_at,
          created_at: created.created_at,
          description: null,
          last_used_at: null,
          use_count: 0,
        },
        plaintext: created.key,
      })
      setIsCreateOpen(false)
      toast.success('API key created successfully')
    },
    onError: (error) => {
      toast.error('Failed to create API key', {
        description: getErrorMessage(error),
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiKeysApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] })
      toast.success('API key deleted')
    },
    onError: (error) => {
      toast.error('Failed to delete API key', {
        description: getErrorMessage(error),
      })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, activate }: { id: number; activate: boolean }) =>
      activate ? apiKeysApi.activate(id) : apiKeysApi.deactivate(id),
    onSuccess: (_, { activate }) => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] })
      toast.success(activate ? 'API key activated' : 'API key deactivated')
    },
    onError: (error, { activate }) => {
      toast.error(`Failed to ${activate ? 'activate' : 'deactivate'} API key`, {
        description: getErrorMessage(error),
      })
    },
  })

  const getTenantName = (tenantId: number) => {
    return tenants?.find((t) => t.id === tenantId)?.name ?? `Tenant ${tenantId}`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">API Keys</h1>
          <p className="text-muted-foreground">Manage API keys for accessing GlassTrax data</p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>Create API Key</Button>
          </DialogTrigger>
          <DialogContent>
            <CreateKeyForm
              tenants={tenants ?? []}
              onSubmit={(data) => createMutation.mutate(data)}
              isLoading={createMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* New Key Alert */}
      {newKeyResult && (
        <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
          <AlertTitle className="text-green-800 dark:text-green-200">
            API Key Created Successfully
          </AlertTitle>
          <AlertDescription className="mt-2">
            <p className="mb-2 text-green-700 dark:text-green-300">
              Copy this key now. You won't be able to see it again!
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded border bg-white p-2 font-mono text-sm break-all dark:bg-black">
                {newKeyResult.plaintext}
              </code>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(newKeyResult.plaintext)
                  toast.success('API key copied to clipboard')
                }}
              >
                Copy
              </Button>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="mt-2"
              onClick={() => setNewKeyResult(null)}
            >
              Dismiss
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Keys Table */}
      <Card>
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
          <CardDescription>
            {apiKeys?.length ?? 0} key{apiKeys?.length !== 1 ? 's' : ''} in database
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-8 text-center">Loading...</div>
          ) : apiKeys && apiKeys.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key Prefix</TableHead>
                  <TableHead>Application</TableHead>
                  <TableHead>Permissions</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {apiKeys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className="font-medium">{key.name}</TableCell>
                    <TableCell>
                      <code className="bg-muted rounded px-1 text-sm">{key.key_prefix}...</code>
                    </TableCell>
                    <TableCell>{getTenantName(key.tenant_id)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {key.permissions.slice(0, 3).map((perm) => (
                          <Badge key={perm} variant="secondary" className="text-xs">
                            {perm}
                          </Badge>
                        ))}
                        {key.permissions.length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{key.permissions.length - 3}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={key.is_active ? 'default' : 'secondary'}>
                        {key.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-muted-foreground text-sm">
                        {key.use_count} requests
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            toggleMutation.mutate({ id: key.id, activate: !key.is_active })
                          }
                        >
                          {key.is_active ? 'Deactivate' : 'Activate'}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive"
                          onClick={() => {
                            if (confirm('Are you sure you want to delete this API key?')) {
                              deleteMutation.mutate(key.id)
                            }
                          }}
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-muted-foreground py-8 text-center">
              No API keys yet. Create one to get started.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// Available permissions for API keys
const AVAILABLE_PERMISSIONS = [
  { id: 'customers:read', label: 'Customers', description: 'Read customer data' },
  { id: 'orders:read', label: 'Orders', description: 'Read order data' },
] as const

interface CreateKeyFormProps {
  tenants: { id: number; name: string }[]
  onSubmit: (data: CreateAPIKeyRequest) => void
  isLoading: boolean
}

function CreateKeyForm({ tenants, onSubmit, isLoading }: CreateKeyFormProps) {
  const [formData, setFormData] = useState({
    name: '',
    tenant_id: tenants[0]?.id ?? 0,
    permissions: AVAILABLE_PERMISSIONS.map((p) => p.id) as string[],
    rate_limit: 60,
  })

  const handlePermissionToggle = (permissionId: string, checked: boolean) => {
    setFormData((prev) => ({
      ...prev,
      permissions: checked
        ? [...prev.permissions, permissionId]
        : prev.permissions.filter((p) => p !== permissionId),
    }))
  }

  const handleSelectAll = () => {
    setFormData((prev) => ({
      ...prev,
      permissions: AVAILABLE_PERMISSIONS.map((p) => p.id),
    }))
  }

  const handleClearAll = () => {
    setFormData((prev) => ({
      ...prev,
      permissions: [],
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.permissions.length === 0) {
      toast.error('Please select at least one permission')
      return
    }
    onSubmit({
      tenant_id: formData.tenant_id,
      name: formData.name,
      permissions: formData.permissions,
      rate_limit: formData.rate_limit,
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>Create New API Key</DialogTitle>
        <DialogDescription>Create a new API key for accessing GlassTrax data</DialogDescription>
      </DialogHeader>

      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <Label htmlFor="name">Key Name</Label>
          <Input
            id="name"
            placeholder="e.g., Production, Development"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="tenant">Application</Label>
          <select
            id="tenant"
            className="border-input bg-background flex h-10 w-full rounded-md border px-3 py-2 text-sm"
            value={formData.tenant_id}
            onChange={(e) => setFormData({ ...formData, tenant_id: Number(e.target.value) })}
          >
            {tenants.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.name}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-2">
          <div className="flex items-center justify-between">
            <Label>Permissions</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={handleSelectAll}
              >
                Select All
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={handleClearAll}
              >
                Clear
              </Button>
            </div>
          </div>
          <div className="space-y-3 rounded-md border p-3">
            {AVAILABLE_PERMISSIONS.map((permission) => (
              <div key={permission.id} className="flex items-start space-x-3">
                <Checkbox
                  id={permission.id}
                  checked={formData.permissions.includes(permission.id)}
                  onCheckedChange={(checked) =>
                    handlePermissionToggle(permission.id, checked === true)
                  }
                />
                <div className="grid gap-0.5 leading-none">
                  <label htmlFor={permission.id} className="cursor-pointer text-sm font-medium">
                    {permission.label}
                  </label>
                  <p className="text-muted-foreground text-xs">{permission.description}</p>
                </div>
              </div>
            ))}
          </div>
          {formData.permissions.length === 0 && (
            <p className="text-destructive text-xs">At least one permission is required</p>
          )}
        </div>

        <div className="grid gap-2">
          <Label htmlFor="rateLimit">Rate Limit (requests/minute)</Label>
          <Input
            id="rateLimit"
            type="number"
            min={1}
            max={1000}
            value={formData.rate_limit}
            onChange={(e) => setFormData({ ...formData, rate_limit: Number(e.target.value) })}
          />
        </div>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Creating...' : 'Create Key'}
        </Button>
      </DialogFooter>
    </form>
  )
}
