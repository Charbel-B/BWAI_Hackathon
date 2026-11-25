import type { components } from './schema'

type Schemas = components['schemas']

export type Invoice = Schemas['InvoiceOut']
export type InvoiceSummary = Schemas['InvoiceSummaryOut']
export type InvoiceLine = Schemas['LineOut']
export type Anomaly = Schemas['AnomalyOut']
export type SourceDocument = Schemas['DocumentOut']
export type ExtractedField = Schemas['DocumentOut']['fields'][number]
export type CreditNote = Schemas['CreditNoteOut']
export type AuditEntry = Schemas['AuditOut']
export type User = Schemas['UserOut']
export type Health = Schemas['HealthResponse']
