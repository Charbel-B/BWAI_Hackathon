import type { CSSProperties, ReactNode } from 'react'

import { useInView } from '@/lib/use-reveal'

/** Fait apparaître son contenu quand il entre à l'écran ; `index` décale l'entrée. */
export function Reveal({
  children,
  index = 0,
  className = '',
}: {
  children: ReactNode
  index?: number
  className?: string
}) {
  const { ref, shown } = useInView<HTMLDivElement>()
  return (
    <div
      ref={ref}
      style={{ '--i': index } as CSSProperties}
      className={`reveal ${shown ? 'is-shown' : ''} ${className}`}
    >
      {children}
    </div>
  )
}
