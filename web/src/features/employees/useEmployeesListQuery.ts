import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getActorId, apiClient } from '@/lib/apiClient'
import { getErrorMessage } from '@/lib/apiError'
import { employeeKeys, type EmployeeListFilters } from '@/lib/queryKeys'

async function fetchEmployees(filters: EmployeeListFilters) {
  const { data, error } = await apiClient.GET('/api/v1/employees', {
    params: {
      query: filters,
      header: { 'X-Actor-Id': getActorId() ?? '' },
    },
  })
  if (error) throw new Error(getErrorMessage(error, 'Failed to load employees'))
  return data
}

export function useEmployeesListQuery(filters: EmployeeListFilters) {
  return useQuery({
    queryKey: employeeKeys.list(filters),
    queryFn: () => fetchEmployees(filters),
    placeholderData: keepPreviousData,
  })
}
