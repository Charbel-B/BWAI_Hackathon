import type { components } from '@/api/schema'
import type { Invoice } from '@/api/types'
import { paths } from '@/app/paths'
import { Money } from '@/components/money'
import { QrCode } from '@/components/qr-code'
import { fr } from '@/i18n/fr'
import { formatAmount, formatDate, formatRate } from '@/lib/format'

type Issuer = components['schemas']['IssuerOut']
const t = fr.print

function Party({ title, lines }: { title: string; lines: (string | null | undefined)[] }) {
  return (
    <div>
      <span className="label text-ink-soft">{title}</span>
      {lines.filter(Boolean).map((line, i) => (
        <p
          key={i}
          className={i === 0 ? 'mt-1 text-[15px] font-semibold' : 'text-[12.5px] text-ink-soft'}
        >
          {line}
        </p>
      ))}
    </div>
  )
}

function TotalRow({
  label,
  value,
  strong = false,
}: {
  label: string
  value: string
  strong?: boolean
}) {
  return (
    <div
      className={`flex justify-between gap-6 ${strong ? 'border-t border-line pt-2 text-[17px] font-semibold' : 'text-[12.5px] text-ink-soft'}`}
    >
      <span>{label}</span>
      <Money value={value} className={strong ? 'text-ink' : ''} />
    </div>
  )
}

/** La facture sur une feuille A4 : ce que le client reçoit. Aucun montant n'est calculé ici. */
export function PrintSheet({ invoice, issuer }: { invoice: Invoice; issuer: Issuer }) {
  const totals = invoice.totals
  const draft = invoice.status === 'DRAFT'
  const verifyUrl = invoice.verification_code
    ? `${window.location.origin}${paths.verify(invoice.id, invoice.verification_code)}`
    : null

  return (
    <article className="sheet relative mx-auto flex min-h-[297mm] w-[210mm] flex-col overflow-hidden bg-white text-ink shadow-card">
      {draft && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 -rotate-[24deg] text-[110px] font-semibold tracking-[0.1em] text-coral/15"
        >
          {t.draft}
        </span>
      )}
      <header className="sky flex items-start justify-between px-[14mm] pt-[12mm] pb-[10mm] text-white">
        <div>
          <p className="text-[22px] font-semibold tracking-[-0.02em]">{issuer.name}</p>
          <p className="text-[12px] text-white/80">{issuer.address}</p>
        </div>
        <div className="text-right">
          <span className="label text-white/80">{t.title}</span>
          <p className="tabular mt-1 text-[26px] tracking-[-0.02em]">{invoice.number ?? t.draft}</p>
        </div>
      </header>

      <section className="grid grid-cols-2 gap-[10mm] px-[14mm] pt-[9mm]">
        <Party
          title={t.issuer}
          lines={[
            issuer.name,
            issuer.address,
            `${t.ifu} ${issuer.tax_id}`,
            `${issuer.phone} · ${issuer.email}`,
          ]}
        />
        <Party
          title={t.billedTo}
          lines={[
            invoice.customer_name,
            invoice.customer_id ? `${fr.dashboard.columns.customer} ${invoice.customer_id}` : null,
          ]}
        />
      </section>

      <dl className="mx-[14mm] mt-[8mm] grid grid-cols-3 gap-4 rounded-2xl bg-ice px-5 py-3">
        {[
          [t.date, formatDate(invoice.issue_date)],
          [t.due, formatDate(invoice.due_date)],
          [t.reference, invoice.reference ?? '—'],
        ].map(([label, value]) => (
          <div key={label}>
            <dt className="label text-[10px] text-ink-soft">{label}</dt>
            <dd className="mt-0.5 text-[13px] font-medium">{value}</dd>
          </div>
        ))}
      </dl>

      <table className="mx-[14mm] mt-[8mm] w-[calc(100%-28mm)] text-[12.5px]">
        <thead>
          <tr className="label border-b border-line text-[10px] text-ink-soft">
            <th className="py-2 text-left font-normal">{t.columns.label}</th>
            <th className="py-2 text-right font-normal">{t.columns.qty}</th>
            <th className="py-2 text-right font-normal">{t.columns.price}</th>
            <th className="py-2 text-right font-normal">{t.columns.discount}</th>
            <th className="py-2 text-right font-normal">{t.columns.vat}</th>
            <th className="py-2 text-right font-normal">{t.columns.net}</th>
          </tr>
        </thead>
        <tbody>
          {invoice.lines.map((line, i) => (
            <tr key={i} className="border-b border-line align-top">
              <td className="py-2.5 pr-3 font-medium">{line.label}</td>
              <td className="tabular py-2.5 text-right whitespace-nowrap">{`${formatAmount(line.quantity)} ${line.unit ?? ''}`}</td>
              <td className="tabular py-2.5 text-right">{formatAmount(line.unit_price_net)}</td>
              <td className="tabular py-2.5 text-right">
                {line.discount_rate === '0' ? '—' : formatRate(line.discount_rate)}
              </td>
              <td className="tabular py-2.5 text-right">{formatRate(line.vat_rate)}</td>
              <td className="tabular py-2.5 text-right font-medium">
                {formatAmount(line.line_net)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <section className="mx-[14mm] mt-[6mm] ml-auto grid w-[78mm] gap-1.5">
        {totals.global_discount_amount !== '0' && (
          <>
            <TotalRow label={fr.totals.lines} value={totals.lines_net_total} />
            <TotalRow label={fr.totals.discount} value={`-${totals.global_discount_amount}`} />
          </>
        )}
        <TotalRow label={fr.totals.net} value={totals.net_total} />
        {totals.vat_breakdown.map((v) => (
          <TotalRow key={v.rate} label={fr.totals.vat(formatRate(v.rate))} value={v.amount} />
        ))}
        <TotalRow
          label={`${fr.totals.gross} (${fr.totals.currency})`}
          value={totals.gross_total}
          strong
        />
        {invoice.balance.paid_total !== '0' && (
          <TotalRow label={fr.totals.paid} value={invoice.balance.paid_total} />
        )}
        {invoice.balance.paid_total !== '0' && (
          <TotalRow label={fr.totals.due} value={invoice.balance.amount_due} />
        )}
      </section>

      <footer className="mt-auto grid grid-cols-[30mm_1fr] items-center gap-[7mm] border-t border-line px-[14mm] py-[9mm]">
        {verifyUrl ? <QrCode value={verifyUrl} label={t.verify} className="w-[30mm]" /> : <span />}
        <div className="grid gap-1.5 text-[11px] leading-relaxed text-ink-soft">
          {verifyUrl && (
            <>
              <b className="text-[12.5px] text-ink">{t.verify}</b>
              <p>{t.verifyText}</p>
              <p className="font-mono">{`${t.code} : ${invoice.verification_code}`}</p>
            </>
          )}
          <p>{t.terms}</p>
          <p className="font-medium text-ink">{t.legal}</p>
          <p>{t.madeWith(fr.brand.name)}</p>
        </div>
      </footer>
    </article>
  )
}
