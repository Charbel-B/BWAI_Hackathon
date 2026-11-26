import { BellRing, Check, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import type { components } from '@/api/schema'
import { paths } from '@/app/paths'
import { Button } from '@/components/button'
import { Money } from '@/components/money'
import { fr } from '@/i18n/fr'
import { formatDate, formatDateTime } from '@/lib/format'
import { problemMessage } from '@/lib/problem-message'

import { useSendReminder } from './use-receivables'

type Receivable = components['schemas']['ReceivableOut']
type Step = components['schemas']['StepOut']

const t = fr.collection
const STANDING_TONE: Record<string, string> = {
  OVERDUE: 'bg-coral-wash text-coral-ink',
  DUE_SOON: 'bg-amber-wash text-amber-ink',
  NOT_DUE: 'bg-sky-wash text-sky-deep',
  NO_DUE_DATE: 'bg-mist text-ink-soft',
}

/** Étapes de relance : envoyée, à envoyer aujourd'hui, ou à venir. */
function StepTrack({ steps, item }: { steps: readonly Step[]; item: Receivable }) {
  const sent = new Set(item.reminders.map((r) => r.step))
  return (
    <ol className="flex flex-wrap items-center gap-1.5">
      {steps.map((step, index) => {
        const done = sent.has(step.code)
        const next = item.next_step?.code === step.code
        const tone = done
          ? 'bg-lime text-lime-ink'
          : next
            ? 'bg-sky text-white shadow-[0_0_0_4px_var(--color-sky-wash)]'
            : 'bg-mist text-ink-soft'
        return (
          <li key={step.code} className="flex items-center gap-1.5">
            {index > 0 && (
              <span
                aria-hidden="true"
                className={`h-px w-4 ${done ? 'bg-lime-ink/40' : 'bg-line'}`}
              />
            )}
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-mono text-[11px] transition-colors duration-300 ${tone}`}
            >
              {done && <Check className="size-3" strokeWidth={3} aria-hidden="true" />}
              {step.label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

/** Une facture de l'échéancier : situation, étapes, relance du jour et historique. */
export function ReceivableRow({ item, steps }: { item: Receivable; steps: readonly Step[] }) {
  const send = useSendReminder()
  const [open, setOpen] = useState(false)
  const inv = item.invoice
  const standing = t.standing[item.standing]?.(item.days_late) ?? item.standing

  return (
    <li className="lift rounded-[22px] bg-white p-5 shadow-card">
      <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr_auto] lg:items-center">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-2.5 py-1 font-mono text-[11px] ${STANDING_TONE[item.standing] ?? STANDING_TONE['NO_DUE_DATE']}`}
            >
              {standing}
            </span>
            <Link
              to={paths.invoice(inv.id)}
              className="tabular text-sm text-ink-soft hover:text-ink"
            >
              {inv.number}
            </Link>
          </div>
          <p className="mt-2 truncate text-[17px] font-semibold">{inv.customer_name}</p>
          <p className="text-sm text-ink-soft">
            {item.due_date ? t.due(formatDate(item.due_date)) : t.noDue}
          </p>
        </div>
        <div className="grid gap-2">
          <Money value={item.amount_due} className="text-[26px] tracking-[-0.02em]" />
          <StepTrack steps={steps} item={item} />
        </div>
        <div className="grid justify-items-start gap-2 lg:justify-items-end">
          <Button
            variant={item.next_step ? 'primary' : 'ghost'}
            disabled={!item.next_step}
            pending={send.isPending}
            icon={<BellRing className="size-4" aria-hidden="true" />}
            onClick={() => send.mutate(inv.id, { onSuccess: () => setOpen(true) })}
          >
            {item.next_step ? t.send(item.next_step.label) : t.nothingToSend}
          </Button>
          {item.reminders.length > 0 && (
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              className="inline-flex items-center gap-1 text-xs text-ink-soft hover:text-ink"
            >
              {`${t.history} (${item.reminders.length})`}
              <ChevronDown
                className={`size-3.5 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
                aria-hidden="true"
              />
            </button>
          )}
        </div>
      </div>
      {send.isError && (
        <p role="alert" className="mt-3 text-sm text-coral-ink">
          {problemMessage(send.error)}
        </p>
      )}
      {open && (
        <ul className="enter mt-4 grid gap-2">
          {item.reminders.map((r) => (
            <li
              key={r.id}
              className="max-w-[560px] rounded-[18px] rounded-tl-md bg-whatsapp-wash px-4 py-3 text-[13.5px] leading-relaxed text-whatsapp-ink"
            >
              {r.message}
              <span className="label mt-2 block text-[10px] opacity-75">
                {t.sentBy(fr.invoice.channels[r.channel] ?? r.channel, formatDateTime(r.sent_at))}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}
