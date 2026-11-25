import type { Anomaly, ExtractedField } from '@/api/types'
import { fr } from '@/i18n/fr'

export type FieldState = 'sure' | 'unsure' | 'missing' | 'absent' | 'corrected' | 'confirmed'

const LINE = /^lines\[(\d+)\]\.(\w+)$/

/**
 * État affiché d'un champ. « Incertain » et « absent obligatoire » viennent des anomalies calculées
 * par le backend : ni le seuil de confiance ni la liste des champs obligatoires ne sont recopiés ici.
 */
export function fieldState(field: ExtractedField, anomalies: readonly Anomaly[]): FieldState {
  if (field.review.state === 'CORRECTED') return 'corrected'
  if (field.review.state === 'CONFIRMED') return 'confirmed'
  const flagged = (code: string) =>
    anomalies.some((a) => a.code === code && a.field === field.name && !a.resolved)
  if (field.status === 'MISSING' || field.effective_value === null) {
    return flagged('MISSING_REQUIRED_FIELD') ? 'missing' : 'absent'
  }
  return flagged('LOW_CONFIDENCE') || field.status === 'AMBIGUOUS' ? 'unsure' : 'sure'
}

export function fieldLabel(name: string): { label: string; line: number | null } {
  const match = LINE.exec(name)
  if (match) {
    const [, index = '0', attr = ''] = match
    return { label: fr.review.lineAttrs[attr] ?? attr, line: Number(index) + 1 }
  }
  return { label: fr.review.fieldNames[name] ?? name, line: null }
}

/** En-tête d'abord, puis les lignes dans l'ordre, puis les totaux lus. */
export function sortFields(fields: readonly ExtractedField[]): ExtractedField[] {
  const rank = (name: string): number => {
    if (name.startsWith('customer.')) return 0
    if (name.startsWith('document.')) return 1
    if (name.startsWith('payment.') || name.startsWith('discount.')) return 2
    const line = LINE.exec(name)
    if (line) return 10 + Number(line[1])
    return 1000
  }
  return [...fields].sort((a, b) => rank(a.name) - rank(b.name))
}

/** Message d'une anomalie, avec le nom lisible du champ quand elle en vise un. */
export function anomalyText(code: string, field: string | null, fallback: string): string {
  if (field === null) return fallback
  const { label, line } = fieldLabel(field)
  const name = line === null ? label : `${label} · ${fr.review.line(line)}`
  if (code === 'LOW_CONFIDENCE') return fr.review.anomalyUnsure(name)
  if (code === 'MISSING_REQUIRED_FIELD') return fr.review.anomalyMissing(name)
  return fallback
}
