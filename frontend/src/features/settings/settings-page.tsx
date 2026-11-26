import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { LogOut, Mail, MessageCircle, RotateCcw, Smartphone } from 'lucide-react'
import { useState } from 'react'

import { api } from '@/api/client'
import { unwrap } from '@/api/problem'
import { Button } from '@/components/button'
import { DemoBadge } from '@/components/demo-badge'
import { PageTitle } from '@/components/page-title'
import { session } from '@/features/auth/session'
import { useCurrentUser } from '@/features/auth/use-session'
import { fr } from '@/i18n/fr'
import { type Channel, CHANNELS, readPreferences, writePreferences } from '@/lib/preferences'

import { PasswordForm } from './password-form'
import { SettingsPanel } from './settings-panel'

const t = fr.settings
const ICONS = { whatsapp: MessageCircle, sms: Smartphone, email: Mail } as const

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-t border-line py-3 first:border-t-0">
      <dt className="text-sm text-ink-soft">{label}</dt>
      <dd
        className={`truncate text-right ${mono ? 'font-mono text-[13px]' : 'text-[15px] font-medium'}`}
      >
        {value}
      </dd>
    </div>
  )
}

/** Paramètres : profil, sécurité, préférences, système et démonstration. */
export function SettingsPage() {
  const user = useCurrentUser()
  const client = useQueryClient()
  const [channel, setChannel] = useState<Channel>(() => readPreferences().channel)
  const [confirming, setConfirming] = useState(false)
  const health = useQuery({
    queryKey: ['health'],
    queryFn: async () => unwrap(await api.GET('/api/v1/health')),
  })
  const reset = useMutation({
    mutationFn: async () => unwrap(await api.POST('/api/v1/admin/reset')),
    onSettled: () => {
      setConfirming(false)
      void client.invalidateQueries()
    },
  })

  if (user === null) return null
  const initials = user.display_name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')

  function choose(next: Channel) {
    setChannel(next)
    writePreferences({ channel: next })
  }

  return (
    <div className="grid gap-5">
      <div className="rounded-card bg-white px-6 pt-6 pb-5 shadow-card">
        <PageTitle light={t.titleLight} bold={t.titleBold} />
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <div className="grid gap-5">
          <SettingsPanel title={t.profile} index={0}>
            <div className="flex items-center gap-4">
              <span className="sky grid size-16 place-items-center rounded-[20px] text-xl font-semibold text-white shadow-float">
                {initials}
              </span>
              <div>
                <b className="block text-[19px] font-semibold">{user.display_name}</b>
                <span className="text-sm text-ink-soft">
                  {fr.nav.roles[user.role as keyof typeof fr.nav.roles] ?? user.role}
                </span>
              </div>
            </div>
            <dl>
              <Row label={t.username} value={user.username} mono />
              <Row label={t.userId} value={user.id} mono />
            </dl>
            <p className="rounded-xl bg-ice px-4 py-3 text-sm leading-relaxed text-ink-soft">
              {t.rights[user.role]}
            </p>
          </SettingsPanel>

          <SettingsPanel title={t.password} index={1} aside={<DemoBadge compact />}>
            <PasswordForm />
          </SettingsPanel>
        </div>

        <div className="grid gap-5">
          <SettingsPanel title={t.preferences} index={2}>
            <div
              role="radiogroup"
              aria-label={t.preferredChannel}
              className="grid gap-2 sm:grid-cols-3"
            >
              {CHANNELS.map((c) => {
                const Icon = ICONS[c]
                const on = channel === c
                return (
                  <button
                    key={c}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    onClick={() => choose(c)}
                    className={`flex items-center gap-2.5 rounded-2xl px-4 py-3.5 text-sm font-medium transition-[background,box-shadow,color] duration-200 ease-out ${on ? 'bg-sky-wash text-sky-deep shadow-[inset_0_0_0_1.5px_var(--color-sky)]' : 'bg-ice text-ink shadow-[inset_0_0_0_1px_var(--color-line)]'}`}
                  >
                    <Icon className="size-4" aria-hidden="true" />
                    {fr.invoice.channels[c]}
                  </button>
                )
              })}
            </div>
            <p className="text-xs text-ink-soft">{`${t.preferredChannel} · ${t.savedLocally}`}</p>
          </SettingsPanel>

          <SettingsPanel title={t.system} index={3}>
            {health.data && (
              <dl>
                <Row label={t.version} value={health.data.version} mono />
                <Row label={t.extractor} value={health.data.extractor} mono />
                <Row label={t.rulesHash} value={health.data.config_sha256.slice(0, 16)} mono />
              </dl>
            )}
            {health.data && (
              <div>
                <span className="label text-ink-soft">{t.simulatedList}</span>
                <ul className="mt-2 flex flex-wrap gap-2">
                  {health.data.simulated.map((item) => (
                    <li
                      key={item}
                      className="rounded-full bg-ice px-3 py-1.5 text-xs text-ink-soft"
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </SettingsPanel>

          {user.role === 'ADMIN' && (
            <SettingsPanel title={t.demo} index={4}>
              <p className="text-sm leading-relaxed text-ink-soft">{t.resetText}</p>
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  variant={confirming ? 'primary' : 'ghost'}
                  icon={<RotateCcw className="size-4" aria-hidden="true" />}
                  pending={reset.isPending}
                  onClick={() => (confirming ? reset.mutate() : setConfirming(true))}
                >
                  {confirming ? t.resetConfirm : t.reset}
                </Button>
                {reset.isSuccess && (
                  <span role="status" className="text-sm text-sky-deep">
                    {t.resetDone}
                  </span>
                )}
              </div>
            </SettingsPanel>
          )}

          <SettingsPanel title={t.session} index={5}>
            <Button
              variant="ghost"
              icon={<LogOut className="size-4" aria-hidden="true" />}
              onClick={session.clear}
              className="justify-self-start"
            >
              {t.logout}
            </Button>
          </SettingsPanel>
        </div>
      </div>
    </div>
  )
}
