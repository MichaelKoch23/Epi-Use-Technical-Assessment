import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { DEEP_CHAIN_THRESHOLD } from '../thresholds'
import type { OrgSummary } from '../types'

function StatCard({
  label,
  value,
  meta,
  caution,
}: {
  label: string
  value: string
  meta?: string
  caution?: boolean
}) {
  return (
    <div
      className={cn(
        'rounded-md border border-border bg-card px-5 py-4',
        caution && 'border-l-4 border-l-status-alert'
      )}
    >
      <p className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
        {label}
      </p>
      <p className="type-numeric my-2 text-2xl font-extrabold text-brand-primary tabular-nums">
        {value}
      </p>
      {meta && <p className="text-xs text-muted-foreground">{meta}</p>}
    </div>
  )
}

const SKELETON_COUNT = 6

export function SummaryStatGrid({
  data,
  isPending,
}: {
  data: OrgSummary | undefined
  isPending: boolean
}) {
  if (isPending || !data) {
    return (
      <section aria-hidden="true">
        <h2 className="sr-only">Summary</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: SKELETON_COUNT }).map((_, i) => (
            <div key={i} className="rounded-md border border-border bg-card px-5 py-4">
              <Skeleton className="mb-3 h-3 w-20" />
              <Skeleton className="mb-2 h-7 w-16" />
              <Skeleton className="h-3 w-24" />
            </div>
          ))}
        </div>
      </section>
    )
  }

  const maxDepthCaution = data.max_depth >= DEEP_CHAIN_THRESHOLD
  const rootCountCaution = data.root_count > 1

  return (
    <section aria-labelledby="summary-stat-grid-heading">
      <h2 id="summary-stat-grid-heading" className="sr-only">
        Summary
      </h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Headcount" value={data.headcount.toLocaleString()} />
        <StatCard
          label="Managers"
          value={data.manager_count.toLocaleString()}
          meta={`${data.individual_contributor_count.toLocaleString()} individual contributors`}
        />
        <StatCard
          label="Individual contributors"
          value={data.individual_contributor_count.toLocaleString()}
        />
        <StatCard
          label="Maximum depth"
          value={String(data.max_depth)}
          meta={maxDepthCaution ? 'Deeper than usual' : undefined}
        />
        <StatCard
          label="Avg. span of control"
          value={data.average_span_of_control.toFixed(1)}
          meta="Managers only"
        />
        <StatCard
          label="Roots"
          value={String(data.root_count)}
          meta={rootCountCaution ? 'More than one root' : undefined}
          caution={rootCountCaution}
        />
      </div>
    </section>
  )
}
