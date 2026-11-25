import { CircleAlert, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'

import type { Invoice } from '@/api/types'
import { Button } from '@/components/button'
import { ErrorView, Loading } from '@/components/state-views'
import { StatusBadge } from '@/components/status-badge'
import { useCurrentUser } from '@/features/auth/use-session'
import { LinesList } from '@/features/invoices/lines-list'
import {
  useDiscardInvoice,
  useResolveAnomaly,
  useReviewField,
  useSourceDocument,
  useValidateInvoice,
} from '@/features/invoices/queries'
import { TotalsCard } from '@/features/invoices/totals-card'
import { fr } from '@/i18n/fr'
import { problemMessage } from '@/lib/problem-message'

import { AnomaliesPanel } from './anomalies-panel'
import { FieldCard } from './field-card'
import { type FieldState, fieldState, sortFields } from './field-state'
import { SourceView } from './source-view'

const t = fr.review

function Section({
  title,
  children,
  aside,
}: {
  title: string
  children: React.ReactNode
  aside?: React.ReactNode
}) {
  return (
    <section className="grid gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-[22px]">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

/** Revue d'un brouillon : la pièce à gauche, ses champs à droite, reliés au survol. */
export function ReviewPage({ invoice }: { invoice: Invoice }) {
  const user = useCurrentUser()
  const document = useSourceDocument(invoice.source_document_id)
  const [active, setActive] = useState<string | null>(null)
  const review = useReviewField(invoice.id, invoice.source_document_id)
  const resolve = useResolveAnomaly(invoice)
  const validate = useValidateInvoice(invoice)
  const discard = useDiscardInvoice(invoice)

  const fields = useMemo(() => sortFields(document.data?.fields ?? []), [document.data])
  const states = useMemo(
    () =>
      new Map<string, FieldState>(fields.map((f) => [f.name, fieldState(f, invoice.anomalies)])),
    [fields, invoice.anomalies],
  )

  if (document.isPending) return <Loading />
  if (document.isError)
    return <ErrorView message={fr.errors.generic} onRetry={() => void document.refetch()} />

  const isValidator = user?.role === 'VALIDATOR' || user?.role === 'ADMIN'
  const isAuthor = user?.id === invoice.created_by
  const blocking = invoice.blocking_count
  const error = [review, resolve, validate, discard].find((m) => m.isError)?.error
  const validateLabel = !isValidator
    ? t.validateNeedsValidator
    : blocking > 0
      ? t.validateBlocked(blocking)
      : t.validate

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4 rounded-card bg-white px-6 py-5 shadow-card">
        <div>
          <div className="flex items-center gap-3">
            <StatusBadge status={invoice.status} />
            <span className="label text-ink-soft">{t.extractor(document.data.extractor)}</span>
          </div>
          <h1 className="mt-3 text-[clamp(28px,3.4vw,44px)]">
            {invoice.customer_name ?? fr.dashboard.unknownCustomer}{' '}
            <b className="font-semibold">{invoice.reference ?? ''}</b>
          </h1>
        </div>
        <Button
          variant="quiet"
          icon={<Trash2 className="size-4" aria-hidden="true" />}
          pending={discard.isPending}
          onClick={() => discard.mutate()}
        >
          {t.discard}
        </Button>
      </div>

      {error !== undefined && (
        <p
          role="alert"
          className="flex items-center gap-2.5 rounded-field bg-coral-wash px-4 py-3 text-sm text-coral-ink"
        >
          <CircleAlert className="size-4 shrink-0" aria-hidden="true" />
          {problemMessage(error)}
        </p>
      )}

      <div className="grid items-start gap-5 lg:grid-cols-[1.05fr_1fr]">
        <div className="lg:sticky lg:top-6">
          <SourceView
            text={document.data.text ?? ''}
            filename={document.data.filename}
            fields={fields}
            states={states}
            active={active}
            onHover={setActive}
          />
        </div>

        <div className="grid gap-7">
          <Section title={t.fields}>
            <ul className="grid gap-2.5">
              {fields.map((field) => (
                <FieldCard
                  key={`${field.name}-${field.review.state}-${field.effective_value ?? ''}`}
                  field={field}
                  state={states.get(field.name) ?? 'sure'}
                  active={active === field.name}
                  editable
                  pending={review.isPending}
                  onHover={setActive}
                  onConfirm={() => review.mutate({ name: field.name })}
                  onCorrect={(value) => review.mutate({ name: field.name, value })}
                />
              ))}
            </ul>
          </Section>

          <Section title={t.anomalies}>
            <AnomaliesPanel
              anomalies={invoice.anomalies}
              canResolve
              pending={resolve.isPending}
              onResolve={(anomalyId, justification) => resolve.mutate({ anomalyId, justification })}
            />
          </Section>

          {invoice.lines.length > 0 && (
            <Section title={t.lines}>
              <LinesList lines={invoice.lines} />
            </Section>
          )}

          <TotalsCard invoice={invoice} />

          <div className="grid gap-2">
            <Button
              variant="primary"
              arrow={isValidator && blocking === 0 && !isAuthor}
              disabled={!isValidator || blocking > 0 || isAuthor}
              pending={validate.isPending}
              onClick={() => validate.mutate()}
              className="w-full py-3.5 text-[15px]"
            >
              {validateLabel}
            </Button>
            {isValidator && isAuthor && (
              <p className="text-center text-xs text-ink-soft">{t.separation}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
