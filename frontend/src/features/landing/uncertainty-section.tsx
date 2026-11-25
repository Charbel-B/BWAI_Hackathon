import { PencilLine, X } from 'lucide-react'

import { ConfidenceRing } from '@/components/confidence-ring'
import { fr } from '@/i18n/fr'

import { SectionTitle } from './section-title'

const t = fr.landing

const SHELL = {
  sure: 'bg-white/[0.06] shadow-[inset_0_0_0_1px_var(--color-night-line)]',
  unsure: 'bg-amber/10 outline-[1.5px] -outline-offset-[1.5px] outline-amber outline-dashed',
  missing:
    'bg-[repeating-linear-gradient(135deg,var(--color-coral-hatch)_0_8px,transparent_8px_16px)] shadow-[inset_0_0_0_1.5px_var(--color-coral-line)]',
  corrected: 'bg-white/[0.06] shadow-[inset_0_0_0_1px_var(--color-night-line)]',
} as const

function Marker({ tone }: { tone: keyof typeof SHELL }) {
  if (tone === 'sure') return <ConfidenceRing value={0.95} />
  if (tone === 'unsure') return <ConfidenceRing value={0.72} tone="amber" />
  if (tone === 'missing')
    return (
      <span className="grid size-7 place-items-center rounded-full bg-coral text-white">
        <X className="size-3.5" strokeWidth={2.6} aria-hidden="true" />
      </span>
    )
  return (
    <span className="grid size-7 place-items-center rounded-full bg-lime text-lime-ink">
      <PencilLine className="size-3.5" aria-hidden="true" />
    </span>
  )
}

/** La promesse centrale : ce que l'IA ne sait pas se voit, et rien n'est inventé. */
export function UncertaintySection() {
  return (
    <section
      id="incertitude"
      className="scroll-mt-6 grid gap-10 rounded-[32px] bg-graphite px-6 py-12 text-white sm:px-12 sm:py-16"
    >
      <SectionTitle
        light={t.uncertaintyTitle[0]}
        bold={t.uncertaintyTitle[1]}
        lead={t.uncertaintyLead}
        tone="light"
      />
      <ul className="grid gap-3 md:grid-cols-2">
        {t.states.map((state) => (
          <li
            key={state.tone}
            className={`grid grid-cols-[28px_1fr] items-center gap-4 rounded-[18px] px-5 py-5 ${SHELL[state.tone as keyof typeof SHELL]}`}
          >
            <Marker tone={state.tone as keyof typeof SHELL} />
            <span>
              <b className="block text-[17px] font-semibold">{state.label}</b>
              <span className="text-sm text-white/65">{state.detail}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
