import { MessageCircle, Mail, Smartphone } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import type { Invoice } from '@/api/types'
import { Button } from '@/components/button'
import { Money } from '@/components/money'
import { fr } from '@/i18n/fr'
import { formatAmount, formatDateTime } from '@/lib/format'
import { orderedChannels, readPreferences } from '@/lib/preferences'
import { problemMessage } from '@/lib/problem-message'

import { useCreditNote, useDispatchInvoice, useRecordPayment } from './queries'

const t = fr.invoice
const CHANNEL_ICONS = { whatsapp: MessageCircle, sms: Smartphone, email: Mail } as const
type Method = 'mobile_money' | 'especes' | 'virement'

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid content-start gap-4 rounded-card bg-white p-6 shadow-card">
      <h2 className="text-[22px]">{title}</h2>
      {children}
    </section>
  )
}

function Failure({ error }: { error: unknown }) {
  return error ? (
    <p role="alert" className="text-sm text-coral-ink">
      {problemMessage(error)}
    </p>
  ) : null
}

export function DispatchPanel({ invoice }: { invoice: Invoice }) {
  const dispatch = useDispatchInvoice(invoice.id)
  const sent = new Set(invoice.dispatches.map((d) => d.channel))
  const open = invoice.status === 'VALIDATED' || invoice.status === 'ISSUED'
  return (
    <Panel title={t.dispatch}>
      <div className="flex flex-wrap gap-2">
        {orderedChannels(readPreferences().channel).map((id) => {
          const Icon = CHANNEL_ICONS[id]
          return (
            <Button
              key={id}
              variant={sent.has(id) ? 'ghost' : 'ink'}
              disabled={!open || sent.has(id)}
              pending={dispatch.isPending && dispatch.variables === id}
              icon={<Icon className="size-4" aria-hidden="true" />}
              onClick={() => dispatch.mutate(id)}
            >
              {t.channels[id]}
            </Button>
          )
        })}
      </div>
      <Failure error={dispatch.error} />
      <ul className="grid gap-3">
        {invoice.dispatches.map((d) => (
          <li
            key={d.id}
            className="max-w-[420px] rounded-[18px] rounded-tl-md bg-whatsapp-wash px-4 py-3 text-[13.5px] leading-relaxed whitespace-pre-line text-whatsapp-ink"
          >
            {d.message}
            <span className="label mt-2 block text-[10.5px] opacity-75">
              {`${t.channels[d.channel] ?? d.channel} · ${fr.demo.simulated} · ${d.recipient} · ${formatDateTime(d.sent_at)}`}
            </span>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

export function PaymentsPanel({ invoice }: { invoice: Invoice }) {
  const record = useRecordPayment(invoice.id)
  const [pendingKey, setPendingKey] = useState(() => crypto.randomUUID())
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState<Method>('mobile_money')
  const open =
    (invoice.status === 'VALIDATED' || invoice.status === 'ISSUED') &&
    invoice.payment_status !== 'PAID'

  function submit(event: FormEvent) {
    event.preventDefault()
    const value = (amount || invoice.balance.amount_due).replace(/\s/g, '')
    // La même clé est renvoyée tant que le règlement n'est pas confirmé : un nouvel essai
    // après une coupure ne peut pas l'enregistrer deux fois.
    record.mutate(
      { amount: value, method, idempotencyKey: pendingKey },
      {
        onSuccess: () => {
          setAmount('')
          setPendingKey(crypto.randomUUID())
        },
      },
    )
  }

  return (
    <Panel title={t.payments}>
      {invoice.payments.length === 0 ? (
        <p className="text-sm text-ink-soft">{t.noPayment}</p>
      ) : (
        <ul className="grid gap-2">
          {invoice.payments.map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between gap-3 rounded-field bg-ice px-4 py-3"
            >
              <span className="grid">
                <span className="text-sm font-medium">{t.methods[p.method] ?? p.method}</span>
                <span className="font-mono text-[11px] text-ink-soft">{`${p.reference} · ${fr.demo.simulated}`}</span>
              </span>
              <Money value={p.amount} className="text-[15px]" />
            </li>
          ))}
        </ul>
      )}
      {open && (
        <form onSubmit={submit} className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
          <label className="sr-only" htmlFor="amount">
            {t.amount}
          </label>
          <input
            id="amount"
            inputMode="decimal"
            value={amount}
            onChange={(e) => {
              setAmount(e.target.value)
              setPendingKey(crypto.randomUUID())
            }}
            placeholder={formatAmount(invoice.balance.amount_due)}
            className="tabular min-w-0 rounded-full bg-ice px-4 py-3 text-sm outline-none focus-visible:shadow-[inset_0_0_0_2px_var(--color-sky)]"
          />
          <label className="sr-only" htmlFor="method">
            {t.method}
          </label>
          <select
            id="method"
            value={method}
            onChange={(e) => {
              setMethod(e.target.value as Method)
              setPendingKey(crypto.randomUUID())
            }}
            className="rounded-full bg-ice px-4 py-3 text-sm outline-none"
          >
            {Object.entries(t.methods).map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
          <Button type="submit" variant="primary" pending={record.isPending}>
            {t.record}
          </Button>
        </form>
      )}
      <Failure error={record.error} />
    </Panel>
  )
}

export function CreditPanel({ invoice, canCredit }: { invoice: Invoice; canCredit: boolean }) {
  const credit = useCreditNote(invoice.id)
  const [reason, setReason] = useState('')
  const open =
    canCredit &&
    (invoice.status === 'VALIDATED' || invoice.status === 'ISSUED') &&
    invoice.balance.credited_total === '0'
  return (
    <Panel title={t.creditNotes}>
      {invoice.credit_notes.length === 0 ? (
        <p className="text-sm text-ink-soft">{t.noCredit}</p>
      ) : (
        <ul className="grid gap-2">
          {invoice.credit_notes.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between gap-3 rounded-field bg-coral-wash px-4 py-3 text-coral-ink"
            >
              <span className="grid">
                <span className="tabular text-sm">{c.number ?? fr.status.DRAFT}</span>
                <span className="text-xs">{c.reason}</span>
              </span>
              <Money value={`-${c.totals.gross_total}`} className="text-[15px]" />
            </li>
          ))}
        </ul>
      )}
      {open && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (reason.trim().length >= 3) credit.mutate(reason.trim())
          }}
          className="grid gap-2 sm:grid-cols-[1fr_auto]"
        >
          <label className="sr-only" htmlFor="reason">
            {t.reason}
          </label>
          <input
            id="reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={t.reasonPlaceholder}
            className="min-w-0 rounded-full bg-ice px-4 py-3 text-sm outline-none focus-visible:shadow-[inset_0_0_0_2px_var(--color-sky)]"
          />
          <Button
            type="submit"
            variant="ghost"
            pending={credit.isPending}
            disabled={reason.trim().length < 3}
          >
            {t.creditFull}
          </Button>
        </form>
      )}
      <Failure error={credit.error} />
    </Panel>
  )
}
