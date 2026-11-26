import bellImage from '@/assets/cloche-relances-verre.webp'
import { Money } from '@/components/money'
import { PageTitle } from '@/components/page-title'
import { Reveal } from '@/components/reveal'
import { ErrorView, Loading } from '@/components/state-views'
import { fr } from '@/i18n/fr'

import { ReceivableRow } from './receivable-row'
import { useReceivables } from './use-receivables'

const t = fr.collection

/** Échéancier du recouvrement : ce qui est dû, ce qui est en retard, et la relance du jour. */
export function CollectionPage() {
  const board = useReceivables()
  if (board.isPending) return <Loading />
  if (board.isError)
    return <ErrorView message={fr.errors.generic} onRetry={() => void board.refetch()} />
  const b = board.data

  return (
    <div className="grid gap-5">
      <section className="relative overflow-hidden rounded-card bg-white px-6 pt-6 pb-7 shadow-card sm:px-8">
        <img
          src={bellImage}
          alt=""
          className="float pointer-events-none absolute -top-4 right-2 hidden w-[190px] drop-shadow-[var(--shadow-object)] md:block"
        />
        <PageTitle light={t.titleLight} bold={t.titleBold} />
        <p className="mt-3 max-w-[62ch] text-[15px] leading-relaxed text-ink-soft">{t.lead}</p>
      </section>

      <div className="grid gap-4 md:grid-cols-3">
        <Reveal index={0} className="grid">
          <div className="night flex min-h-[150px] flex-col justify-between rounded-card p-6 text-white shadow-card">
            <span className="label text-white/70">{t.outstanding}</span>
            <Money value={b.outstanding} className="text-[38px] tracking-[-0.03em]" />
            <span className="text-sm text-white/70">{t.invoices(b.items.length)}</span>
          </div>
        </Reveal>
        <Reveal index={1} className="grid">
          <div className="flex min-h-[150px] flex-col justify-between rounded-card bg-white p-6 shadow-card">
            <span className="label text-coral-ink">{t.overdue}</span>
            <Money value={b.overdue_amount} className="text-[38px] tracking-[-0.03em]" />
            <span className="text-sm text-ink-soft">{t.invoices(b.overdue_count)}</span>
          </div>
        </Reveal>
        <Reveal index={2} className="grid">
          <div className="flex min-h-[150px] flex-col justify-between rounded-card bg-white p-6 shadow-card">
            <span className="label text-amber-ink">{t.dueSoon}</span>
            <Money value={b.due_soon_amount} className="text-[38px] tracking-[-0.03em]" />
            <span className="text-sm text-ink-soft">{t.invoices(b.due_soon_count)}</span>
          </div>
        </Reveal>
      </div>

      {b.items.length === 0 ? (
        <p className="rounded-card bg-white p-8 text-center text-ink-soft shadow-card">{t.empty}</p>
      ) : (
        <ul className="grid gap-3">
          {b.items.map((item) => (
            <ReceivableRow key={item.invoice.id} item={item} steps={b.steps} />
          ))}
        </ul>
      )}
    </div>
  )
}
