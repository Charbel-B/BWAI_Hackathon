import { useQuery } from '@tanstack/react-query'
import { ShieldAlert, ShieldCheck } from 'lucide-react'

import { api } from '@/api/client'
import { ApiProblem, unwrap } from '@/api/problem'
import { PageTitle } from '@/components/page-title'
import { ErrorView, Loading } from '@/components/state-views'
import { fr } from '@/i18n/fr'
import { displayUser, formatDateTime } from '@/lib/format'

const t = fr.audit

/** Journal d'audit en ajout seul, avec la vérification de sa chaîne d'empreintes. */
export function AuditPage() {
  const entries = useQuery({
    queryKey: ['audit', 'all'],
    queryFn: async () => unwrap(await api.GET('/api/v1/audit-log')),
  })
  const verify = useQuery({
    queryKey: ['audit', 'verify'],
    queryFn: async () => unwrap(await api.GET('/api/v1/audit-log/verify')),
  })

  if (entries.isPending) return <Loading />
  if (entries.isError) {
    const forbidden = entries.error instanceof ApiProblem && entries.error.status === 403
    return <ErrorView message={forbidden ? fr.errors.FORBIDDEN : fr.errors.generic} />
  }

  const intact = verify.data?.intact ?? true
  return (
    <div className="grid gap-5 rounded-card bg-white p-6 shadow-card sm:p-8">
      <PageTitle light={t.titleLight} bold={t.titleBold}>
        {verify.data && (
          <span
            className={`inline-flex items-center gap-2.5 rounded-full px-4 py-2.5 text-sm font-medium ${intact ? 'bg-night text-white' : 'bg-coral text-white'}`}
          >
            {intact ? (
              <ShieldCheck className="size-4 text-lime" aria-hidden="true" />
            ) : (
              <ShieldAlert className="size-4" aria-hidden="true" />
            )}
            {intact ? t.intact(verify.data.entries) : t.broken(verify.data.first_broken_seq ?? 0)}
          </span>
        )}
      </PageTitle>
      <p className="max-w-[66ch] text-[15px] leading-relaxed text-ink-soft">{t.lead}</p>
      {entries.data.length === 0 ? (
        <p className="text-ink-soft">{t.empty}</p>
      ) : (
        <ol className="grid">
          {[...entries.data].reverse().map((entry) => (
            <li
              key={entry.seq}
              className="grid grid-cols-[56px_1fr_auto] items-baseline gap-4 border-t border-line py-3.5 first:border-t-0"
            >
              <span className="tabular text-xs text-ink-soft">{`#${entry.seq}`}</span>
              <span className="min-w-0">
                <span className="text-[15px] font-medium">
                  {t.actions[entry.action] ?? entry.action}
                </span>
                <span className="ml-2 font-mono text-xs text-ink-soft">{`${displayUser(entry.user_id)} · ${entry.entity_id}`}</span>
                <span
                  className="block truncate font-mono text-[11px] text-ink-soft/70"
                  title={entry.hash}
                >
                  {entry.hash}
                </span>
              </span>
              <span className="text-right text-xs whitespace-nowrap text-ink-soft">
                {formatDateTime(entry.at)}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
