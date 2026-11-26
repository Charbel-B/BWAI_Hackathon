import { FileDown } from 'lucide-react'
import { Link } from 'react-router'

import type { Invoice } from '@/api/types'
import { paths } from '@/app/paths'
import { PaymentBadge, StatusBadge } from '@/components/status-badge'
import { useCurrentUser } from '@/features/auth/use-session'
import { fr } from '@/i18n/fr'
import { displayUser, formatDate } from '@/lib/format'

import { LinesList } from './lines-list'
import { CreditPanel, DispatchPanel, PaymentsPanel } from './settlement-panels'
import { TotalsCard } from './totals-card'
import { VerificationPanel } from './verification-panel'

const t = fr.invoice

/** Facture validée : immuable ; on l'émet, on suit ses règlements, on la corrige par avoir. */
export function IssuedInvoice({ invoice }: { invoice: Invoice }) {
  const user = useCurrentUser()
  const canCredit = user?.role === 'VALIDATOR' || user?.role === 'ADMIN'
  const live = invoice.status !== 'DISCARDED'
  return (
    <div className="grid gap-5">
      <header className="flex flex-wrap items-end justify-between gap-6 rounded-card bg-white px-6 py-6 shadow-card">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={invoice.status} />
            {live && <PaymentBadge status={invoice.payment_status} />}
          </div>
          <h1 className="tabular mt-4 text-[clamp(30px,4vw,52px)] font-normal tracking-[-0.03em]">
            {invoice.number ?? fr.status[invoice.status as keyof typeof fr.status]}
          </h1>
          <p className="mt-2 text-[15px] text-ink-soft">
            {invoice.customer_name}
            {invoice.reference && ` · ${t.reference} ${invoice.reference}`}
          </p>
        </div>
        <div className="grid justify-items-end gap-3">
          <Link
            to={paths.invoicePrint(invoice.id)}
            className="inline-flex items-center gap-2 rounded-full bg-night px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-sky-deep"
          >
            <FileDown className="size-4" aria-hidden="true" />
            {fr.print.download}
          </Link>
          <dl className="grid gap-1 text-right text-sm text-ink-soft">
            {invoice.validated_at && (
              <dd>
                {t.issuedOn(formatDate(invoice.validated_at))}
                {invoice.validated_by && ` ${t.validator(displayUser(invoice.validated_by))}`}
              </dd>
            )}
            {invoice.due_date && <dd>{t.due(formatDate(invoice.due_date))}</dd>}
            {invoice.config_sha256 && (
              <dd
                className="font-mono text-[11px]"
                title={invoice.config_sha256}
              >{`${t.configHash} · ${invoice.config_sha256.slice(0, 12)}`}</dd>
            )}
          </dl>
        </div>
      </header>

      <div className="grid items-start gap-5 lg:grid-cols-[1.1fr_1fr]">
        <div className="grid gap-5">
          <section className="grid gap-3 rounded-card bg-white p-6 shadow-card">
            <h2 className="text-[22px]">{t.lines}</h2>
            <LinesList lines={invoice.lines} />
          </section>
          {live && <DispatchPanel invoice={invoice} />}
        </div>
        <div className="grid gap-5">
          <TotalsCard invoice={invoice} withBalance={live} />
          <VerificationPanel invoice={invoice} />
          {live && <PaymentsPanel invoice={invoice} />}
          {live && <CreditPanel invoice={invoice} canCredit={canCredit} />}
        </div>
      </div>
    </div>
  )
}
