import { useSyncExternalStore } from 'react'

import { session } from './session'

/** Utilisateur connecté, ou null ; le composant se met à jour à la connexion et à la sortie. */
export function useCurrentUser() {
  return useSyncExternalStore(session.subscribe, session.user, session.user)
}
