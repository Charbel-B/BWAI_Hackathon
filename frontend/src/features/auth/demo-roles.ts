/** Comptes de démonstration, dans l'ordre d'affichage (config/utilisateurs.yaml). */
export const ROLES = ['operateur', 'validateur', 'admin'] as const
export type DemoRole = (typeof ROLES)[number]

export function asDemoRole(username: string): DemoRole | null {
  return (ROLES as readonly string[]).includes(username) ? (username as DemoRole) : null
}
