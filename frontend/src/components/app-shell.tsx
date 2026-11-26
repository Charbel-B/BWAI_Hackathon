import { LogOut } from 'lucide-react'
import { NavLink, Outlet } from 'react-router'

import { Copilot } from '@/features/assistant/copilot'
import { useCurrentUser } from '@/features/auth/use-session'
import { session } from '@/features/auth/session'
import { paths } from '@/app/paths'
import { fr } from '@/i18n/fr'

import { DemoBadge } from './demo-badge'
import { Logo } from './logo'

const LINKS = [
  { to: paths.dashboard, label: fr.nav.dashboard, end: true },
  { to: paths.import, label: fr.nav.import, end: false },
  { to: paths.collection, label: fr.collection.nav, end: false },
  { to: paths.audit, label: fr.nav.audit, end: false },
  { to: paths.settings, label: fr.settings.nav, end: false },
] as const

/** Cadre de l'application : bandeau de ciel, menu en pilule de verre, contenu sur fond glace. */
export function AppShell() {
  const user = useCurrentUser()
  return (
    <div className="min-h-dvh">
      <header className="sky-band relative pb-44">
        <div className="mx-auto flex max-w-[1320px] flex-wrap items-center justify-between gap-x-4 gap-y-3 px-4 pt-5 sm:flex-nowrap sm:px-8">
          <NavLink to={paths.dashboard} aria-label={fr.nav.dashboard}>
            <Logo />
          </NavLink>
          <nav
            aria-label="Navigation principale"
            className="order-last flex w-full justify-center gap-1 rounded-full border border-white/30 bg-white/15 p-[5px] backdrop-blur-[18px] sm:order-none sm:w-auto"
          >
            {LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `label rounded-full px-3.5 py-2.5 transition-colors duration-200 sm:px-4 ${isActive ? 'bg-white text-ink' : 'text-white hover:bg-white/15'}`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <span className="hidden md:inline-flex">
              <DemoBadge />
            </span>
            <span className="md:hidden">
              <DemoBadge compact />
            </span>
            {user && (
              <button
                type="button"
                onClick={session.clear}
                title={fr.nav.logout}
                className="flex items-center gap-2.5 rounded-full border border-white/30 bg-white/15 py-1.5 pr-1.5 pl-4 text-sm text-white backdrop-blur-[18px] transition-colors hover:bg-white/25"
              >
                <span className="hidden text-right leading-tight sm:block">
                  <span className="block font-medium">{user.display_name}</span>
                  <span className="label text-[10px] text-white/75">
                    {fr.nav.roles[user.role as keyof typeof fr.nav.roles] ?? user.role}
                  </span>
                </span>
                <span className="grid size-8 place-items-center rounded-full bg-white text-ink">
                  <LogOut className="size-4" aria-label={fr.nav.logout} />
                </span>
              </button>
            )}
          </div>
        </div>
      </header>
      <main className="relative mx-auto -mt-36 max-w-[1320px] px-4 pb-24 sm:px-8">
        <Outlet />
      </main>
      <Copilot />
    </div>
  )
}
