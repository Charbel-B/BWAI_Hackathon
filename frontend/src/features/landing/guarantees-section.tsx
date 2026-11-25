import { fr } from '@/i18n/fr'

import { SectionTitle } from './section-title'

const t = fr.landing

/** Les garanties du cœur déterministe, dites par leur mécanisme et non par un slogan. */
export function GuaranteesSection() {
  return (
    <section
      id="garanties"
      className="scroll-mt-6 grid gap-10 rounded-[32px] bg-white px-6 py-12 shadow-card sm:px-12 sm:py-16"
    >
      <SectionTitle light={t.guaranteesTitle[0]} bold={t.guaranteesTitle[1]} />
      <dl className="grid gap-x-10 sm:grid-cols-2 lg:grid-cols-3">
        {t.guarantees.map((g) => (
          <div key={g.title} className="border-t border-line py-6">
            <dt className="text-[19px] font-semibold tracking-[-0.01em]">{g.title}</dt>
            <dd className="mt-2 text-[15px] leading-relaxed text-ink-soft">{g.text}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
