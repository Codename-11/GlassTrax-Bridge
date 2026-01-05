import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@/__tests__/test-utils'
import { DashboardPage } from '../Dashboard'

describe('Dashboard', () => {
  it('renders without crashing', async () => {
    render(<DashboardPage />)

    // Dashboard should have the title
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument()
    })
  })

  it('renders stats cards', async () => {
    const { container } = render(<DashboardPage />)

    // Dashboard should render stat cards
    await waitFor(() => {
      expect(container.querySelectorAll('[data-slot="card"]').length).toBeGreaterThan(0)
    })
  })

  it('shows version badge', async () => {
    render(<DashboardPage />)

    await waitFor(
      () => {
        // MSW returns version "1.2.0" - look for the version badge
        expect(screen.getByText(/v1\.2\.0/)).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })

  it('displays quick action buttons', async () => {
    render(<DashboardPage />)

    await waitFor(
      () => {
        // Look for Create API Key button
        expect(screen.getByRole('button', { name: /create api key/i })).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })
})
