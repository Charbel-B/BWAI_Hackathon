import { CountUp } from '@/components/count-up'
import { Reveal } from '@/components/reveal'
import { fr } from '@/i18n/fr'

import { SectionTitle } from './section-title'

const t = fr.landing

/** L'apport de l'IA, chiffré sur un jeu de test séparé ; le citron souligne, il ne recouvre pas. */
export function MeasuresSection() {
  return (
    <section
      id="mesures"
      className="scroll-mt-6 grid gap-10 rounded-[32px] bg-white px-6 py-12 shadow-card sm:px-12 sm:py-16"
    >
      <SectionTitle light={t.measuresTitle[0]} bold={t.measuresTitle[1]} lead={t.measuresLead} />
      <dl className="grid gap-6 sm:grid-cols-3">
        {t.measures.map((m, index) => (
          <Reveal key={m.label} index={index}>
            <div className="relative overflow-hidden rounded-[22px] bg-ice px-6 pt-6 pb-7">
              <span
                aria-hidden="true"
                className="absolute inset-x-6 top-0 h-1 rounded-b-full bg-lime"
              />
              <dt className="tabular text-[clamp(52px,6vw,92px)] leading-none tracking-[-0.04em] text-sky-deep">
                <CountUp value={m.value} format={(n) => `${n}${m.suffix}`} />
              </dt>
              <dd className="mt-3 text-[15px] text-ink-soft">{m.label}</dd>
            </div>
          </Reveal>
        ))}
      </dl>
      <p className="font-mono text-xs text-ink-soft">{t.measuresSource}</p>
    </section>
  )
}
