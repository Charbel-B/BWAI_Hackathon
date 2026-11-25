import { QueryClient } from '@tanstack/react-query'

import { ApiProblem } from '@/api/problem'

/** Une erreur métier (4xx) ne se corrige pas en réessayant : seules les pannes sont retentées. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => !(error instanceof ApiProblem && error.status < 500) && count < 2,
      refetchOnWindowFocus: false,
    },
  },
})
