import { fr } from '@/i18n/fr'

import { useHealth } from './use-health'

export function HealthStatus() {
  const health = useHealth()
  if (health.isPending) return <p role="status">{fr.health.loading}</p>
  if (health.isError) return <p role="alert">{fr.health.error}</p>
  return <p role="status">{fr.health.ok}</p>
}
