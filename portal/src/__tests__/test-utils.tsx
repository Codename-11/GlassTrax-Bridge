import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/lib/auth'
import { ThemeProvider } from '@/lib/theme'

/**
 * Create a fresh QueryClient for each test.
 * Disables retries for faster test failures.
 */
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

interface WrapperProps {
  children: React.ReactNode
}

/**
 * Wrapper component that provides all necessary context providers.
 */
function AllProviders({ children }: WrapperProps) {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

/**
 * Custom render function that wraps components with all providers.
 *
 * Usage:
 *   import { render, screen } from '@/__tests__/test-utils';
 *   render(<MyComponent />);
 *   expect(screen.getByText('Hello')).toBeInTheDocument();
 */
function customRender(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  return render(ui, { wrapper: AllProviders, ...options })
}

/**
 * Render with a pre-authenticated state.
 * Sets a mock token in localStorage before rendering.
 */
function renderAuthenticated(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  localStorage.setItem('token', 'mock-jwt-token-12345')
  return customRender(ui, options)
}

// Re-export everything from testing-library
export * from '@testing-library/react'
// user-event has default export, import and re-export it
import userEvent from '@testing-library/user-event'
export { userEvent }

// Export custom render functions
export { customRender as render, renderAuthenticated }
