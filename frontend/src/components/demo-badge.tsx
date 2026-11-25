import { fr } from '@/i18n/fr'

/** Rappel permanent que les services extérieurs sont simulés (ADR 0005). */
export function DemoBadge({ compact = false }: { compact?: boolean }) {
  return (
    <span
      title={fr.demo.explain}
      className="label inline-flex items-center gap-2 rounded-full bg-graphite px-3 py-2 text-white"
    >
      <span
        aria-hidden="true"
        className="size-[7px] rounded-full bg-lime shadow-[0_0_0_3px_color-mix(in_srgb,var(--color-lime)_25%,transparent)]"
      />
      {compact ? fr.demo.short : fr.demo.badge}
    </span>
  )
}
