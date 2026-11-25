/** Jauge circulaire de confiance. La valeur exacte est toujours écrite à côté, jamais seule. */
export function ConfidenceRing({ value, tone = 'sky' }: { value: number; tone?: 'sky' | 'amber' }) {
  const color = tone === 'sky' ? 'var(--color-sky)' : 'var(--color-amber)'
  const r = 11
  const length = 2 * Math.PI * r
  return (
    <svg viewBox="0 0 28 28" className="size-7 -rotate-90 shrink-0" aria-hidden="true">
      <circle cx="14" cy="14" r={r} fill="none" stroke="var(--color-ink-track)" strokeWidth="3.5" />
      <circle
        cx="14"
        cy="14"
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeDasharray={`${length * value} ${length}`}
        className="transition-[stroke-dasharray] duration-500 ease-out"
      />
    </svg>
  )
}
