import { Navigate, Outlet, useLocation } from 'react-router'

import { useCurrentUser } from './use-session'

/** Les écrans de l'application exigent une session ; sinon, retour à la connexion. */
export function RequireAuth() {
  const user = useCurrentUser()
  const location = useLocation()
  if (user === null) return <Navigate to="/connexion" replace state={{ from: location.pathname }} />
  return <Outlet />
}
