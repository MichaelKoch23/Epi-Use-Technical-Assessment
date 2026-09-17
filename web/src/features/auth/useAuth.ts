import { useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import { clearTokens, getRefreshToken, isLoggedIn } from '@/lib/auth'

export const meQueryKey = ['auth', 'me'] as const

async function fetchMe() {
  const { data, error } = await apiClient.GET('/api/v1/auth/me')
  if (error) throw error
  return data
}

async function revokeSession(): Promise<void> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return
  try {
    await apiClient.POST('/api/v1/auth/logout', {
      body: { refresh_token: refreshToken },
    })
  } catch {
  }
}

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
