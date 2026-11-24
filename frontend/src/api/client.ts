import createClient from 'openapi-fetch'

import type { paths } from './schema'

/**
 * Client de l'API, typé par le schéma généré depuis le backend (make api-types).
 * `fetch` est résolu à chaque appel, et non à la création, pour rester remplaçable en test.
 */
export const api = createClient<paths>({
  baseUrl: window.location.origin,
  fetch: (request) => globalThis.fetch(request),
})
