import { useQuery } from '@tanstack/react-query'
import { ChevronRightIcon } from 'lucide-react'
import { apiClient } from '@/lib/apiClient'
import { employeeKeys } from '@/lib/queryKeys'

async function fetchReportingLine(id: string, asOf: string) {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}/reporting-line', {
    params: { path: { employee_id: id }, query: { as_of: asOf } },
  })
  if (error) throw error
  return data.items
}

export function ReportingLineBreadcrumb({
  employeeId,
  employeeName,
  asOf,
  onSelect,
}: {
  employeeId: string
  employeeName: string
  asOf: string
  onSelect: (id: string) => void
}) {
  const { data } = useQuery({
    queryKey: employeeKeys.reportingLine(employeeId, asOf),
    queryFn: () => fetchReportingLine(employeeId, asOf),
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
