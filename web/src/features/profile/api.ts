import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { meQueryKey } from '@/features/auth/useAuth'
import { fileBody } from '@/features/employees/mutations'
import { apiClient } from '@/lib/apiClient'
import type { components } from '@/lib/api-types'
import { profileKeys } from '@/lib/queryKeys'

export type Profile = components['schemas']['ProfileResponse']
export type ProfilePerson = components['schemas']['ProfilePerson']

async function fetchProfile(): Promise<Profile> {
  const { data, error } = await apiClient.GET('/api/v1/profile')
  if (error) throw error
  return data
}

export function useProfile() {
  return useQuery({ queryKey: profileKeys.me(), queryFn: fetchProfile })
}

/** Upload (`file`) or remove (`null`) the signed-in account's own photo. */
export function useProfileAvatarMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (file: File | null) => {
      const { data, error } = file
        ? await apiClient.PUT('/api/v1/profile/avatar', fileBody(file))
        : await apiClient.DELETE('/api/v1/profile/avatar')
      if (error) throw error
      return data
    },
    onSuccess: (profile) => {
      queryClient.setQueryData(profileKeys.me(), profile)
      // The topbar avatar reads `/auth/me`. Employee photos are separate
      // records, so nothing else needs refetching.
      void queryClient.invalidateQueries({ queryKey: meQueryKey })
    },
  })
}
