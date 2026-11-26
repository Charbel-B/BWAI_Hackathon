import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router'

import { paths } from '@/app/paths'
import { Button } from '@/components/button'
import { DemoBadge } from '@/components/demo-badge'
import { HeroVisual } from '@/components/hero-visual'
import { Logo } from '@/components/logo'
import { useCurrentUser } from '@/features/auth/use-session'
import { fr } from '@/i18n/fr'

const t = fr.landing
const order = (i: number) => ({ '--i': i }) as CSSProperties
const ANCHORS = [
  { id: 'parcours', label: t.nav.flow },
  { id: 'incertitude', label: t.nav.uncertainty },
  { id: 'garanties', label: t.nav.guarantees },
  { id: 'mesures', label: t.nav.measures },
] as const

/** Premier écran : la promesse, puis le mécanisme montré, puis l'entrée. */
export function LandingHero() {
  const navigate = useNavigate()
  const user = useCurrentUser()
  const enter = () => void navigate(user ? paths.dashboard : paths.login)

  return (
    <section className="relative isolate overflow-hidden rounded-[32px] bg-[linear-gradient(180deg,var(--color-sky-strong)_0%,var(--color-sky-horizon)_46%,var(--color-sky-haze)_100%)] pb-10 text-white">
      <header className="flex flex-wrap items-center justify-between gap-4 px-5 pt-5 sm:px-8">
        <Logo />
        <nav
          aria-label="Sections"
          className="hidden gap-1 rounded-full border border-white/30 bg-white/15 p-[5px] backdrop-blur-[18px] lg:flex"
        >
          {ANCHORS.map((a) => (
            <a
              key={a.id}
              href={`#${a.id}`}
              className="label rounded-full px-4 py-2.5 text-white transition-colors hover:bg-white/15"
            >
              {a.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-flex">
            <DemoBadge />
          </span>
          <span className="sm:hidden">
            <DemoBadge compact />
          </span>
          <button
            type="button"
            onClick={enter}
            className="rounded-full border border-white/40 bg-white/15 px-4 py-2.5 text-sm font-medium text-white backdrop-blur-[18px] transition-colors hover:bg-white/25"
          >
            {user ? t.openApp : t.login}
          </button>
        </div>
      </header>

      <div className="mx-auto mt-[clamp(36px,7vh,88px)] px-5 text-center">
        <h1 className="mx-auto max-w-[15ch] text-[clamp(40px,6vw,84px)]">
          <span style={order(0)} className="enter block">
            {t.titleLight}
          </span>
          <b style={order(1)} className="enter block font-semibold">
            {t.titleBold}{' '}
            <span className="relative inline-block whitespace-nowrap">
              {t.titleAccent}
              <svg
                aria-hidden="true"
                viewBox="0 0 300 18"
                preserveAspectRatio="none"
                className="underline-draw absolute -bottom-[0.14em] left-0 h-[0.22em] w-full overflow-visible"
              >
                <path
                  d="M3 12 C 60 4, 120 3, 175 8 S 270 13, 297 6"
                  pathLength={1}
                  fill="none"
                  stroke="var(--color-lime)"
                  strokeWidth="7"
                  strokeLinecap="round"
                />
              </svg>
            </span>
          </b>
        </h1>
        <p
          style={order(2)}
          className="enter mx-auto mt-7 max-w-[56ch] text-[17px] leading-relaxed text-white/90"
        >
          {t.lead}
        </p>
        <div style={order(3)} className="enter mt-8 flex flex-wrap justify-center gap-3">
          <Button variant="primary" arrow onClick={enter}>
            {user ? t.openApp : t.tryDemo}
          </Button>
          <a
            href="#parcours"
            className="inline-flex items-center rounded-full bg-white/15 px-5 py-3 text-sm font-medium text-white backdrop-blur-[18px] transition-colors hover:bg-white/25"
          >
            {t.nav.flow}
          </a>
        </div>
      </div>

      <div style={order(4)} className="enter">
        <HeroVisual className="mx-auto -mt-4 w-[min(100%,1180px)]" />
      </div>
    </section>
  )
}
