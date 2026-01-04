import { Outlet, Navigate } from 'react-router-dom';
import { useAuth } from '@/lib/auth';
import { Sidebar } from './Sidebar';

export function Layout() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="container py-6 px-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
