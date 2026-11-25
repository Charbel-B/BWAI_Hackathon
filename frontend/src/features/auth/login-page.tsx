import { CircleAlert, PencilLine, ScanText, Sigma } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { Navigate, useLocation } from 'react-router'

import heroImage from '@/assets/hero-facture-verre.webp'
import { Button } from '@/components/button'
import { ConfidenceRing } from '@/components/confidence-ring'
import { DemoBadge } from '@/components/demo-badge'
import { Logo } from '@/components/logo'
import { fr } from '@/i18n/fr'

import { useLogin } from './use-login'
import { useCurrentUser } from './use-session'

const ACCOUNTS = ['operateur', 'validateur', 'admin'] as const
const t = fr.login

function Callout({
  icon,
  title,
  detail,
  className,
}: {
  icon: React.ReactNode
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

/** Connexion : le héros montre le mécanisme, une pièce annotée par ses champs. */
export function LoginPage() {
  const user = useCurrentUser()
  const location = useLocation()
  const login = useLogin()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const from = (location.state as { from?: string } | null)?.from ?? '/'
  if (user !== null) return <Navigate to={from} replace />

  function submit(event: FormEvent) {
    event.preventDefault()
    login.mutate({ username: username.trim(), password })
  }

  function fill(account: string) {
    setUsername(account)
    setPassword(`demo-${account}`)
  }

  return (
    <div className="min-h-dvh bg-ice p-2 sm:p-3">
      <section className="relative isolate flex min-h-[calc(100dvh-24px)] flex-col overflow-hidden rounded-[32px] bg-[linear-gradient(180deg,var(--color-sky-strong)_0%,var(--color-sky-horizon)_46%,var(--color-sky-haze)_100%)] text-white">
        <div className="flex items-center justify-between gap-4 px-5 pt-5 sm:px-8">
          <Logo />
          <DemoBadge />
        </div>

        <div className="mx-auto mt-[clamp(20px,4vh,48px)] px-5 text-center">
          <h1 className="mx-auto max-w-[15ch] text-[clamp(38px,5.2vw,72px)]">
            {t.titleLight} <b className="font-semibold">{t.titleBold}</b>
          </h1>
        </div>
        <p className="mx-auto mt-4 max-w-[52ch] px-5 text-center text-[17px] leading-relaxed text-white/90">
          {t.lead}
        </p>

        <div className="relative mx-auto mt-2 aspect-[16/9] w-[min(100%,calc(58dvh*16/9),1180px)]">
          <img
            src={heroImage}
            alt={t.heroAlt}
            className="pointer-events-none absolute inset-0 size-full object-cover [mask-composite:intersect] [mask-image:linear-gradient(to_bottom,transparent_0,#000_20%,#000_78%,transparent_100%),linear-gradient(to_right,transparent_0,#000_14%,#000_86%,transparent_100%)]"
          />
          <Callout
            className="top-[30%] left-[2%]"
            title={t.callouts.customer.title}
            detail={t.callouts.customer.detail}
            icon={
              <span className="grid size-9 place-items-center rounded-[11px] bg-sky-wash">
                <ConfidenceRing value={0.95} />
              </span>
            }
          />
          <Callout
            className="top-[22%] right-[3%]"
            title={t.callouts.vat.title}
            detail={t.callouts.vat.detail}
            icon={
              <span className="grid size-9 place-items-center rounded-[11px] bg-ink text-white">
                <Sigma className="size-[18px]" aria-hidden="true" />
              </span>
            }
          />
          <Callout
            className="top-[56%] right-[6%]"
            title={t.callouts.quantity.title}
            detail={t.callouts.quantity.detail}
            icon={
              <span className="grid size-9 place-items-center rounded-[11px] bg-amber text-amber-ink">
                <ScanText className="size-[18px]" aria-hidden="true" />
              </span>
            }
          />
          <Callout
            className="top-[62%] left-[5%]"
            title={t.callouts.corrected.title}
            detail={t.callouts.corrected.detail}
            icon={
              <span className="grid size-9 place-items-center rounded-[11px] bg-lime text-lime-ink">
                <PencilLine className="size-[18px]" aria-hidden="true" />
              </span>
            }
          />
        </div>

        <div className="relative z-10 -mt-[clamp(40px,7dvh,72px)] px-4 pb-7">
          <form
            onSubmit={submit}
            className="mx-auto flex w-full max-w-[640px] flex-col gap-2 rounded-[26px] border border-white/45 bg-white/25 p-1.5 shadow-float backdrop-blur-[20px] sm:flex-row sm:rounded-full"
          >
            <label className="sr-only" htmlFor="username">
              {t.username}
            </label>
            <input
              id="username"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={t.username}
              className="min-w-0 flex-1 rounded-full bg-white px-5 py-3 text-sm text-ink outline-none placeholder:text-ink-soft focus-visible:shadow-[0_0_0_3px_var(--color-sky)]"
            />
            <label className="sr-only" htmlFor="password">
              {t.password}
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t.password}
              className="min-w-0 flex-1 rounded-full bg-white px-5 py-3 text-sm text-ink outline-none placeholder:text-ink-soft focus-visible:shadow-[0_0_0_3px_var(--color-sky)]"
            />
            <Button type="submit" variant="primary" arrow pending={login.isPending}>
              {login.isPending ? t.submitting : t.submit}
            </Button>
          </form>
          <div
            aria-live="polite"
            className="mx-auto mt-3 flex min-h-6 max-w-[640px] flex-wrap items-center justify-center gap-x-3 gap-y-2 text-[13px] text-ink"
          >
            {login.isError ? (
              <span className="inline-flex items-center gap-2 rounded-full bg-coral-wash px-3 py-1.5 text-coral-ink">
                <CircleAlert className="size-4" aria-hidden="true" />
                {t.failed}
              </span>
            ) : (
              <>
                <span className="text-ink/75">{t.accounts}</span>
                {ACCOUNTS.map((account) => (
                  <button
                    key={account}
                    type="button"
                    onClick={() => fill(account)}
                    className="rounded-full bg-white/70 px-3 py-1 font-mono text-xs text-ink transition-colors hover:bg-white"
                  >
                    {account}
                  </button>
                ))}
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
