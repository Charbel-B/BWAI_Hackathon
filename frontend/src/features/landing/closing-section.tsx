import { useNavigate } from 'react-router'

import { paths } from '@/app/paths'
import { Button } from '@/components/button'
import { DemoBadge } from '@/components/demo-badge'
import { Logo } from '@/components/logo'
import { useCurrentUser } from '@/features/auth/use-session'
import { fr } from '@/i18n/fr'

const t = fr.landing

/** Ce qui est simulé, dit franchement ; puis l'invitation, puis le pied de page. */
export function ClosingSection() {
  const navigate = useNavigate()
  const user = useCurrentUser()
  return (
    <>
      <section className="grid gap-5 rounded-[32px] bg-white px-6 py-10 shadow-card sm:grid-cols-[auto_1fr] sm:items-center sm:px-12">
        <DemoBadge />
        <div>
          <h2 className="text-[24px] font-semibold tracking-[-0.02em]">{t.simulatedTitle}</h2>
          <p className="mt-2 max-w-[78ch] text-[15px] leading-relaxed text-ink-soft">
            {t.simulatedText}
          </p>
        </div>
      </section>

      <section className="sky relative overflow-hidden rounded-[32px] px-6 py-16 text-center text-white sm:py-20">
        <h2 className="mx-auto max-w-[16ch] text-[clamp(34px,4.6vw,64px)]">
          {t.ctaTitle[0]} <b className="font-semibold">{t.ctaTitle[1]}</b>
        </h2>
        <p className="mx-auto mt-4 max-w-[52ch] text-[16px] text-white/85">{t.ctaLead}</p>
        <Button
          variant="primary"
          arrow
          className="mt-8"
          onClick={() => void navigate(user ? paths.dashboard : paths.login)}
        >
          {user ? t.openApp : t.tryDemo}
        </Button>
      </section>

      <footer className="flex flex-wrap items-center justify-between gap-4 px-2 py-6 text-sm text-ink-soft">
        <Logo tone="dark" />
        <span>{t.footer}</span>
      </footer>
    </>
  )
}
