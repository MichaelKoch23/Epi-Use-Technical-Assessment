import { useQuery } from '@tanstack/react-query'
import { analyticsKeys } from '@/lib/queryKeys'
import { fetchOrgSummary } from './api'

export function useOrgSummary() {
  return useQuery({
    queryKey: analyticsKeys.orgSummary(),
    queryFn: fetchOrgSummary,
    staleTime: 60_000,
  })
}
