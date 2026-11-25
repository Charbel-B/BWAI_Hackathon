import { useQuery } from '@tanstack/react-query'
import { ChevronRight, FilePlus2, ShieldCheck, ShieldAlert } from 'lucide-react'
import { Link, useNavigate } from 'react-router'

import { api } from '@/api/client'
import uploadImage from '@/assets/depot-pieces-verre.webp'
import { unwrap } from '@/api/problem'
import type { InvoiceSummary } from '@/api/types'
import { Button } from '@/components/button'
import { Money } from '@/components/money'
import { PageTitle } from '@/components/page-title'
import { ErrorView, Loading } from '@/components/state-views'
import { PaymentBadge, StatusBadge } from '@/components/status-badge'
import { useCurrentUser } from '@/features/auth/use-session'
import { paths } from '@/app/paths'
import { fr } from '@/i18n/fr'
import { formatDateTime } from '@/lib/format'

import { useInvoices } from './queries'

const t = fr.dashboard

function count(list: InvoiceSummary[], test: (i: InvoiceSummary) => boolean): number {
  return list.filter(test).length
}

function AuditCard() {
  const user = useCurrentUser()
  const allowed = user?.role !== 'OPERATOR'
  const verify = useQuery({
    queryKey: ['audit', 'verify'],
    enabled: allowed,
    queryFn: async () => unwrap(await api.GET('/api/v1/audit-log/verify')),
  })
  const intact = verify.data?.intact ?? true
  return (
    <Link
      to={paths.audit}
      className="group flex min-h-[170px] flex-col justify-between rounded-card bg-graphite p-6 text-white transition-transform duration-300 ease-out hover:-translate-y-0.5"
    >
      <span className="label text-white/60">{t.audit}</span>
      <span className="flex items-center gap-3">
        <span
          className={`grid size-8 place-items-center rounded-full ${intact ? 'bg-lime text-lime-ink' : 'bg-coral text-white'}`}
        >
          {intact ? (
            <ShieldCheck className="size-4" aria-hidden="true" />
          ) : (
            <ShieldAlert className="size-4" aria-hidden="true" />
          )}
        </span>
        <span className="text-[15px]">
          {verify.data
            ? verify.data.intact
              ? fr.audit.intact(verify.data.entries)
              : fr.audit.broken(verify.data.first_broken_seq ?? 0)
            : fr.audit.verify}
        </span>
        <ChevronRight
          className="ml-auto size-4 opacity-50 transition-transform group-hover:translate-x-0.5"
          aria-hidden="true"
        />
      </span>
    </Link>
  )
}

function InvoiceRow({ invoice }: { invoice: InvoiceSummary }) {
  const navigate = useNavigate()
  const open = () => void navigate(paths.invoice(invoice.id))
  return (
    <tr
      onClick={open}
      className="cursor-pointer border-t border-line transition-colors duration-150 first:border-t-0 hover:bg-sky-wash/60"
    >
      <td className="py-4 pr-4 pl-6">
        <Link
          to={paths.invoice(invoice.id)}
          className="tabular text-sm text-ink"
          onClick={(e) => e.stopPropagation()}
        >
          {invoice.number ?? <span className="text-ink-soft">{t.draftNumber}</span>}
        </Link>
      </td>
      <td className="max-w-[260px] truncate py-4 pr-4 text-[15px] font-medium">
        {invoice.customer_name ?? (
          <span className="font-normal text-coral-ink">{t.unknownCustomer}</span>
        )}
      </td>
      <td className="py-4 pr-4">
        <span className="flex items-center gap-2">
          <StatusBadge status={invoice.status} />
          {invoice.blocking_count > 0 && (
            <span className="rounded-full bg-coral-wash px-2 py-1 font-mono text-[11px] text-coral-ink">
              {t.blocking(invoice.blocking_count)}
            </span>
          )}
        </span>
      </td>
      <td className="py-4 pr-4">
        {invoice.status !== 'DRAFT' && invoice.status !== 'DISCARDED' && (
          <PaymentBadge status={invoice.payment_status} />
        )}
      </td>
      <td className="py-4 pr-4 text-right text-[15px]">
        <Money value={invoice.gross_total} />
      </td>
      <td className="hidden py-4 pr-6 text-right text-sm text-ink-soft md:table-cell">
        {formatDateTime(invoice.created_at)}
      </td>
    </tr>
  )
}

