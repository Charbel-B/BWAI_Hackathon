import { useMutation } from '@tanstack/react-query'

import { api } from '@/api/client'
import { unwrap } from '@/api/problem'

export function useAsk() {
  return useMutation({
    mutationFn: async (vars: { question: string; invoiceId: string | null }) =>
      unwrap(
        await api.POST('/api/v1/assistant/ask', {
          body: vars.invoiceId
            ? { question: vars.question, invoice_id: vars.invoiceId }
            : { question: vars.question },
        }),
      ),
  })
}
