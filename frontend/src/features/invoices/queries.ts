import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import { unwrap } from '@/api/problem'
import type { Invoice } from '@/api/types'

export const keys = {
  invoices: ['invoices'] as const,
  invoice: (id: string) => ['invoice', id] as const,
  document: (id: string) => ['document', id] as const,
  audit: (entityId?: string) => ['audit', entityId ?? 'all'] as const,
}

const path = (invoiceId: string) => ({ path: { invoice_id: invoiceId } })
const ifMatch = (version: number) => ({ header: { 'if-match': String(version) } })

export function useInvoices() {
  return useQuery({
    queryKey: keys.invoices,
    queryFn: async () => unwrap(await api.GET('/api/v1/invoices')),
  })
}

export function useInvoice(invoiceId: string) {
  return useQuery({
    queryKey: keys.invoice(invoiceId),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/invoices/{invoice_id}', { params: path(invoiceId) })),
  })
}

export function useSourceDocument(documentId: string | undefined) {
  return useQuery({
    queryKey: keys.document(documentId ?? ''),
    enabled: documentId !== undefined,
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/source-documents/{document_id}', {
          params: { path: { document_id: documentId ?? '' } },
        }),
      ),
  })
}

/** Après chaque action, la facture renvoyée par le serveur remplace celle du cache. */
function useInvoiceMutation<V>(invoiceId: string, run: (vars: V) => Promise<Invoice>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: run,
    onSuccess: (invoice) => {
      client.setQueryData(keys.invoice(invoiceId), invoice)
      void client.invalidateQueries({ queryKey: keys.invoices })
      void client.invalidateQueries({ queryKey: ['audit'] })
    },
    onError: () => void client.invalidateQueries({ queryKey: keys.invoice(invoiceId) }),
  })
}

export function useReviewField(invoiceId: string, documentId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (vars: { name: string; value?: string }) =>
      unwrap(
        await api.POST('/api/v1/source-documents/{document_id}/fields/{name}/review', {
          params: { path: { document_id: documentId, name: vars.name } },
          body:
            vars.value === undefined
              ? { action: 'confirm' }
              : { action: 'correct', value: vars.value },
        }),
      ),
    onSuccess: (document) => {
      client.setQueryData(keys.document(documentId), document)
      void client.invalidateQueries({ queryKey: keys.invoice(invoiceId) })
      void client.invalidateQueries({ queryKey: keys.invoices })
    },
  })
}

export function useResolveAnomaly(invoice: Invoice) {
  return useInvoiceMutation(
    invoice.id,
    async (vars: { anomalyId: string; justification: string }) =>
      unwrap(
        await api.POST('/api/v1/invoices/{invoice_id}/anomalies/{anomaly_id}/resolve', {
          params: {
            path: { invoice_id: invoice.id, anomaly_id: vars.anomalyId },
            ...ifMatch(invoice.version),
          },
          body: { justification: vars.justification },
        }),
      ),
  )
}

export function useValidateInvoice(invoice: Invoice) {
  return useInvoiceMutation(invoice.id, async () =>
    unwrap(
      await api.POST('/api/v1/invoices/{invoice_id}/validate', {
        params: { ...path(invoice.id), ...ifMatch(invoice.version) },
      }),
    ),
  )
}

export function useDiscardInvoice(invoice: Invoice) {
  return useInvoiceMutation(invoice.id, async () =>
    unwrap(
      await api.POST('/api/v1/invoices/{invoice_id}/discard', {
        params: { ...path(invoice.id), ...ifMatch(invoice.version) },
      }),
    ),
  )
}

export function useDispatchInvoice(invoiceId: string) {
  return useInvoiceMutation(invoiceId, async (channel: string) =>
    unwrap(
      await api.POST('/api/v1/invoices/{invoice_id}/dispatch', {
        params: path(invoiceId),
        body: { channel },
      }),
    ),
  )
}

export function useRecordPayment(invoiceId: string) {
  return useInvoiceMutation(
    invoiceId,
    async (vars: { amount: string; method: 'mobile_money' | 'especes' | 'virement' }) =>
      unwrap(
        await api.POST('/api/v1/invoices/{invoice_id}/payments', {
          params: path(invoiceId),
          body: vars,
        }),
      ),
  )
}

export function useCreditNote(invoiceId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (reason: string) => {
      const note = unwrap(
        await api.POST('/api/v1/invoices/{invoice_id}/credit-notes', {
          params: path(invoiceId),
          body: { reason },
        }),
      )
      return unwrap(
        await api.POST('/api/v1/credit-notes/{credit_note_id}/validate', {
          params: { path: { credit_note_id: note.id }, ...ifMatch(note.version) },
        }),
      )
    },
    onSettled: () => {
      void client.invalidateQueries({ queryKey: keys.invoice(invoiceId) })
      void client.invalidateQueries({ queryKey: keys.invoices })
    },
  })
}
