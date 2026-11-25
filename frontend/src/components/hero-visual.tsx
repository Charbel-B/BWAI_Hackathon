import { PencilLine, ScanText, Sigma } from 'lucide-react'
import type { ReactNode } from 'react'

import heroImage from '@/assets/hero-facture-verre.webp'
import { fr } from '@/i18n/fr'

import { ConfidenceRing } from './confidence-ring'

const c = fr.hero.callouts

function Callout({
  icon,
  title,
  detail,
  className,
}: {
  icon: ReactNode
  title: string
  detail: string
  className: string
}) {
  return (
    <div
      className={`glass absolute hidden items-center gap-3 rounded-[18px] py-3 pr-4 pl-3 text-ink shadow-float lg:flex ${className}`}
    >
      {icon}
      <div>
        <b className="block text-sm font-semibold">{title}</b>
        <span className="text-xs text-ink-soft">{detail}</span>
      </div>
    </div>
  )
}

const tile = 'grid size-9 place-items-center rounded-[11px]'

/**
 * Le mécanisme en une image : la pièce au centre, annotée par ses champs.
 * Le rendu se fond dans le ciel par un masque, sans bord visible.
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
      {callouts && (
        <>
          <Callout
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
