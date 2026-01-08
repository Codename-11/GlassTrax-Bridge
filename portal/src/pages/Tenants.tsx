import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { tenantsApi, getErrorMessage, formatLocalDate, type Tenant } from '@/lib/api'
import { Button } from '@/components/ui/button'
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
import { Switch } from '@/components/ui/switch'

export function TenantsPage() {
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null)

  const { data: tenants, isLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then((r) => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; contact_email?: string }) =>
      tenantsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      setIsCreateOpen(false)
      toast.success('Application registered successfully')
    },
    onError: (error) => {
      toast.error('Failed to register application', {
        description: getErrorMessage(error),
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number
      data: { name?: string; description?: string; contact_email?: string; is_active?: boolean }
    }) => tenantsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      setEditingTenant(null)
      toast.success('Application updated successfully')
    },
    onError: (error) => {
      toast.error('Failed to update application', {
        description: getErrorMessage(error),
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => tenantsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] })
      toast.success('Application deleted successfully')
    },
    onError: (error) => {
      toast.error('Failed to delete application', {
        description: getErrorMessage(error),
      })
    },
  })

  // Filter out System tenant from display (or mark it specially)
  const userTenants = tenants?.filter((t) => t.name !== 'System') ?? []
  const systemTenant = tenants?.find((t) => t.name === 'System')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Applications</h1>
          <p className="text-muted-foreground">Manage apps and services that connect to the API</p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>Register Application</Button>
          </DialogTrigger>
          <DialogContent>
            <CreateAppForm
              onSubmit={(data) => createMutation.mutate(data)}
              isLoading={createMutation.isPending}
            />
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Registered Applications</CardTitle>
          <CardDescription>
            {userTenants.length} application{userTenants.length !== 1 ? 's' : ''} registered
            {systemTenant && <span className="text-muted-foreground ml-2">(+ 1 system)</span>}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-8 text-center">Loading...</div>
          ) : userTenants.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {userTenants.map((tenant) => (
                  <TableRow key={tenant.id}>
                    <TableCell className="font-mono">{tenant.id}</TableCell>
                    <TableCell className="font-medium">{tenant.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {tenant.description || '-'}
                    </TableCell>
                    <TableCell>{tenant.contact_email || '-'}</TableCell>
                    <TableCell>
                      <Badge variant={tenant.is_active ? 'default' : 'secondary'}>
                        {tenant.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatLocalDate(tenant.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="ghost" size="sm" onClick={() => setEditingTenant(tenant)}>
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive"
                          onClick={() => {
                            if (
                              confirm(
                                `Delete "${tenant.name}"?\n\nThis will also delete all API keys associated with this application. This action cannot be undone.`
                              )
                            ) {
                              deleteMutation.mutate(tenant.id)
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
              No applications registered yet. Register one to get started.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog
        open={editingTenant !== null}
        onOpenChange={(open) => !open && setEditingTenant(null)}
      >
        <DialogContent>
          {editingTenant && (
            <EditAppForm
              tenant={editingTenant}
              onSubmit={(data) => updateMutation.mutate({ id: editingTenant.id, data })}
              isLoading={updateMutation.isPending}
              onCancel={() => setEditingTenant(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

interface CreateAppFormProps {
  onSubmit: (data: { name: string; description?: string; contact_email?: string }) => void
  isLoading: boolean
}

function CreateAppForm({ onSubmit, isLoading }: CreateAppFormProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    contact_email: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      name: formData.name,
      description: formData.description || undefined,
      contact_email: formData.contact_email || undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>Register Application</DialogTitle>
        <DialogDescription>Add an app or service that will connect to the API</DialogDescription>
      </DialogHeader>

      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <Label htmlFor="name">Application Name</Label>
          <Input
            id="name"
            placeholder="e.g., Warehouse App, Sales Dashboard, Mobile App"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="description">Description (optional)</Label>
          <Input
            id="description"
            placeholder="What does this application do?"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="email">Developer Contact (optional)</Label>
          <Input
            id="email"
            type="email"
            placeholder="developer@example.com"
            value={formData.contact_email}
            onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
          />
        </div>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Registering...' : 'Register Application'}
        </Button>
      </DialogFooter>
    </form>
  )
}

interface EditAppFormProps {
  tenant: Tenant
  onSubmit: (data: {
    name?: string
    description?: string
    contact_email?: string
    is_active?: boolean
  }) => void
  isLoading: boolean
  onCancel: () => void
}

function EditAppForm({ tenant, onSubmit, isLoading, onCancel }: EditAppFormProps) {
  const [formData, setFormData] = useState({
    name: tenant.name,
    description: tenant.description || '',
    contact_email: tenant.contact_email || '',
    is_active: tenant.is_active,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      name: formData.name,
      description: formData.description || undefined,
      contact_email: formData.contact_email || undefined,
      is_active: formData.is_active,
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>Edit Application</DialogTitle>
        <DialogDescription>Update application details. ID: {tenant.id}</DialogDescription>
      </DialogHeader>

      <div className="grid gap-4 py-4">
        <div className="grid gap-2">
          <Label htmlFor="edit-name">Application Name</Label>
          <Input
            id="edit-name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="edit-description">Description</Label>
          <Input
            id="edit-description"
            placeholder="What does this application do?"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="edit-email">Developer Contact</Label>
          <Input
            id="edit-email"
            type="email"
            placeholder="developer@example.com"
            value={formData.contact_email}
            onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
          />
        </div>

        <div className="flex items-center justify-between rounded-lg border p-4">
          <div className="space-y-0.5">
            <Label>Active</Label>
            <p className="text-muted-foreground text-sm">
              Inactive applications cannot use their API keys
            </p>
          </div>
          <Switch
            checked={formData.is_active}
            onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
          />
        </div>
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : 'Save Changes'}
        </Button>
      </DialogFooter>
    </form>
  )
}
