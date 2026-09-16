import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { globalAuditKeys } from '@/lib/queryKeys'
import { fetchGlobalAuditLog } from './api'

export function useGlobalAuditLog(page: number) {
  return useQuery({
    queryKey: globalAuditKeys.page(page),
    queryFn: () => fetchGlobalAuditLog(page),
    placeholderData: keepPreviousData,
  })
}
