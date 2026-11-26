import { ArrowRight, FileText } from 'lucide-react'
import { useNavigate } from 'react-router'

import type { components } from '@/api/schema'
import { fr } from '@/i18n/fr'

type AnswerOut = components['schemas']['AnswerOut']

export type Turn = { role: 'user'; text: string } | { role: 'assistant'; answer: AnswerOut }

/** Un échange : la question à droite, la réponse à gauche avec ses sources et ses actions. */
export function CopilotMessage({ turn, onNavigate }: { turn: Turn; onNavigate: () => void }) {
  const navigate = useNavigate()
  if (turn.role === 'user')
    return (
      <p className="enter ml-auto max-w-[85%] rounded-[18px] rounded-br-md bg-sky px-4 py-2.5 text-[14px] text-white">
        {turn.text}
      </p>
    )
  const a = turn.answer
  return (
    <div className="enter grid max-w-[92%] gap-2.5 rounded-[18px] rounded-bl-md bg-ice px-4 py-3 text-[14px] leading-relaxed text-ink">
      <p className="whitespace-pre-line">{a.answer}</p>
      {a.sources.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="label text-[10px] text-ink-soft">{fr.assistant.sources}</span>
          {a.sources.map((s, i) => (
            <span
              key={`${s.label}-${i}`}
              className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 font-mono text-[10.5px] text-ink-soft shadow-[inset_0_0_0_1px_var(--color-line)]"
            >
              <FileText className="size-3" aria-hidden="true" />
              {s.field ? `${s.label} · ${s.field}` : s.label}
            </span>
          ))}
        </div>
      )}
      {a.actions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {a.actions.map((x) => (
            <button
              key={x.path + x.label}
              type="button"
              onClick={() => {
                void navigate(x.path)
                onNavigate()
              }}
              className="inline-flex items-center gap-1.5 rounded-full bg-night px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-sky-deep"
            >
              {x.label}
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
