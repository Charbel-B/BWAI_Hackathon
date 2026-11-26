import { ArrowLeft, Download } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { paths } from '@/app/paths'
import { Button } from '@/components/button'
import { ErrorView, Loading } from '@/components/state-views'
import { useInvoice } from '@/features/invoices/queries'
import { fr } from '@/i18n/fr'

import { PrintSheet } from './print-sheet'
import { useIssuer } from './use-issuer'

const t = fr.print

/** Facture imprimable : la feuille A4, et le bouton qui la transforme en PDF. */
export function PrintPage() {
  const { invoiceId = '' } = useParams()
  const invoice = useInvoice(invoiceId)
  const issuer = useIssuer()

  if (invoice.isPending || issuer.isPending) return <Loading />
  if (invoice.isError || issuer.isError) return <ErrorView message={fr.errors.generic} />

  return (
    <div className="min-h-dvh bg-mist py-8 print:bg-white print:py-0">
      <div className="no-print mx-auto mb-6 flex w-[210mm] max-w-full flex-wrap items-center justify-between gap-3 px-4">
        <Link
          to={paths.invoice(invoiceId)}
          className="inline-flex items-center gap-2 text-sm text-ink-soft hover:text-ink"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          {t.back}
        </Link>
        <div className="flex items-center gap-3">
          <span className="hidden text-xs text-ink-soft sm:inline">{t.hint}</span>
          <Button
            variant="primary"
            icon={<Download className="size-4" aria-hidden="true" />}
            onClick={() => window.print()}
          >
            {t.download}
          </Button>
        </div>
      </div>
      <PrintSheet invoice={invoice.data} issuer={issuer.data} />
    </div>
  )
}
