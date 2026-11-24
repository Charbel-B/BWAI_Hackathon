import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { fr } from '@/i18n/fr'

import { HealthStatus } from './health-status'

function renderWithQuery() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <HealthStatus />
    </QueryClientProvider>,
  )
}

describe('HealthStatus', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('annonce le serveur disponible quand l’API répond', async () => {
    const body = { status: 'ok', version: '0.1.0', config_sha256: 'abc' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(body)))
    renderWithQuery()
    expect(await screen.findByText(fr.health.ok)).toBeInTheDocument()
  })

  it('annonce le serveur injoignable quand l’API échoue', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 500 })))
    renderWithQuery()
    expect(await screen.findByRole('alert')).toHaveTextContent(fr.health.error)
  })
})
