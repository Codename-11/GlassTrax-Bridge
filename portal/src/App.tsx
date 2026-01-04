import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider, MutationCache, QueryCache } from '@tanstack/react-query';
import { toast } from 'sonner';
import { AuthProvider } from '@/lib/auth';
import { ThemeProvider } from '@/lib/theme';
import { getErrorMessage } from '@/lib/api';
import { Layout } from '@/components/layout/Layout';
import { LoginPage } from '@/pages/Login';
import { DashboardPage } from '@/pages/Dashboard';
import { ApiKeysPage } from '@/pages/ApiKeys';
import { TenantsPage } from '@/pages/Tenants';
import { AccessLogsPage } from '@/pages/AccessLogs';
import { DiagnosticsPage } from '@/pages/Diagnostics';
import { SettingsPage } from '@/pages/Settings';
import { Toaster } from '@/components/ui/sonner';

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      // Only show toast for non-401 errors (401 is handled by redirect)
      const message = getErrorMessage(error);
      if (!message.includes('401')) {
        toast.error('Failed to fetch data', { description: message });
      }
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      // Only show toast if the mutation doesn't have its own onError handler
      if (!mutation.options.onError) {
        toast.error('Operation failed', { description: getErrorMessage(error) });
      }
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
});

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<Layout />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/keys" element={<ApiKeysPage />} />
                <Route path="/tenants" element={<TenantsPage />} />
                <Route path="/logs" element={<AccessLogsPage />} />
                <Route path="/diagnostics" element={<DiagnosticsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
          <Toaster />
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
