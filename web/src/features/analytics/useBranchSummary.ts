import { useQuery } from '@tanstack/react-query'
import { analyticsKeys } from '@/lib/queryKeys'
import { fetchBranchSummary } from './api'

export function useBranchSummary(employeeId: string | null) {
  return useQuery({
    queryKey: analyticsKeys.branch(employeeId ?? ''),
    queryFn: () => fetchBranchSummary(employeeId!),
    enabled: employeeId !== null,
  })
}
