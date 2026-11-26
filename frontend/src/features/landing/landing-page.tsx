import { ClosingSection } from './closing-section'
import { FlowSection } from './flow-section'
import { GuaranteesSection } from './guarantees-section'
import { LandingHero } from './landing-hero'
import { MeasuresSection } from './measures-section'
import { TrySection } from './try-section'
import { UncertaintySection } from './uncertainty-section'

/** Page d'accueil publique : ce que fait le produit, comment, et avec quelles garanties. */
export function LandingPage() {
  return (
    <div className="grid gap-4 bg-ice p-2 sm:gap-5 sm:p-3">
      <LandingHero />
      <div className="mx-auto grid w-full max-w-[1320px] gap-16 px-2 pt-12 sm:gap-20 sm:px-6 sm:pt-16">
        <TrySection />
        <FlowSection />
        <UncertaintySection />
        <GuaranteesSection />
        <MeasuresSection />
        <ClosingSection />
      </div>
    </div>
  )
}
