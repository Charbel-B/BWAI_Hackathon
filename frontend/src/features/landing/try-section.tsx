import { useEffect, useState } from 'react'

import { ConfidenceRing } from '@/components/confidence-ring'
import { Reveal } from '@/components/reveal'
import { fr } from '@/i18n/fr'
import { percent } from '@/lib/format'

import { SectionTitle } from './section-title'

const t = fr.landing
const CYCLE_MS = 2200

interface Part {
  text: string
  field?: number
}

/** Découpe le texte d'exemple autour des valeurs de chaque champ. */
function parts(text: string): Part[] {
  const anchors = t.tryFields
    .map((f, index) => ({
      index,
      start: text.indexOf(f.match),
      end: text.indexOf(f.match) + f.match.length,
    }))
    .filter((a) => a.start >= 0)
    .sort((a, b) => a.start - b.start)
  const out: Part[] = []
  let cursor = 0
  for (const a of anchors) {
    if (a.start < cursor) continue
    if (a.start > cursor) out.push({ text: text.slice(cursor, a.start) })
    out.push({ text: text.slice(a.start, a.end), field: a.index })
    cursor = a.end
  }
  out.push({ text: text.slice(cursor) })
  return out
}

const SOURCE = parts(t.trySource)

function reducedMotion(): boolean {
  return (
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/** La revue, jouable dans la landing : le mécanisme montré plutôt que décrit. */
export function TrySection() {
  const [active, setActive] = useState(0)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    if (paused || reducedMotion()) return
    const timer = window.setInterval(() => setActive((i) => (i + 1) % t.tryFields.length), CYCLE_MS)
    return () => window.clearInterval(timer)
  }, [paused])

  return (
    <section className="grid gap-8">
      <SectionTitle light={t.tryTitle[0]} bold={t.tryTitle[1]} lead={t.tryLead} />
      <Reveal>
        <div
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
          className="grid gap-4 rounded-[32px] bg-white p-4 shadow-card sm:p-6 lg:grid-cols-[1.15fr_1fr]"
        >
          <pre className="rounded-[22px] bg-ice p-6 font-mono text-[14px] leading-[2] whitespace-pre-wrap text-ink-source">
            {SOURCE.map((part, index) =>
              part.field === undefined ? (
                <span key={index}>{part.text}</span>
              ) : (
                <mark
                  key={index}
                  className={`rounded-[6px] px-[3px] py-[2px] text-inherit transition-[background,box-shadow] duration-300 ease-out ${
                    active === part.field
                      ? 'bg-sky/30 shadow-[0_0_0_4px_var(--color-sky-soft)]'
                      : t.tryFields[part.field]?.state === 'unsure'
                        ? 'bg-amber/15 shadow-[inset_0_-2px_0_var(--color-amber)]'
                        : 'bg-sky/10 shadow-[inset_0_-2px_0_var(--color-sky-soft)]'
                  }`}
                >
                  {part.text}
                </mark>
              ),
            )}
          </pre>
          <ul className="grid content-start gap-2">
            {t.tryFields.map((f, index) => {
              const on = active === index
              const unsure = f.state === 'unsure'
              return (
                <li key={f.label}>
                  <button
                    type="button"
                    onMouseEnter={() => setActive(index)}
                    onFocus={() => setActive(index)}
                    className={`grid w-full grid-cols-[28px_1fr_auto] items-center gap-3 rounded-field px-3.5 py-3 text-left transition-[box-shadow,transform,background] duration-300 ease-out ${
                      on
                        ? '-translate-y-px bg-white shadow-[inset_0_0_0_1.5px_var(--color-sky),var(--shadow-focus-field)]'
                        : unsure
                          ? 'bg-amber-wash'
                          : 'bg-ice'
                    }`}
                  >
                    <ConfidenceRing value={f.confidence} tone={unsure ? 'amber' : 'sky'} />
                    <span className="min-w-0">
                      <span className="label block text-ink-soft">{f.label}</span>
                      <b className="block truncate font-medium">{f.value}</b>
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-1 font-mono text-[11px] ${unsure ? 'bg-amber text-amber-deep' : 'bg-sky-wash text-sky-deep'}`}
                    >
                      {`${unsure ? fr.review.states.unsure : fr.review.states.sure} · ${percent(f.confidence)}`}
                    </span>
                  </button>
                </li>
              )
            })}
            <li className="px-1 pt-2 text-xs text-ink-soft">{t.tryHint}</li>
          </ul>
        </div>
      </Reveal>
    </section>
  )
}
