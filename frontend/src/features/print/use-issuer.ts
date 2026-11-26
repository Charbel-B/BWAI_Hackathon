import { useQuery } from '@tanstack/react-query'

import { api } from '@/api/client'
import { unwrap } from '@/api/problem'

export function useIssuer() {
  return useQuery({
    queryKey: ['issuer'],
    queryFn: async () => unwrap(await api.GET('/api/v1/issuer')),
    staleTime: Infinity,
  })
}
