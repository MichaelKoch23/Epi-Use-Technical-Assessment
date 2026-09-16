import { apiClient } from '@/lib/apiClient'
import { getErrorMessage } from '@/lib/apiError'

export async function fetchGlobalAuditLog(page: number) {
  const { data, error } = await apiClient.GET('/api/v1/audit', { params: { query: { page } } })
  if (error) throw new Error(getErrorMessage(error, 'Failed to load change history'))
  return data
}
