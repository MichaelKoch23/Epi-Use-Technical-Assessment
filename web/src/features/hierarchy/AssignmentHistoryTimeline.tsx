import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDate } from '@/features/employees/format'
import { employeeKeys } from '@/lib/queryKeys'
import { fetchAssignmentHistory, type AssignmentHistoryItem } from './api'

const COLLAPSED_COUNT = 4

function dateRange(row: AssignmentHistoryItem): string {
  const from = formatDate(row.valid_from)
  return row.valid_to ? `${from} - ${formatDate(row.valid_to)}` : `${from} - present`
}

export function AssignmentHistoryTimeline({ employeeId }: { employeeId: string }) {
  const [expanded, setExpanded] = useState(false)
  const query = useQuery({
    queryKey: employeeKeys.assignmentHistory(employeeId),
    queryFn: () => fetchAssignmentHistory(employeeId),
  })

  const items = query.data ?? []
  const visible = expanded ? items : items.slice(0, COLLAPSED_COUNT)

  return (
    <section aria-label="Reporting history" className="flex flex-col gap-2">
      <h2 className="font-display text-sm font-bold text-brand-primary">Reporting history</h2>

      {query.isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : query.isError ? (
        <p className="text-sm text-muted-foreground">Could not load the reporting history.</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No reporting history recorded yet.</p>
      ) : (
        <>
          <ul>
            {visible.map((row) => (
              <li
                key={row.id}
                className="flex flex-col gap-1 border-b border-border py-2.5 last:border-none"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold">
                    {row.manager_name ?? 'No manager'}
                  </span>
                  {row.scheduled ? (
                    <Badge className="bg-brand-teal/15 text-brand-teal">Scheduled</Badge>
                  ) : row.in_force ? (
                    <Badge variant="secondary">Current</Badge>
                  ) : null}
                </div>
                <div className="text-xs text-muted-foreground">{dateRange(row)}</div>
                {row.reason && <div className="text-sm">{row.reason}</div>}
                {row.created_by_email && (
                  <div className="text-xs text-muted-foreground">
                    Set by {row.created_by_email}
                  </div>
                )}
              </li>
            ))}
          </ul>
          {items.length > COLLAPSED_COUNT && (
            <button
              type="button"
              className="self-start text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setExpanded((prev) => !prev)}
            >
              {expanded ? 'Show fewer' : `Show all ${items.length}`}
            </button>
          )}
        </>
      )}
    </section>
  )
}
