import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { accessLogsApi, tenantsApi, formatLocalTime, formatLocalDate, parseUTCDate, type AccessLog } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

type StatusFilter = 'all' | '2xx' | '4xx' | '5xx';
type MethodFilter = 'all' | 'GET' | 'POST' | 'PUT' | 'DELETE';

export function AccessLogsPage() {
  const [searchPath, setSearchPath] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [methodFilter, setMethodFilter] = useState<MethodFilter>('all');
  const [keyFilter, setKeyFilter] = useState('');
  const [tenantFilter, setTenantFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<string>('');

  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['accessLogs'],
    queryFn: () => accessLogsApi.list({ limit: 200 }).then((r) => r.data),
    refetchInterval: 10000, // Auto-refresh every 10 seconds
  });

  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.list().then((r) => r.data),
  });

  // Client-side filtering
  const filteredLogs = useMemo(() => {
    if (!logs) return [];

    return logs.filter((log) => {
      // Path search
      if (searchPath && !log.path.toLowerCase().includes(searchPath.toLowerCase())) {
        return false;
      }

      // Method filter
      if (methodFilter !== 'all' && log.method !== methodFilter) {
        return false;
      }

      // Status filter
      if (statusFilter !== 'all') {
        if (statusFilter === '2xx' && (log.status_code < 200 || log.status_code >= 300)) {
          return false;
        }
        if (statusFilter === '4xx' && (log.status_code < 400 || log.status_code >= 500)) {
          return false;
        }
        if (statusFilter === '5xx' && log.status_code < 500) {
          return false;
        }
      }

      // API Key filter
      if (keyFilter && (!log.key_prefix || !log.key_prefix.toLowerCase().includes(keyFilter.toLowerCase()))) {
        return false;
      }

      // Tenant filter
      if (tenantFilter !== 'all') {
        const tenantId = parseInt(tenantFilter, 10);
        if (log.tenant_id !== tenantId) {
          return false;
        }
      }

      // Date filter
      if (dateFilter) {
        const logDate = parseUTCDate(log.created_at);
        const filterDate = new Date(dateFilter);
        // Compare year, month, day only
        if (
          logDate.getFullYear() !== filterDate.getFullYear() ||
          logDate.getMonth() !== filterDate.getMonth() ||
          logDate.getDate() !== filterDate.getDate()
        ) {
          return false;
        }
      }

      return true;
    });
  }, [logs, searchPath, methodFilter, statusFilter, keyFilter, tenantFilter, dateFilter]);

  const getStatusColor = (status: number) => {
    if (status >= 500) return 'destructive';
    if (status >= 400) return 'secondary';
    return 'default';
  };

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'POST':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'PUT':
      case 'PATCH':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'DELETE':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const clearFilters = () => {
    setSearchPath('');
    setStatusFilter('all');
    setMethodFilter('all');
    setKeyFilter('');
    setTenantFilter('all');
    setDateFilter('');
  };

  const hasActiveFilters = searchPath || statusFilter !== 'all' || methodFilter !== 'all' || keyFilter || tenantFilter !== 'all' || dateFilter;

  const getTenantName = (tenantId: number | null) => {
    if (!tenantId || !tenants) return '';
    const tenant = tenants.find((t) => t.id === tenantId);
    return tenant?.name || '';
  };

  const exportToCSV = () => {
    if (!filteredLogs.length) return;

    const headers = ['Time', 'Method', 'Path', 'Query', 'Status', 'Duration (ms)', 'Application', 'API Key', 'Request ID'];
    const rows = filteredLogs.map((log) => [
      parseUTCDate(log.created_at).toISOString(),
      log.method,
      log.path,
      log.query_string || '',
      log.status_code.toString(),
      log.response_time_ms?.toFixed(0) || '',
      getTenantName(log.tenant_id),
      log.key_prefix || '',
      log.request_id || '',
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `access-logs-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Access Logs</h1>
          <p className="text-muted-foreground">
            View all API requests and their details
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportToCSV} disabled={!filteredLogs.length}>
            Export CSV
          </Button>
          <Button variant="outline" onClick={() => refetch()}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Filters</CardTitle>
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                Clear all
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-6">
            <div>
              <label className="text-sm font-medium mb-1.5 block">Date</label>
              <Input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Search Path</label>
              <Input
                placeholder="e.g., /api/v1/customers"
                value={searchPath}
                onChange={(e) => setSearchPath(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Method</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={methodFilter}
                onChange={(e) => setMethodFilter(e.target.value as MethodFilter)}
              >
                <option value="all">All Methods</option>
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Status</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              >
                <option value="all">All Statuses</option>
                <option value="2xx">Success (2xx)</option>
                <option value="4xx">Client Error (4xx)</option>
                <option value="5xx">Server Error (5xx)</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Application</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={tenantFilter}
                onChange={(e) => setTenantFilter(e.target.value)}
              >
                <option value="all">All Applications</option>
                {tenants?.map((tenant) => (
                  <option key={tenant.id} value={tenant.id.toString()}>
                    {tenant.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">API Key Prefix</label>
              <Input
                placeholder="e.g., gtb_abc123"
                value={keyFilter}
                onChange={(e) => setKeyFilter(e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Request Log</CardTitle>
          <CardDescription>
            Showing {filteredLogs.length} of {logs?.length ?? 0} requests (auto-refreshing)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">Loading...</div>
          ) : filteredLogs.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-36">Date/Time</TableHead>
                    <TableHead className="w-20">Method</TableHead>
                    <TableHead>Path</TableHead>
                    <TableHead className="w-24">Status</TableHead>
                    <TableHead className="w-24">Duration</TableHead>
                    <TableHead className="w-32">Application</TableHead>
                    <TableHead className="w-32">API Key</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLogs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        <div>{formatLocalDate(log.created_at)}</div>
                        <div>{formatLocalTime(log.created_at)}</div>
                      </TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${getMethodColor(log.method)}`}
                        >
                          {log.method}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {log.path}
                        {log.query_string && (
                          <span className="text-muted-foreground">?{log.query_string}</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusColor(log.status_code)}>
                          {log.status_code}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {log.response_time_ms?.toFixed(0)}ms
                      </TableCell>
                      <TableCell>
                        {log.tenant_id ? (
                          <span className="text-sm">{getTenantName(log.tenant_id)}</span>
                        ) : (
                          <span className="text-muted-foreground text-xs">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {log.key_prefix ? (
                          <code className="text-xs bg-muted px-1 rounded">
                            {log.key_prefix}...
                          </code>
                        ) : (
                          <span className="text-muted-foreground text-xs">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              {logs && logs.length > 0
                ? 'No logs match your filters.'
                : 'No access logs yet. Make some API requests to see them here.'}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
