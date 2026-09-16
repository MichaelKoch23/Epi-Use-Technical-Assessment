import { useQuery } from '@tanstack/react-query'
import { analyticsKeys } from '@/lib/queryKeys'
import { fetchOrgSummary } from './api'

export function useOrgSummary() {
  return useQuery({
    queryKey: analyticsKeys.orgSummary(),
    queryFn: fetchOrgSummary,
    // Matches the server's own 60-second cache (§ analytics) — refetching
    // sooner would only ever re-read the same cached figures.
    staleTime: 60_000,
  })
}
