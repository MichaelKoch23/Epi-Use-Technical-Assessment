import { apiClient } from '@/lib/apiClient'
import { getErrorMessage } from '@/lib/apiError'

export async function searchAll(q: string) {
  const { data, error } = await apiClient.GET('/api/v1/search', { params: { query: { q } } })
  if (error) throw new Error(getErrorMessage(error, 'Search failed'))
  return data
}
