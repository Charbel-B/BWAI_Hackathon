import { CircleAlert, LoaderCircle } from 'lucide-react'
import type { ReactNode } from 'react'

import { fr } from '@/i18n/fr'

import { Button } from './button'

export function Loading() {
  return (
    <div role="status" className="flex items-center gap-3 py-24 text-ink-soft justify-center">
      <LoaderCircle className="size-5 animate-spin" aria-hidden="true" />
      {fr.common.loading}
    </div>
  )
}

export function ErrorView({
  message,
  onRetry,
  action,
}: {
  message: string
  onRetry?: () => void
  action?: ReactNode
}) {
  return (
    <div
      role="alert"
      className="mx-auto flex max-w-md flex-col items-center gap-4 py-24 text-center"
    >
      <span className="grid size-12 place-items-center rounded-2xl bg-coral-wash text-coral">
        <CircleAlert className="size-6" aria-hidden="true" />
      </span>
      <p className="text-ink">{message}</p>
      {onRetry && <Button onClick={onRetry}>{fr.common.retry}</Button>}
      {action}
    </div>
  )
}
