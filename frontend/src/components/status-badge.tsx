import { fr } from '@/i18n/fr'

const LIFECYCLE: Record<string, string> = {
  DRAFT: 'bg-mist text-ink-soft',
  VALIDATED: 'bg-sky-wash text-sky-deep',
  ISSUED: 'bg-ink text-white',
  DISCARDED: 'bg-mist text-ink-soft line-through',
  CANCELLED: 'bg-coral-wash text-coral-ink',
}

const PAYMENT: Record<string, string> = {
  UNPAID: 'bg-white text-ink-soft shadow-[inset_0_0_0_1px_var(--color-line)]',
  PARTIALLY_PAID: 'bg-amber-wash text-amber-ink',
  PAID: 'bg-lime text-lime-ink',
}

function Pill({ tone, children }: { tone: string; children: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[11px] tracking-[0.04em] whitespace-nowrap ${tone}`}
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-current opacity-70" />
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const label = fr.status[status as keyof typeof fr.status] ?? status
  return <Pill tone={LIFECYCLE[status] ?? LIFECYCLE['DRAFT']!}>{label}</Pill>
}

export function PaymentBadge({ status }: { status: string }) {
  const label = fr.payment[status as keyof typeof fr.payment] ?? status
  return <Pill tone={PAYMENT[status] ?? PAYMENT['UNPAID']!}>{label}</Pill>
}
