import { useMutation } from '@tanstack/react-query'

import { api } from '@/api/client'
import { unwrap } from '@/api/problem'

import { session } from './session'

export function useLogin() {
  return useMutation({
    mutationFn: async (credentials: { username: string; password: string }) =>
      unwrap(await api.POST('/api/v1/auth/login', { body: credentials })),
    onSuccess: (data) => session.open(data.access_token, data.user),
  })
}
