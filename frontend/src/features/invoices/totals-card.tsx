import type { Invoice } from '@/api/types'
import { Money } from '@/components/money'
import { fr } from '@/i18n/fr'
import { formatRate } from '@/lib/format'

const t = fr.totals

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between font-mono text-[13px] text-white/70">
      <span>{label}</span>
      <Money value={value} />
    </div>
  )
}

/** Totaux renvoyés par le moteur ; le solde n'apparaît qu'une fois la facture validée. */
export function TotalsCard({
  invoice,
  withBalance = false,
}: {
  invoice: Invoice
  withBalance?: boolean
}) {
  const { totals, balance } = invoice
  return (
    <div className="grid gap-2 rounded-[22px] bg-graphite p-5 text-white">
      {totals.global_discount_amount !== '0' && (
        <>
          <Row label={t.lines} value={totals.lines_net_total} />
          <Row label={t.discount} value={`-${totals.global_discount_amount}`} />
        </>
      )}
      <Row label={t.net} value={totals.net_total} />
      {totals.vat_breakdown.map((vat) => (
        <Row key={vat.rate} label={t.vat(formatRate(vat.rate))} value={vat.amount} />
      ))}
      <div className="mt-1.5 flex items-baseline justify-between border-t border-white/12 pt-3">
        <span className="label text-white/60">{`${t.gross} · ${t.currency}`}</span>
        <Money value={totals.gross_total} className="text-[30px] font-medium tracking-[-0.02em]" />
      </div>
      {withBalance && (
        <div className="mt-2 grid gap-2 border-t border-white/12 pt-3">
          {balance.credited_total !== '0' && (
            <Row label={t.credited} value={`-${balance.credited_total}`} />
          )}
          <Row label={t.paid} value={balance.paid_total} />
          <div className="flex items-baseline justify-between">
            <span className="label text-lime">{t.due}</span>
            <Money value={balance.amount_due} className="text-xl text-lime" />
          </div>
        </div>
      )}
      <span className="mt-1 text-[11px] text-white/45">{t.engine}</span>
    </div>
  )
}
