import { ArrowLeft, CircleAlert } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router'

import { paths } from '@/app/paths'
import { Button } from '@/components/button'
import { DemoBadge } from '@/components/demo-badge'
import { HeroVisual } from '@/components/hero-visual'
import { Logo } from '@/components/logo'
import { fr } from '@/i18n/fr'

import { useLogin } from './use-login'
import { useCurrentUser } from './use-session'

const ACCOUNTS = ['operateur', 'validateur', 'admin'] as const
const t = fr.login
const field =
  'w-full rounded-2xl bg-ice px-4 py-3.5 text-[15px] text-ink outline-none shadow-[inset_0_0_0_1px_var(--color-line)] placeholder:text-ink-soft focus-visible:shadow-[inset_0_0_0_2px_var(--color-sky)]'

/** Connexion : le formulaire à gauche, le visuel du produit à droite. */
export function LoginPage() {
  const user = useCurrentUser()
  const location = useLocation()
  const login = useLogin()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const from = (location.state as { from?: string } | null)?.from ?? paths.dashboard
  if (user !== null) return <Navigate to={from} replace />

  function submit(event: FormEvent) {
    event.preventDefault()
    login.mutate({ username: username.trim(), password })
  }

  return (
    <div className="grid min-h-dvh bg-ice p-2 sm:p-3 lg:grid-cols-[minmax(420px,0.9fr)_1.1fr] lg:gap-3">
      <section className="flex flex-col rounded-[32px] bg-white px-6 py-6 shadow-card sm:px-12 sm:py-8">
        <div className="flex items-center justify-between gap-4">
          <Link to={paths.landing} aria-label={t.back}>
            <Logo tone="dark" />
          </Link>
          <Link
            to={paths.landing}
            className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm text-ink-soft transition-colors hover:bg-ice hover:text-ink"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            {t.back}
          </Link>
        </div>

        <div className="mx-auto my-auto w-full max-w-[400px] py-12">
          <h1 className="text-[clamp(38px,4vw,52px)]">
            <b className="font-semibold">{t.title}</b>
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-ink-soft">{t.lead}</p>

          <form onSubmit={submit} className="mt-8 grid gap-3">
            <label className="grid gap-1.5">
              <span className="label text-ink-soft">{t.username}</span>
              <input
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className={field}
              />
            </label>
            <label className="grid gap-1.5">
              <span className="label text-ink-soft">{t.password}</span>
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={field}
              />
            </label>
            {login.isError && (
              <p
                role="alert"
                className="flex items-center gap-2 rounded-xl bg-coral-wash px-3.5 py-2.5 text-sm text-coral-ink"
              >
                <CircleAlert className="size-4 shrink-0" aria-hidden="true" />
                {t.failed}
              </p>
            )}
            <Button
              type="submit"
              variant="primary"
              arrow
              pending={login.isPending}
              className="mt-2 w-full py-3.5 text-[15px]"
            >
              {login.isPending ? t.submitting : t.submit}
            </Button>
          </form>

          <div className="mt-10">
            <div className="flex items-baseline justify-between gap-3">
              <span className="label text-ink-soft">{t.accounts}</span>
              <span className="text-xs text-ink-soft">{t.accountsHint}</span>
            </div>
            <ul className="mt-3 grid gap-2">
              {ACCOUNTS.map((account) => {
                const selected = username === account
                return (
                  <li key={account}>
                    <button
                      type="button"
                      onClick={() => {
                        setUsername(account)
                        setPassword(`demo-${account}`)
                      }}
                      aria-pressed={selected}
                      className={`grid w-full grid-cols-[auto_1fr] items-center gap-x-3 rounded-2xl px-4 py-3 text-left transition-[box-shadow,background] duration-200 ease-out ${selected ? 'bg-sky-wash shadow-[inset_0_0_0_1.5px_var(--color-sky)]' : 'bg-ice shadow-[inset_0_0_0_1px_var(--color-line)] hover:shadow-[inset_0_0_0_1px_var(--color-sky-soft)]'}`}
                    >
                      <span className="font-mono text-sm">{account}</span>
                      <span className="text-right text-xs leading-snug text-ink-soft">
                        {t.roles[account]}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        </div>
      </section>

      <aside className="relative hidden flex-col overflow-hidden rounded-[32px] bg-[linear-gradient(180deg,var(--color-sky-strong)_0%,var(--color-sky-horizon)_46%,var(--color-sky-haze)_100%)] p-8 text-white lg:flex">
        <div className="flex justify-end">
          <DemoBadge />
        </div>
        <div className="my-auto">
          <HeroVisual callouts={false} className="w-full" />
        </div>
        <p className="mx-auto max-w-[36ch] text-center text-[15px] text-ink">{t.visualCaption}</p>
      </aside>
    </div>
  )
}
