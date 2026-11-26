import { useQuery } from '@tanstack/react-query'
import { ShieldAlert, ShieldCheck, ShieldQuestion, ShieldX } from 'lucide-react'
import { useParams, useSearchParams } from 'react-router'

import { api } from '@/api/client'
import { unwrap } from '@/api/problem'
import shieldImage from '@/assets/bouclier-qr-verre.webp'
import { Logo } from '@/components/logo'
import { Money } from '@/components/money'
import { Loading } from '@/components/state-views'
import { fr } from '@/i18n/fr'
import { formatDate, formatDateTime } from '@/lib/format'

const t = fr.verify

const TONES = {
  AUTHENTIC: { Icon: ShieldCheck, badge: 'bg-lime text-lime-ink' },
  CANCELLED: { Icon: ShieldAlert, badge: 'bg-amber text-amber-deep' },
  ALTERED: { Icon: ShieldX, badge: 'bg-coral text-white' },
  UNKNOWN: { Icon: ShieldQuestion, badge: 'bg-mist text-ink-soft' },
} as const

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-t border-line py-3 first:border-t-0">
      <dt className="text-sm text-ink-soft">{label}</dt>
      <dd className="text-right text-[15px] font-medium">{children}</dd>
    </div>
  )
}

/** Page publique ouverte par le QR code : aucune connexion, le strict nécessaire. */
export function VerificationPage() {
  const { invoiceId = '' } = useParams()
  const [params] = useSearchParams()
  const code = params.get('code') ?? ''
  const result = useQuery({
    queryKey: ['verify', invoiceId, code],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/public/verify/{invoice_id}', {
          params: { path: { invoice_id: invoiceId }, query: { code } },
        }),
      ),
  })

  const verdict = (result.data?.verdict ?? 'UNKNOWN') as keyof typeof TONES
  const tone = TONES[verdict] ?? TONES.UNKNOWN
  const copy = t.verdicts[verdict] ?? t.verdicts['UNKNOWN']!
  const data = result.data

  return (
    <div className="sky-band min-h-dvh px-4 py-6 sm:py-10">
      <div className="mx-auto flex max-w-[560px] items-center justify-between">
        <Logo />
        <span className="label text-white/80">{t.pageTitle}</span>
      </div>
      <main className="mx-auto mt-10 max-w-[560px]">
        <div className="relative rounded-[32px] bg-white px-6 pt-28 pb-7 shadow-card sm:px-8">
          <img
            src={shieldImage}
            alt=""
            className="float absolute -top-16 left-1/2 w-[150px] -translate-x-1/2 drop-shadow-[var(--shadow-object)]"
          />
          {result.isPending ? (
            <Loading />
          ) : (
            <div className="enter grid gap-6">
              <div className="text-center">
                <span
                  className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold ${tone.badge}`}
                >
                  <tone.Icon className="size-4" aria-hidden="true" />
                  {copy.title}
                </span>
                <p className="mx-auto mt-3 max-w-[40ch] text-[15px] leading-relaxed text-ink-soft">
                  {copy.text}
                </p>
              </div>
              {data?.number && (
                <dl>
                  <Row label={t.number}>
                    <span className="tabular">{data.number}</span>
                  </Row>
                  {data.customer_name && <Row label={t.customer}>{data.customer_name}</Row>}
                  {data.issue_date && <Row label={t.date}>{formatDate(data.issue_date)}</Row>}
                  {data.gross_total && (
                    <Row label={t.total}>
                      <Money value={data.gross_total} /> {fr.totals.currency}
                    </Row>
                  )}
                  {data.validated_at && (
                    <Row label={t.validatedAt}>{formatDateTime(data.validated_at)}</Row>
                  )}
                  <Row label={t.journal}>{data.journal_intact ? t.journalOk : t.journalKo}</Row>
                </dl>
              )}
              {data?.content_sha256 && (
                <div className="rounded-2xl bg-ice px-4 py-3">
                  <span className="label text-ink-soft">{t.fingerprint}</span>
                  <p className="mt-1 font-mono text-[11px] leading-relaxed break-all text-ink-soft">
                    {data.content_sha256}
                  </p>
                </div>
              )}
              <p className="text-center text-xs leading-relaxed text-ink-soft">{t.how}</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
