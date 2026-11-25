import { Check, Minus, PencilLine, X } from 'lucide-react'
import { type FormEvent, useState } from 'react'

import type { ExtractedField } from '@/api/types'
import { ConfidenceRing } from '@/components/confidence-ring'
import { fr } from '@/i18n/fr'
import { percent } from '@/lib/format'

import { type FieldState, fieldLabel } from './field-state'

const t = fr.review

const SHELL: Record<FieldState, string> = {
  absent: 'bg-ice shadow-[inset_0_0_0_1px_var(--color-line)]',
  sure: 'bg-white shadow-[inset_0_0_0_1px_var(--color-line)]',
  confirmed: 'bg-white shadow-[inset_0_0_0_1px_var(--color-line)]',
  unsure: 'bg-amber-wash outline-[1.5px] outline-dashed -outline-offset-[1.5px] outline-amber',
  missing:
    'bg-[repeating-linear-gradient(135deg,var(--color-coral-wash)_0_8px,#fff_8px_16px)] shadow-[inset_0_0_0_1.5px_var(--color-coral-line)]',
  corrected: 'bg-white shadow-[inset_0_0_0_1px_var(--color-line)]',
}

const TAG: Record<FieldState, string> = {
  absent: 'bg-mist text-ink-soft',
  sure: 'bg-sky-wash text-sky-deep',
  confirmed: 'bg-ink text-white',
  unsure: 'bg-amber text-amber-deep',
  missing: 'bg-coral text-white',
  corrected: 'bg-lime text-lime-ink',
}

function Marker({ state, confidence }: { state: FieldState; confidence: number | null }) {
  if ((state === 'sure' || state === 'unsure') && confidence !== null)
    return <ConfidenceRing value={confidence} tone={state === 'sure' ? 'sky' : 'amber'} />
  const tone = {
    missing: 'bg-coral text-white',
    absent: 'bg-mist text-ink-soft',
    corrected: 'bg-lime text-lime-ink',
    confirmed: 'bg-ink text-white',
  }[state as 'missing']
  const Icon =
    state === 'missing'
      ? X
      : state === 'absent'
        ? Minus
        : state === 'corrected'
          ? PencilLine
          : Check
  return (
    <span className={`grid size-7 shrink-0 place-items-center rounded-full ${tone ?? 'bg-mist'}`}>
      <Icon className="size-3.5" strokeWidth={2.6} aria-hidden="true" />
    </span>
  )
}

interface Props {
  field: ExtractedField
  state: FieldState
  active: boolean
  editable: boolean
  pending: boolean
  onHover: (name: string | null) => void
  onConfirm: () => void
  onCorrect: (value: string) => void
}

/** Un champ extrait : sa valeur, son état lisible sans couleur, et le geste humain possible. */
export function FieldCard({
  field,
  state,
  active,
  editable,
  pending,
  onHover,
  onConfirm,
  onCorrect,
}: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(field.effective_value ?? '')
  const { label, line } = fieldLabel(field.name)
  const tag =
    state === 'sure' && field.confidence !== null
      ? `${t.states.sure} · ${percent(field.confidence)}`
      : state === 'unsure' && field.confidence !== null
        ? `${t.states.unsure} · ${percent(field.confidence)}`
        : t.states[state]

  function submit(event: FormEvent) {
    event.preventDefault()
    if (draft.trim() === '') return
    onCorrect(draft.trim())
    setEditing(false)
  }

  return (
    <li
      onMouseEnter={() => onHover(field.name)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(field.name)}
      className={`rounded-field px-3.5 py-3 transition-[box-shadow,transform] duration-200 ease-out ${SHELL[state]} ${active ? 'shadow-[inset_0_0_0_1.5px_var(--color-sky),var(--shadow-focus-field)] -translate-y-px' : ''}`}
    >
      <div className="grid grid-cols-[28px_1fr_auto] items-center gap-3.5">
        <Marker state={state} confidence={field.confidence} />
        <div className="min-w-0">
          <div className="label text-ink-soft">
            {label}
            {line !== null && ` · ${t.line(line)}`}
          </div>
          <div
            className={`mt-0.5 truncate text-[15px] font-medium ${state === 'missing' ? 'text-coral-ink' : state === 'absent' ? 'font-normal text-ink-soft' : ''}`}
          >
            {state === 'corrected' && field.value !== null && (
              <s className="mr-2 font-normal text-ink-soft">{field.value}</s>
            )}
            {field.effective_value ?? t.states[state === 'absent' ? 'absent' : 'missing']}
          </div>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 font-mono text-[11px] whitespace-nowrap ${TAG[state]}`}
        >
          {tag}
        </span>
      </div>

      {editable && !editing && (state === 'unsure' || state === 'missing' || active) && (
        <div className="mt-3 flex gap-2 pl-[42px]">
          {state !== 'missing' &&
            state !== 'absent' &&
            state !== 'confirmed' &&
            state !== 'corrected' && (
              <button
                type="button"
                disabled={pending}
                onClick={onConfirm}
                className="inline-flex items-center gap-1.5 rounded-full bg-ink px-3.5 py-1.5 text-xs font-medium text-white transition-opacity disabled:opacity-50"
              >
                <Check className="size-3.5" aria-hidden="true" />
                {t.confirm}
              </button>
            )}
          <button
            type="button"
            disabled={pending}
            onClick={() => setEditing(true)}
            className="inline-flex items-center gap-1.5 rounded-full bg-white px-3.5 py-1.5 text-xs font-medium text-ink shadow-[inset_0_0_0_1px_var(--color-line)] disabled:opacity-50"
          >
            <PencilLine className="size-3.5" aria-hidden="true" />
            {state === 'missing' || state === 'absent' ? t.fill : t.correct}
          </button>
        </div>
      )}

      {editing && (
        <form onSubmit={submit} className="mt-3 flex gap-2 pl-[42px]">
          <label className="sr-only" htmlFor={`edit-${field.name}`}>
            {label}
          </label>
          <input
            id={`edit-${field.name}`}
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="min-w-0 flex-1 rounded-full bg-white px-4 py-1.5 text-sm shadow-[inset_0_0_0_1px_var(--color-line)] outline-none focus-visible:shadow-[inset_0_0_0_2px_var(--color-sky)]"
          />
          <button
            type="submit"
            className="rounded-full bg-lime px-3.5 py-1.5 text-xs font-medium text-lime-ink"
          >
            {t.save}
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="rounded-full px-3 py-1.5 text-xs text-ink-soft hover:text-ink"
          >
            {t.cancel}
          </button>
        </form>
      )}
    </li>
  )
}
