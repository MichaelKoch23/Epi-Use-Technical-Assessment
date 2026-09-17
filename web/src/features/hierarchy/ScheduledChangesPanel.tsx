import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarClockIcon, XIcon } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDate } from '@/features/employees/format'
import { getErrorMessage } from '@/lib/apiError'
import { employeeKeys, hierarchyKeys } from '@/lib/queryKeys'
import { cancelScheduled, fetchScheduled } from './api'
import type { AsOfState } from './useAsOf'

export function ScheduledChangesPanel({
  state,
  canEdit,
}: {
  state: AsOfState
  canEdit: boolean
}) {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: hierarchyKeys.scheduled(),
    queryFn: fetchScheduled,
    staleTime: 60_000,
  })

  const cancelMutation = useMutation({
    mutationFn: cancelScheduled,
    onSuccess: (_data, assignmentId) => {
      const row = query.data?.find((item) => item.id === assignmentId)
      void queryClient.invalidateQueries({ queryKey: hierarchyKeys.all })
      if (row) {
        void queryClient.invalidateQueries({
          queryKey: employeeKeys.assignmentHistory(row.employee_id),
        })
      }
      toast.success('Scheduled change cancelled')
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Failed to cancel the scheduled change'))
    },
  })

  return (
    <section
      aria-labelledby="scheduled-changes-heading"
      className="rounded-md border border-border bg-card px-4 py-3 print:hidden"
    >
      <h2
        id="scheduled-changes-heading"
        className="font-display mb-2 flex items-center gap-1.5 text-sm font-bold text-brand-primary"
      >
        <CalendarClockIcon className="size-4" aria-hidden="true" />
        Scheduled changes
      </h2>

      {query.isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : query.isError ? (
        <p className="text-sm text-muted-foreground">Could not load scheduled changes.</p>
      ) : query.data.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No changes are scheduled. Set an effective date when reassigning someone to plan a
          move ahead of time.
        </p>
      ) : (
        <ul className="flex flex-col">
          {query.data.map((row) => (
            <li
              key={row.id}
              className="flex flex-wrap items-center justify-between gap-2 border-b border-border py-2 last:border-none"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-baseline gap-2 text-sm">
                  <button
                    type="button"
                    className="font-medium text-depth-4 underline underline-offset-2"
                    onClick={() => state.setAsOf(row.effective_from)}
                  >
                    {formatDate(row.effective_from)}
                  </button>
                  <span className="font-medium">{row.employee_name}</span>
                  <span className="text-muted-foreground">
                    &rarr; {row.manager_name ?? 'No manager'}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {row.employee_position}
                  {row.reason && <> &middot; {row.reason}</>}
                  {row.created_by_email && <> &middot; set by {row.created_by_email}</>}
                </div>
              </div>
              {canEdit && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={cancelMutation.isPending}
                  onClick={() => cancelMutation.mutate(row.id)}
                >
                  <XIcon className="size-3.5" aria-hidden="true" /> Cancel
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
