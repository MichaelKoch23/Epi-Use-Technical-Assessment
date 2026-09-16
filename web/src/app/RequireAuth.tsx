import { Navigate, Outlet, useLocation } from 'react-router'
import { isLoggedIn } from '@/lib/auth'

/** Route guard for everything behind the app shell - no access token, no
 * app. The interceptor in `apiClient.ts` handles the reverse case (a
 * token that's since gone bad) by redirecting here on a failed refresh. */
export function RequireAuth() {
  const location = useLocation()
  if (!isLoggedIn()) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    )
  }
  return <Outlet />
}
