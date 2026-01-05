import { Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { Sidebar } from './Sidebar'

export function Layout() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="border-primary h-8 w-8 animate-spin rounded-full border-b-2"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="bg-background flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="container px-8 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
