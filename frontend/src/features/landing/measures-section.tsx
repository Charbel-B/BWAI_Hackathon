import { fr } from '@/i18n/fr'

import { SectionTitle } from './section-title'

const t = fr.landing

/** L'apport de l'IA, chiffré sur un jeu de test séparé. */
export function MeasuresSection() {
  return (
    <section
      id="mesures"
      className="scroll-mt-6 grid gap-10 rounded-[32px] bg-lime px-6 py-12 text-lime-ink sm:px-12 sm:py-16"
    >
      <SectionTitle
        light={t.measuresTitle[0]}
        bold={t.measuresTitle[1]}
        lead={t.measuresLead}
        tone="lime"
      />
      <dl className="grid gap-6 sm:grid-cols-3">
        {t.measures.map((m) => (
          <div key={m.label} className="border-t border-lime-ink/20 pt-5">
            <dt className="tabular text-[clamp(48px,6vw,88px)] leading-none tracking-[-0.04em]">
              {m.value}
            </dt>
            <dd className="mt-3 text-[15px]">{m.label}</dd>
          </div>
        ))}
      </dl>
      <p className="font-mono text-xs opacity-70">{t.measuresSource}</p>
    </section>
  )
}
