import { useEffect, useRef } from 'react'

import type { ExtractedField } from '@/api/types'
import { fr } from '@/i18n/fr'

import type { FieldState } from './field-state'
import { segment } from './segments'

const MARK: Record<FieldState, string> = {
  sure: 'bg-sky/15 shadow-[inset_0_-2px_0_var(--color-sky)]',
  confirmed: 'bg-sky/15 shadow-[inset_0_-2px_0_var(--color-ink)]',
  unsure: 'bg-amber/20 shadow-[inset_0_-2px_0_var(--color-amber)]',
  corrected:
    'bg-lime/40 shadow-[inset_0_-2px_0_var(--color-lime-ink)] line-through decoration-lime-ink/50',
  missing: '',
  absent: '',
}

interface Props {
  text: string
  filename: string
  fields: readonly ExtractedField[]
  states: ReadonlyMap<string, FieldState>
  active: string | null
  onHover: (name: string | null) => void
}

/** La pièce telle que reçue ; chaque valeur lue y est surlignée selon son état. */
export function SourceView({ text, filename, fields, states, active, onHover }: Props) {
  const refs = useRef(new Map<string, HTMLElement>())
  useEffect(() => {
    if (active) refs.current.get(active)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [active])

  return (
    <figure className="rounded-[22px] bg-white p-6 shadow-[inset_0_0_0_1px_var(--color-line)]">
      <figcaption className="mb-4 flex items-center justify-between gap-3">
        <span className="label text-ink-soft">{fr.review.source}</span>
        <span className="truncate font-mono text-xs text-ink-soft">{filename}</span>
      </figcaption>
      <pre className="font-mono text-[13.5px] leading-[1.9] whitespace-pre-wrap text-ink-source">
        {segment(text, fields).map((part, index) =>
          part.field === undefined ? (
            <span key={index}>{part.text}</span>
          ) : (
            <mark
              key={index}
              ref={(el) => {
                if (el) refs.current.set(part.field!, el)
              }}
              onMouseEnter={() => onHover(part.field!)}
              onMouseLeave={() => onHover(null)}
              className={`rounded-[5px] px-[3px] py-[2px] text-inherit transition-[box-shadow,background] duration-200 ease-out ${MARK[states.get(part.field) ?? 'sure']} ${active === part.field ? 'bg-sky/30 ring-[3px] ring-sky/30' : ''}`}
            >
              {part.text}
            </mark>
          ),
        )}
      </pre>
    </figure>
  )
}
