import { useMutation, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import { unwrap } from '@/api/problem'
import { keys } from '@/features/invoices/queries'

/** Envoie la pièce en multipart ; le backend l'extrait et crée le brouillon d'un seul geste. */
export function useImportDocument() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) =>
      unwrap(
        await api.POST('/api/v1/source-documents', {
          body: { file: file as unknown as string },
          bodySerializer: () => {
            const form = new FormData()
            form.append('file', file)
            return form
          },
        }),
      ),
    onSuccess: (result) => {
      client.setQueryData(keys.invoice(result.invoice.id), result.invoice)
      client.setQueryData(keys.document(result.document.id), result.document)
      void client.invalidateQueries({ queryKey: keys.invoices })
    },
  })
}
