import createClient, { type Middleware } from 'openapi-fetch'

import { session } from '@/features/auth/session'

import type { paths } from './schema'

/**
 * Ajoute le jeton porteur à chaque requête, et une clé d'idempotence à chaque POST qui n'en a
 * pas : rejouer la même requête (double clic, reprise) ne produit alors qu'un seul effet.
 */
const contractHeaders: Middleware = {
  onRequest({ request }) {
    const token = session.token()
    if (token !== null) request.headers.set('Authorization', `Bearer ${token}`)
    if (request.method === 'POST' && !request.headers.has('Idempotency-Key')) {
      request.headers.set('Idempotency-Key', crypto.randomUUID())
    }
    return request
  },
  onResponse({ response }) {
    if (response.status === 401 && session.token() !== null) session.clear()
    return response
  },
}

/**
 * Client de l'API, typé par le schéma généré depuis le backend (make api-types).
 * `fetch` est résolu à chaque appel, et non à la création, pour rester remplaçable en test.
 */
export const api = createClient<paths>({
  baseUrl: window.location.origin,
  fetch: (request) => globalThis.fetch(request),
})
api.use(contractHeaders)
