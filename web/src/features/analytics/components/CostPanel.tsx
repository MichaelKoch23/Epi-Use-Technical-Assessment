import { LockIcon } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency } from '@/features/employees/format'
import type { CostSummary } from '../types'

/** Admin-only cost roll-up (§9.3). For a viewer `cost` is never present on
 * the response at all — this panel still renders, with the `.salary-locked`
 * treatment, so the viewer knows the data exists and that they can't see
 * it, rather than the panel silently disappearing. */
export function CostPanel({
  cost,
  restricted,
  isPending,
}: {
  cost: CostSummary | undefined
  restricted: boolean
  isPending: boolean
}) {
  return (
    <section aria-labelledby="cost-panel-heading" className="rounded-md border border-border bg-card px-5 py-4">
      <h2 id="cost-panel-heading" className="font-display mb-3 text-sm font-bold text-brand-primary">
        Cost
      </h2>

      {isPending ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i}>
              <Skeleton className="mb-2 h-3 w-24" />
              <Skeleton className="h-7 w-28" />
            </div>
          ))}
        </div>
      ) : restricted || !cost ? (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground italic">
          <LockIcon className="size-3.5" aria-hidden="true" />
          Restricted — the annual cost roll-up requires HR admin access
        </span>
      ) : (
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-muted-foreground">Total annual</dt>
            <dd className="type-numeric text-xl font-bold text-brand-primary tabular-nums">
              {formatCurrency(cost.total_annual, cost.currency)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Average</dt>
            <dd className="type-numeric text-xl font-bold text-brand-primary tabular-nums">
              {formatCurrency(cost.average, cost.currency)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Median</dt>
            <dd className="type-numeric text-xl font-bold text-brand-primary tabular-nums">
              {formatCurrency(cost.median, cost.currency)}
            </dd>
          </div>
        </dl>
      )}
    </section>
  )
}
