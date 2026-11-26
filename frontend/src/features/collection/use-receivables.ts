import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import { unwrap } from '@/api/problem'

const KEY = ['receivables'] as const

export function useReceivables() {
  return useQuery({
    queryKey: KEY,
    queryFn: async () => unwrap(await api.GET('/api/v1/receivables')),
  })
}

export function useSendReminder() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (invoiceId: string) =>
      unwrap(
        await api.POST('/api/v1/invoices/{invoice_id}/reminders', {
          params: { path: { invoice_id: invoiceId } },
        }),
      ),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: KEY })
      void client.invalidateQueries({ queryKey: ['audit'] })
    },
  })
}
