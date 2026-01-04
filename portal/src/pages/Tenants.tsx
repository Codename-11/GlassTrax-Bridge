import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { tenantsApi, getErrorMessage, formatLocalDate } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export function TenantsPage() {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const { data: tenants, isLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; contact_email?: string }) =>
      tenantsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] });
      setIsCreateOpen(false);
      toast.success('Application registered successfully');
    },
    onError: (error) => {
      toast.error('Failed to register application', {
        description: getErrorMessage(error),
      });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Applications</h1>
          <p className="text-muted-foreground">
            Manage apps and services that connect to the API
          </p>
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
            {tenants?.length ?? 0} application{tenants?.length !== 1 ? 's' : ''} registered
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">Loading...</div>
          ) : tenants && tenants.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants.map((tenant) => (
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
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No applications registered yet. Register one to get started.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

interface CreateAppFormProps {
  onSubmit: (data: { name: string; description?: string; contact_email?: string }) => void;
  isLoading: boolean;
}

function CreateAppForm({ onSubmit, isLoading }: CreateAppFormProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    contact_email: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name: formData.name,
      description: formData.description || undefined,
      contact_email: formData.contact_email || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>Register Application</DialogTitle>
        <DialogDescription>
          Add an app or service that will connect to the API
        </DialogDescription>
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
  );
}
