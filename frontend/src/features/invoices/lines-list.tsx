import type { InvoiceLine } from '@/api/types'
import { Money } from '@/components/money'
import { fr } from '@/i18n/fr'
import { formatAmount, formatRate } from '@/lib/format'

/** Lignes recalculées par le moteur. */
export function LinesList({ lines }: { lines: readonly InvoiceLine[] }) {
  return (
    <ul className="grid gap-2">
      {lines.map((line, index) => (
        <li
          key={index}
          className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 rounded-field bg-white px-4 py-3 shadow-[inset_0_0_0_1px_var(--color-line)]"
        >
          <span className="truncate text-[15px] font-medium">{line.label}</span>
          <Money value={line.line_net} className="text-right text-[15px]" />
          <span className="font-mono text-xs text-ink-soft">
            {formatAmount(line.quantity)} {line.unit ?? ''} × {formatAmount(line.unit_price_net)}
            {line.discount_rate !== '0' && ` · −${formatRate(line.discount_rate)}`}
          </span>
          <span className="text-right font-mono text-xs text-ink-soft">
            {fr.totals.vat(formatRate(line.vat_rate))}
          </span>
        </li>
      ))}
    </ul>
  )
}
