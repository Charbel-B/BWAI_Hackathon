import { formatAmount } from '@/lib/format'

/** Montant tel que renvoyé par le backend, en chiffres à chasse fixe. Aucun calcul ici. */
export function Money({ value, className = '' }: { value: string; className?: string }) {
  return <span className={`tabular whitespace-nowrap ${className}`}>{formatAmount(value)}</span>
}
