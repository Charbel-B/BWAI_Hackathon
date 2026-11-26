import { PencilLine, ScanText, Sigma } from 'lucide-react'
import type { CSSProperties, ReactNode } from 'react'

import heroImage from '@/assets/hero-facture-verre.webp'
import { fr } from '@/i18n/fr'

import { ConfidenceRing } from './confidence-ring'

const c = fr.hero.callouts
const tile = 'grid size-9 place-items-center rounded-[11px]'

interface CalloutProps {
  icon: ReactNode
  title: string
  detail: string
  className: string
  index: number
}

/** Une annotation : elle apparaît après la pièce, puis flotte à son propre rythme. */
function Callout({ icon, title, detail, className, index }: CalloutProps) {
  const order = { '--i': index } as CSSProperties
  return (
    <div style={order} className={`enter-pop absolute hidden lg:block ${className}`}>
      <div
        style={order}
        className="float glass flex items-center gap-3 rounded-[18px] py-3 pr-4 pl-3 text-ink shadow-float"
      >
        {icon}
        <div>
          <b className="block text-sm font-semibold">{title}</b>
          <span className="text-xs text-ink-soft">{detail}</span>
        </div>
      </div>
    </div>
  )
}

/**
 * Le mécanisme en une image : la pièce au centre, annotée par ses champs, parcourue par un
 * balayage de lecture. Le rendu se fond dans le ciel par un masque, sans bord visible.
 */
export function HeroVisual({
  callouts = true,
  className = '',
}: {
  callouts?: boolean
  className?: string
}) {
  return (
    <div className={`relative aspect-[16/9] ${className}`}>
      <img
        src={heroImage}
        alt={fr.hero.alt}
        className="pointer-events-none absolute inset-0 size-full object-cover [mask-composite:intersect] [mask-image:linear-gradient(to_bottom,transparent_0,#000_20%,#000_78%,transparent_100%),linear-gradient(to_right,transparent_0,#000_14%,#000_86%,transparent_100%)]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-[14%] left-[34%] h-[66%] w-[33%] -rotate-[14deg] overflow-hidden [mask-image:linear-gradient(to_right,transparent,#000_18%,#000_82%,transparent)]"
      >
        <div className="scan-beam h-[20%] w-full bg-[linear-gradient(180deg,transparent,var(--color-scan-soft)_42%,var(--color-scan-core)_50%,var(--color-scan-soft)_58%,transparent)]" />
      </div>
      {callouts && (
        <>
          <Callout
            index={0}
            className="top-[30%] left-[2%]"
            title={c.customer.title}
            detail={c.customer.detail}
            icon={
              <span className={`${tile} bg-sky-wash`}>
                <ConfidenceRing value={0.95} />
              </span>
            }
          />
          <Callout
            index={1}
            className="top-[22%] right-[3%]"
            title={c.vat.title}
            detail={c.vat.detail}
            icon={
              <span className={`${tile} bg-ink text-white`}>
                <Sigma className="size-[18px]" aria-hidden="true" />
              </span>
            }
          />
          <Callout
            index={2}
            className="top-[56%] right-[6%]"
            title={c.quantity.title}
            detail={c.quantity.detail}
            icon={
              <span className={`${tile} bg-amber text-amber-ink`}>
                <ScanText className="size-[18px]" aria-hidden="true" />
              </span>
            }
          />
          <Callout
            index={3}
            className="top-[62%] left-[5%]"
            title={c.corrected.title}
            detail={c.corrected.detail}
            icon={
              <span className={`${tile} bg-lime text-lime-ink`}>
                <PencilLine className="size-[18px]" aria-hidden="true" />
              </span>
            }
          />
        </>
      )}
    </div>
  )
}
