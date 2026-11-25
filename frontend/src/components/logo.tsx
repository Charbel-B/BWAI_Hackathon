import { fr } from '@/i18n/fr'

/** Marque : une coche dans un sceau arrondi, reprise de la coche du rendu 3D. */
export function Logo({ tone = 'light' }: { tone?: 'light' | 'dark' }) {
  const text = tone === 'light' ? 'text-white' : 'text-ink'
  return (
    <span
      className={`flex items-center gap-2.5 text-[19px] font-semibold tracking-[-0.02em] ${text}`}
    >
      <span className="grid size-[30px] place-items-center rounded-[9px] bg-white shadow-[var(--shadow-mark)]">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M5 12.5 10 17 19 7"
            stroke="var(--color-sky-deep)"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      {fr.brand.name}
    </span>
  )
}
