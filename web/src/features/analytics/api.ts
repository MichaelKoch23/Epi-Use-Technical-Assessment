import { apiClient } from '@/lib/apiClient'
import { getErrorMessage } from '@/lib/apiError'
import type { BranchSummary, OrgSummary } from './types'

export async function fetchOrgSummary(): Promise<OrgSummary> {
  const { data, error } = await apiClient.GET('/api/v1/analytics/org-summary')
  if (error) throw new Error(getErrorMessage(error, 'Failed to load organisation analytics'))
  return data
}

export async function fetchBranchSummary(employeeId: string): Promise<BranchSummary> {
  const { data, error } = await apiClient.GET('/api/v1/analytics/branch/{employee_id}', {
    params: { path: { employee_id: employeeId } },
  })
  if (error) throw new Error(getErrorMessage(error, 'Failed to load branch analytics'))
  return data
}
