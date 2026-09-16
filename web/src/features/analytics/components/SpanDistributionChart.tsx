import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import type { OrgSummary } from '../types'

const HEALTHY_MIN = 3
const HEALTHY_MAX = 10

function isHealthy(directReports: number): boolean {
  return directReports >= HEALTHY_MIN && directReports <= HEALTHY_MAX
}

/** Single-series horizontal bars built from the style guide's
 * `sp-bar-track`/`sp-bar-fill` pattern (§ analytics charts) — no charting
 * library, so the bundle stays small and the colours stay exactly on
 * brand. Bars outside the healthy range get the alert token *and* a
 * label, since colour alone never carries the meaning. */
export function SpanDistributionChart({
  data,
  isPending,
}: {
  data: OrgSummary['span_distribution'] | undefined
  isPending: boolean
}) {
  if (isPending || !data) {
    return (
      <section aria-hidden="true" className="rounded-md border border-border bg-card px-5 py-4">
        <Skeleton className="mb-4 h-4 w-56" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-5 w-full" />
          ))}
        </div>
      </section>
    )
  }

  const maxCount = Math.max(1, ...data.map((row) => row.manager_count))
  const totalEmployees = data.reduce((sum, row) => sum + row.manager_count, 0)

  return (
    <section
      aria-labelledby="span-distribution-heading"
      className="rounded-md border border-border bg-card px-5 py-4"
    >
      <h2 id="span-distribution-heading" className="font-display text-sm font-bold text-brand-primary">
        Span of control distribution
      </h2>
      <p className="mb-4 text-xs text-muted-foreground">
        How many employees have how many direct reports. The healthy range is{' '}
        {HEALTHY_MIN}–{HEALTHY_MAX} direct reports; bars outside it are flagged.
      </p>

      <div
        role="img"
        aria-label={`Span of control distribution across ${totalEmployees} employees. Bars outside the healthy range of ${HEALTHY_MIN} to ${HEALTHY_MAX} direct reports are marked out of range.`}
        className="space-y-1.5"
      >
        {data.map((row) => {
          const healthy = isHealthy(row.direct_reports)
          return (
            <div key={row.direct_reports} className="grid grid-cols-[6rem_1fr_3.5rem] items-center gap-3">
              <span className="text-xs text-muted-foreground">
                {row.direct_reports} report{row.direct_reports === 1 ? '' : 's'}
              </span>
              <div className="h-4 rounded-sm bg-muted">
                <div
                  data-testid={`span-bar-fill-${row.direct_reports}`}
                  className={cn(
                    'h-full rounded-sm',
                    healthy ? 'bg-brand-steel' : 'bg-status-alert'
                  )}
                  style={{ width: `${(row.manager_count / maxCount) * 100}%` }}
                />
              </div>
              <span className="type-numeric text-right text-xs tabular-nums text-muted-foreground">
                {row.manager_count}
                {!healthy && <span className="sr-only"> (out of healthy range)</span>}
              </span>
            </div>
          )
        })}
      </div>

      <table className="sr-only">
        <caption>Number of employees by direct-report count</caption>
        <thead>
          <tr>
            <th scope="col">Direct reports</th>
            <th scope="col">Employees</th>
            <th scope="col">In healthy range (3–10)</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.direct_reports}>
              <td>{row.direct_reports}</td>
              <td>{row.manager_count}</td>
              <td>{isHealthy(row.direct_reports) ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
