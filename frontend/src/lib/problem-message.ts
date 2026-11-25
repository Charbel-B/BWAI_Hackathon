import { ApiProblem } from '@/api/problem'
import { fr } from '@/i18n/fr'

/** Message lisible pour une erreur d'action ; le détail du serveur sert pour les règles métier. */
export function problemMessage(error: unknown): string {
  if (!(error instanceof ApiProblem)) return fr.errors.generic
  const known = fr.errors[error.code as keyof typeof fr.errors]
  if (typeof known === 'string') return known
  return error.code === 'INVALID_INPUT' ? error.message : fr.errors.generic
}
