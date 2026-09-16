import { useQuery } from '@tanstack/react-query'
import { ChevronRightIcon } from 'lucide-react'
import { apiClient, getActorId } from '@/lib/apiClient'
import { employeeKeys } from '@/lib/queryKeys'

async function fetchReportingLine(id: string) {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}/reporting-line', {
    params: { path: { employee_id: id }, header: { 'X-Actor-Id': getActorId() ?? '' } },
  })
  if (error) throw error
  return data
}

/** `/employees/{id}/reporting-line`, rendered root-first as a breadcrumb —
 * the ancestor chain above a selected employee. Also used as the "expand
 * ancestors" data source for search and focus mode. */
export function ReportingLineBreadcrumb({
  employeeId,
  employeeName,
  onSelect,
}: {
  employeeId: string
  employeeName: string
  onSelect: (id: string) => void
}) {
  const { data } = useQuery({
    queryKey: employeeKeys.reportingLine(employeeId),
    queryFn: () => fetchReportingLine(employeeId),
  })

  const ancestors = data ? [...data].reverse() : []

  return (
    <nav
      aria-label="Reporting line"
      className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground"
    >
      {ancestors.map(({ employee }) => (
        <span key={employee.id} className="flex items-center gap-1.5">
          <button
            type="button"
            className="font-medium text-brand-mid hover:underline"
            onClick={() => onSelect(employee.id)}
          >
            {employee.first_name} {employee.last_name}
          </button>
          <ChevronRightIcon className="size-3" aria-hidden="true" />
        </span>
      ))}
      <span aria-current="page" className="font-semibold text-brand-primary">
        {employeeName}
      </span>
    </nav>
  )
}
