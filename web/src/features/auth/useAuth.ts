import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import { clearTokens, isLoggedIn } from '@/lib/auth'

export const meQueryKey = ['auth', 'me'] as const

async function fetchMe() {
  const { data, error } = await apiClient.GET('/api/v1/auth/me')
  if (error) throw error
  return data
}

/** `GET /auth/me`'s role and capability flags (§9.2), cached for the
 * session — a role change takes effect on next login, same as the access
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

  const logout = () => {
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
