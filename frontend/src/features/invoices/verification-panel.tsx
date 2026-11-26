import { ExternalLink } from 'lucide-react'
import { Link } from 'react-router'

import type { Invoice } from '@/api/types'
import { paths } from '@/app/paths'
import { QrCode } from '@/components/qr-code'
import { fr } from '@/i18n/fr'

const t = fr.verify

/** QR code de vérification d'une facture validée. */
export function VerificationPanel({ invoice }: { invoice: Invoice }) {
  if (!invoice.verification_code) return null
  const path = paths.verify(invoice.id, invoice.verification_code)
  return (
    <section className="grid gap-4 rounded-card bg-white p-6 shadow-card sm:grid-cols-[150px_1fr] sm:items-center">
      <QrCode
        value={`${window.location.origin}${path}`}
        label={t.open}
        className="w-full max-w-[150px] justify-self-center"
      />
      <div className="grid gap-3">
        <h2 className="text-[22px]">{t.panelTitle}</h2>
        <p className="text-sm leading-relaxed text-ink-soft">{t.panelText}</p>
        <span className="font-mono text-xs text-ink-soft">{`${t.code} · ${invoice.verification_code}`}</span>
        <Link
          to={path}
          target="_blank"
          className="inline-flex w-max items-center gap-2 text-sm font-medium text-sky-deep underline underline-offset-4"
        >
          {t.open}
          <ExternalLink className="size-3.5" aria-hidden="true" />
        </Link>
      </div>
    </section>
  )
}
