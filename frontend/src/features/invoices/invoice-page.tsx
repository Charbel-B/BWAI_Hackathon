import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { ApiProblem } from '@/api/problem'
import { ErrorView, Loading } from '@/components/state-views'
import { ReviewPage } from '@/features/review/review-page'
import { fr } from '@/i18n/fr'

import { IssuedInvoice } from './issued-invoice'
import { useInvoice } from './queries'

/** Une facture : en revue tant qu'elle est en brouillon, puis sa vie après validation. */
export function InvoicePage() {
  const { invoiceId = '' } = useParams()
  const invoice = useInvoice(invoiceId)

  if (invoice.isPending) return <Loading />
  if (invoice.isError) {
    const missing = invoice.error instanceof ApiProblem && invoice.error.status === 404
    return (
      <ErrorView
        message={missing ? fr.errors.notFound : fr.errors.generic}
        {...(missing ? {} : { onRetry: () => void invoice.refetch() })}
        action={
          <Link to="/" className="text-sm underline underline-offset-4">
            {fr.errors.back}
          </Link>
        }
      />
    )
  }
  return (
    <div className="grid gap-4">
      <Link
        to="/"
        className="inline-flex w-max items-center gap-2 rounded-full bg-white/20 px-3.5 py-2 text-sm text-white backdrop-blur-md transition-colors hover:bg-white/30"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        {fr.errors.back}
      </Link>
      {invoice.data.status === 'DRAFT' ? (
        <ReviewPage invoice={invoice.data} />
      ) : (
        <IssuedInvoice invoice={invoice.data} />
      )}
    </div>
  )
}
