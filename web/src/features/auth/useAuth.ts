import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import { clearTokens, getRefreshToken, isLoggedIn } from '@/lib/auth'

export const meQueryKey = ['auth', 'me'] as const

async function fetchMe() {
  const { data, error } = await apiClient.GET('/api/v1/auth/me')
  if (error) throw error
  return data
}

/** Tell the server to revoke the refresh token before dropping our copy.
 *
 * Clearing localStorage alone only makes *this browser* forget the token -
 * the token itself stays valid for its full lifetime, so anything that
 * captured it keeps working long after the user believes they signed out.
 * Best-effort by design: if the call fails we still sign out locally,
 * because refusing to log someone out because the network is down is worse
 * than a token that expires on its own schedule. */
async function revokeSession(): Promise<void> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return
  try {
    await apiClient.POST('/api/v1/auth/logout', {
      body: { refresh_token: refreshToken },
    })
  } catch {
    // Ignored - see above.
  }
}

/** `GET /auth/me`'s role and capability flags (§9.2), cached for the
 * session - a role change takes effect on next login, same as the access
 * token it's read from. */
export function useAuth() {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: meQueryKey,
    queryFn: fetchMe,
    enabled: isLoggedIn(),
    retry: false,
    staleTime: Infinity,
  })

  const logout = async () => {
    await revokeSession()
    clearTokens()
    queryClient.removeQueries({ queryKey: meQueryKey })
    window.location.assign('/login')
  }

  return {
    principal: query.data ?? null,
    isLoading: isLoggedIn() && query.isLoading,
    canViewSalary: query.data?.can_view_salary ?? false,
    canEdit: query.data?.can_edit ?? false,
    logout,
  }
}