/** Tableau de bord : ce qui attend une action, puis toutes les factures. */
export function DashboardPage() {
  const invoices = useInvoices()
  const navigate = useNavigate()

  if (invoices.isPending) return <Loading />
  if (invoices.isError)
    return <ErrorView message={fr.errors.generic} onRetry={() => void invoices.refetch()} />

  const list = invoices.data
  const drafts = count(list, (i) => i.status === 'DRAFT')
  const live = count(list, (i) => i.status === 'VALIDATED' || i.status === 'ISSUED')
  const paid = count(
    list,
    (i) => i.payment_status === 'PAID' && i.status !== 'DRAFT' && i.status !== 'DISCARDED',
  )

  return (
    <div className="grid gap-8">
      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr_1fr] lg:grid-rows-[auto_auto]">
        <div className="sky flex min-h-[200px] flex-col justify-between gap-6 rounded-card p-7 text-white shadow-card lg:row-span-2">
          <span className="label text-white/75">{t.toReview}</span>
          <div>
            <div className="tabular text-[64px] leading-none tracking-[-0.03em]">{drafts}</div>
            <p className="mt-2 max-w-[28ch] text-[15px] text-white/90">
              {t.toReviewDetail(drafts)}
            </p>
          </div>
          <Button
            variant="primary"
            arrow
            className="self-start"
            icon={<FilePlus2 className="size-4" aria-hidden="true" />}
            onClick={() => void navigate(paths.import)}
          >
            {t.importCta}
          </Button>
        </div>
        <div className="flex min-h-[170px] flex-col justify-between rounded-card bg-white p-6 shadow-card">
          <span className="label text-ink-soft">{fr.status.VALIDATED}</span>
          <div className="tabular text-[44px] leading-none tracking-[-0.03em]">{live}</div>
          <span className="text-sm text-ink-soft">{t.validated(live)}</span>
        </div>
        <div className="flex min-h-[170px] flex-col justify-between rounded-card bg-lime p-6 text-lime-ink">
          <span className="label">{t.extraction}</span>
          <div>
            <div className="tabular text-[44px] leading-none tracking-[-0.03em]">
              {t.extractionValue}
            </div>
            <span className="mt-2 block text-[13px]">{t.extractionDetail}</span>
          </div>
        </div>
        <div className="flex min-h-[170px] flex-col justify-between rounded-card bg-mist p-6">
          <span className="label text-ink-soft">{fr.payment.PAID}</span>
          <div className="tabular text-[44px] leading-none tracking-[-0.03em]">{paid}</div>
          <span className="self-start">
            <PaymentBadge status="PAID" />
          </span>
        </div>
        <AuditCard />
      </div>

      <section className="overflow-hidden rounded-card bg-white shadow-card">
        <div className="px-6 pt-6 pb-4">
          <PageTitle light={t.titleLight} bold={t.titleBold} />
        </div>
        {list.length === 0 ? (
          <div className="flex flex-col items-center gap-3 px-6 pt-2 pb-12 text-center">
            <img
              src={uploadImage}
              alt=""
              className="w-[140px] drop-shadow-[var(--shadow-object)]"
            />
            <p className="max-w-[40ch] text-ink-soft">{t.empty}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left">
              <thead>
                <tr className="label text-ink-soft">
                  <th scope="col" className="pt-2 pr-4 pb-3 pl-6 font-normal">
                    {t.columns.number}
                  </th>
                  <th scope="col" className="pr-4 pb-3 font-normal">
                    {t.columns.customer}
                  </th>
                  <th scope="col" className="pr-4 pb-3 font-normal">
                    {t.columns.status}
                  </th>
                  <th scope="col" className="pr-4 pb-3 font-normal">
                    {t.columns.payment}
                  </th>
                  <th scope="col" className="pr-4 pb-3 text-right font-normal">
                    {t.columns.total}
                  </th>
                  <th scope="col" className="hidden pr-6 pb-3 text-right font-normal md:table-cell">
                    {t.columns.date}
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.map((invoice) => (
                  <InvoiceRow key={invoice.id} invoice={invoice} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
