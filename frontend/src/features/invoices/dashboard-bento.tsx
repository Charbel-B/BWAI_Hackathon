import { FilePlus2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { paths } from '@/app/paths'
import inboxImage from '@/assets/bac-arrivee-verre.webp'
import stampImage from '@/assets/cachet-verre.webp'
import tokensImage from '@/assets/jetons-regles-verre.webp'
import { Button } from '@/components/button'
import { CountUp } from '@/components/count-up'
import { Reveal } from '@/components/reveal'
import { PaymentBadge } from '@/components/status-badge'
import { fr } from '@/i18n/fr'

const t = fr.dashboard

/** Visuel d'arrière-plan d'une carte, fondu vers le contenu pour ne jamais gêner la lecture. */
function Backdrop({ src, className }: { src: string; className: string }) {
  return (
    <img
      src={src}
      alt=""
      aria-hidden="true"
      className={`pointer-events-none absolute select-none ${className}`}
    />
  )
}

function Card({
  index,
  className,
  children,
}: {
  index: number
  className: string
  children: ReactNode
}) {
  return (
    <Reveal index={index} className="grid">
      <div
        className={`lift relative isolate flex min-h-[176px] flex-col justify-between overflow-hidden rounded-card p-6 ${className}`}
      >
        {children}
      </div>
    </Reveal>
  )
}

const figure = 'tabular relative text-[46px] leading-none tracking-[-0.03em]'

/** Compteurs du tableau de bord, chacun sur sa matière : ciel, verre, glace. */
export function DashboardBento({
  drafts,
  live,
  paid,
  audit,
}: {
  drafts: number
  live: number
  paid: number
  audit: ReactNode
}) {
  const navigate = useNavigate()
  return (
    <div className="grid gap-4 lg:grid-cols-[1.25fr_1fr_1fr] lg:grid-rows-[auto_auto]">
      <Reveal index={0} className="grid lg:row-span-2">
        <div className="sky relative isolate flex min-h-[260px] flex-col justify-between gap-6 overflow-hidden rounded-card p-7 text-white shadow-card">
          <Backdrop
            src={inboxImage}
            className="right-[-7%] bottom-[-16%] -z-10 w-[min(50%,250px)] drop-shadow-[var(--shadow-object)]"
          />
          <span className="label text-white/80">{t.toReview}</span>
          <div>
            <CountUp
              value={drafts}
              className="tabular block text-[72px] leading-none tracking-[-0.04em]"
            />
            <p className="mt-2 max-w-[20ch] text-[15px] text-white/90">
              {t.toReviewDetail(drafts)}
            </p>
          </div>
          <Button
            variant="primary"
            arrow
            className="self-start"
            icon={<FilePlus2 className="size-4" aria-hidden="true" />}
            onClick={() => void navigate(paths.import)}
          >
            {t.importCta}
          </Button>
        </div>
      </Reveal>

      <Card index={1} className="bg-white shadow-card">
        <Backdrop
          src={stampImage}
          className="right-[-18px] bottom-[-26px] -z-10 w-[150px] opacity-90 [mask-image:radial-gradient(circle_at_65%_65%,#000_45%,transparent_78%)]"
        />
        <span className="label text-ink-soft">{fr.status.VALIDATED}</span>
        <CountUp value={live} className={figure} />
        <span className="text-sm text-ink-soft">{t.validated(live)}</span>
      </Card>

      <Card index={2} className="bg-white shadow-card">
        <span aria-hidden="true" className="absolute inset-x-6 top-0 h-1 rounded-b-full bg-lime" />
        <span className="label text-ink-soft">{t.extraction}</span>
        <div>
          <span className={`${figure} text-sky-deep`}>{t.extractionValue}</span>
          <span className="mt-2 block text-[13px] text-ink-soft">{t.extractionDetail}</span>
        </div>
      </Card>

      <Card
        index={3}
        className="bg-[linear-gradient(160deg,var(--color-sky-wash),var(--color-ice))] shadow-card"
      >
        <Backdrop
          src={tokensImage}
          className="right-[-14px] bottom-[-24px] -z-10 w-[140px] opacity-90 [mask-image:radial-gradient(circle_at_65%_65%,#000_45%,transparent_78%)]"
        />
        <span className="label text-ink-soft">{fr.payment.PAID}</span>
        <CountUp value={paid} className={figure} />
        <span className="self-start">
          <PaymentBadge status="PAID" />
        </span>
      </Card>

      <Reveal index={4} className="grid">
        {audit}
      </Reveal>
    </div>
  )
}
