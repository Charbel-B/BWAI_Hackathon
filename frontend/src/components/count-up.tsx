import { useEffect, useState } from 'react'

import { useInView } from '@/lib/use-reveal'

const DURATION_MS = 1100

function prefersReducedMotion(): boolean {
  return (
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/**
 * Compteur pour l'affichage : défile jusqu'à `value` quand il entre à l'écran.
 * Purement visuel : la valeur finale est celle reçue, jamais recalculée.
 */
export function CountUp({
  value,
  format = (n) => String(n),
  className = '',
}: {
  value: number
  format?: (n: number) => string
  className?: string
}) {
  const { ref, shown } = useInView<HTMLSpanElement>()
  const [current, setCurrent] = useState(0)
  const instant = value === 0 || prefersReducedMotion()

  useEffect(() => {
    if (!shown || instant) return
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / DURATION_MS)
      const eased = 1 - Math.pow(1 - progress, 4)
      setCurrent(Math.round(value * eased))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [shown, value, instant])

  return (
    <span ref={ref} className={className} aria-label={format(value)}>
      <span aria-hidden="true">{format(instant ? value : shown ? current : 0)}</span>
    </span>
  )
}
