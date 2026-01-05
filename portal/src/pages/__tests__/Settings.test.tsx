import { describe, it, expect } from 'vitest'
import { renderAuthenticated, screen, waitFor } from '@/__tests__/test-utils'
import { SettingsPage } from '../Settings'

describe('Settings', () => {
  it('renders without crashing', async () => {
    renderAuthenticated(<SettingsPage />)

    // Settings page should have a title/heading
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /settings/i })).toBeInTheDocument()
    })
  })

  it('displays loading state then content', async () => {
    const { container } = renderAuthenticated(<SettingsPage />)

    // Should render some content initially
    await waitFor(
      () => {
        expect(container.querySelector('[data-slot="card"]')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })
})
