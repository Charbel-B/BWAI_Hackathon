import { CircleAlert, CircleCheck, PencilLine, TriangleAlert } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import type { Anomaly } from '@/api/types'
import { fr } from '@/i18n/fr'
import { displayUser } from '@/lib/format'

const t = fr.review

function ResolveForm({
  onResolve,
  pending,
}: {
  onResolve: (justification: string) => void
  pending: boolean
}) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  if (!open)
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-2 text-xs font-medium underline underline-offset-4"
      >
        {t.resolve}
      </button>
    )
  function submit(event: FormEvent) {
    event.preventDefault()
    if (text.trim().length >= 3) onResolve(text.trim())
  }
  return (
    <form onSubmit={submit} className="mt-2 flex gap-2">
      <label className="sr-only" htmlFor="justification">
        {t.justification}
      </label>
      <input
        id="justification"
        autoFocus
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t.justificationPlaceholder}
        className="min-w-0 flex-1 rounded-full bg-white px-4 py-1.5 text-xs text-ink outline-none"
      />
      <button
        type="submit"
        disabled={pending || text.trim().length < 3}
        className="rounded-full bg-ink px-3.5 py-1.5 text-xs text-white disabled:opacity-50"
      >
        {t.save}
      </button>
    </form>
  )
}

/**
 * Anomalies du brouillon. Une anomalie de champ (absent, incertain) se traite sur le champ
 * lui-même ; les autres se lèvent ici avec une justification écrite.
 */
export function AnomaliesPanel({
  anomalies,
  canResolve,
  pending,
  onResolve,
}: {
  anomalies: readonly Anomaly[]
  canResolve: boolean
  pending: boolean
  onResolve: (id: string, justification: string) => void
}) {
  if (anomalies.length === 0)
    return (
      <p className="flex items-center gap-2.5 rounded-field bg-sky-wash px-4 py-3 text-sm text-sky-deep">
        <CircleCheck className="size-4" aria-hidden="true" />
        {t.noAnomaly}
      </p>
    )
  const fieldBound = (a: Anomaly) =>
    a.code === 'LOW_CONFIDENCE' || a.code === 'MISSING_REQUIRED_FIELD'
  const openFieldCount = anomalies.filter((a) => fieldBound(a) && !a.resolved).length
  const others = anomalies.filter((a) => !fieldBound(a))
  return (
    <ul className="grid gap-2">
      {openFieldCount > 0 && (
        <li className="flex items-center gap-2.5 rounded-field bg-amber-wash px-4 py-3 text-[13px] text-amber-ink">
          <PencilLine className="size-4 shrink-0" aria-hidden="true" />
          <span className="label mr-1 text-[10px]">{t.blocking}</span>
          {t.fieldGroup(openFieldCount)}
        </li>
      )}
      {others.map((a) => {
        const blocking = a.severity === 'BLOCKING'
        const tone = a.resolved
          ? 'bg-mist text-ink-soft'
          : blocking
            ? 'bg-coral-wash text-coral-ink'
            : 'bg-amber-wash text-amber-ink'
        const Icon = a.resolved ? CircleCheck : blocking ? CircleAlert : TriangleAlert
        return (
          <li
            key={a.id}
            className={`flex gap-2.5 rounded-field px-4 py-3 text-[13px] leading-relaxed ${tone}`}
          >
            <Icon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <div className="min-w-0">
              <span className="label mr-2 text-[10px]">{blocking ? t.blocking : t.warning}</span>
              <span className={a.resolved ? 'line-through' : ''}>{a.message}</span>
              {a.resolved && a.justification && (
                <p className="mt-1 text-xs">{`${t.resolved(displayUser(a.resolved_by))} : ${a.justification}`}</p>
              )}
              {!a.resolved && canResolve && (
                <ResolveForm pending={pending} onResolve={(j) => onResolve(a.id, j)} />
              )}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
