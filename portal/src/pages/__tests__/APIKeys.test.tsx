import { describe, it, expect } from 'vitest'
import { renderAuthenticated, screen, waitFor } from '@/__tests__/test-utils'
import { ApiKeysPage } from '../ApiKeys'

describe('ApiKeys', () => {
  it('renders without crashing', async () => {
    renderAuthenticated(<ApiKeysPage />)

    await waitFor(() => {
      expect(document.body).toBeInTheDocument()
    })
  })

  it('displays API keys after loading', async () => {
    renderAuthenticated(<ApiKeysPage />)

    await waitFor(
      () => {
        // MSW returns mock API keys
        expect(screen.getByText(/Development Key/i)).toBeInTheDocument()
      },
      { timeout: 3000 }
    )
  })

  it('shows key prefix in table', async () => {
    renderAuthenticated(<ApiKeysPage />)

    await waitFor(
      () => {
        // MSW returns keys with prefixes
        expect(screen.getByText(/gtb_dev12345/i)).toBeInTheDocument()
      },
      { timeout: 3000 }
    )
  })

  it('displays permissions for keys', async () => {
    renderAuthenticated(<ApiKeysPage />)

    await waitFor(
      () => {
        // First key has customers:read permission
        expect(screen.getByText(/customers:read/i)).toBeInTheDocument()
      },
      { timeout: 3000 }
    )
  })

  it('has create key button', async () => {
    renderAuthenticated(<ApiKeysPage />)

    await waitFor(
      () => {
        // Look for create/add button
        const createButton = screen.getByRole('button', { name: /create|add|new/i })
        expect(createButton).toBeInTheDocument()
      },
      { timeout: 3000 }
    )
  })
})
