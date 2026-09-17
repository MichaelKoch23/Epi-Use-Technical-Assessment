import { useState } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { AuditEntry } from '@/features/employees/AuditTimeline'
import { getErrorMessage } from '@/lib/apiError'
import { useGlobalAuditLog } from './useGlobalAuditLog'

export function GlobalAuditPage() {
  const [page, setPage] = useState(1)
  const query = useGlobalAuditLog(page)

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-bold">Change history</h1>
        <p className="text-muted-foreground">Every recorded change, across every employee.</p>
      </div>

      <section aria-label="Change history" className="rounded-md border border-border bg-card px-5 py-2">
        {query.isPending ? (
          <div className="flex flex-col gap-2 py-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : query.isError ? (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <p className="text-sm font-medium text-foreground">
              {getErrorMessage(query.error, 'Failed to load change history')}
            </p>
            <p className="text-sm text-muted-foreground">Nothing was changed.</p>
            <button
              type="button"
              className="text-sm font-medium text-brand-mid underline-offset-2 hover:underline"
              onClick={() => query.refetch()}
            >
              Retry
            </button>
          </div>
        ) : query.data.items.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            No changes recorded yet.
          </p>
        ) : (
          <ul>
            {query.data.items.map((entry) => (
              <AuditEntry
                key={entry.id}
                entry={entry}
                employeeName={entry.employee_name}
                employeeId={entry.employee_id}
              />
            ))}
          </ul>
        )}

        {query.data && query.data.total > query.data.page_size && (
          <div className="flex items-center justify-end gap-3 py-3 text-sm">
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground disabled:opacity-40"
              disabled={page * query.data.page_size >= query.data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        )}
      </section>
    </div>
  )
}
