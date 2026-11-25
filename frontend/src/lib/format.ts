/**
 * Mise en forme pour l'affichage uniquement : aucun calcul. Les montants arrivent du backend
 * en chaînes décimales et sont regroupés par milliers sans passer par un nombre flottant.
 */
const THIN_SPACE = ' '

export function formatAmount(value: string): string {
  const negative = value.startsWith('-')
  const [whole = '0', decimals] = value.replace('-', '').split('.')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, THIN_SPACE)
  const trimmed = decimals !== undefined && /[1-9]/.test(decimals) ? `,${decimals}` : ''
  return `${negative ? '−' : ''}${grouped}${trimmed}`
}

export function formatRate(value: string): string {
  return `${formatAmount(value)}${THIN_SPACE}%`
}

const dateFormat = new Intl.DateTimeFormat('fr-FR', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})
const dateTimeFormat = new Intl.DateTimeFormat('fr-FR', {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})

export function formatDate(iso: string | null | undefined): string {
  return iso ? dateFormat.format(new Date(iso)) : '—'
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso))
}

export function percent(confidence: number): string {
  return `${Math.round(confidence * 100)}${THIN_SPACE}%`
}

/** Les identifiants d'utilisateur sont préfixés côté serveur ; on affiche le nom de compte. */
export function displayUser(id: string | null | undefined): string {
  return (id ?? '').replace(/^USR-/, '')
}
