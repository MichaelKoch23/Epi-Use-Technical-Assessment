import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRightIcon, GitCompareIcon, LockIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency, formatDate } from '@/features/employees/format'
import { fetchStructureDiff, hasDiffCost, type StructureDiff } from '@/features/hierarchy/api'
import { shiftIso, todayIso } from '@/features/hierarchy/useAsOf'
import { getErrorMessage } from '@/lib/apiError'
import { hierarchyKeys } from '@/lib/queryKeys'

type ManagerChange = StructureDiff['manager_changes'][number]

function ChangeList({ title, changes }: { title: string; changes: ManagerChange[] }) {
  if (changes.length === 0) return null
  return (
    <section className="flex flex-col gap-1">
      <h3 className="text-sm font-semibold">
        {title} ({changes.length})
      </h3>
      <ul className="rounded-md border border-border">
        {changes.map((change) => (
          <li
            key={change.employee_id}
            className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-3 py-2 text-sm last:border-none"
          >
            <span className="font-medium">{change.employee_name}</span>
            <span className="flex items-center gap-1.5 text-muted-foreground">
              {change.from_manager_name ?? 'No manager'}
              <ArrowRightIcon className="size-3.5" aria-hidden="true" />
              <span className="font-medium text-foreground">
                {change.to_manager_name ?? 'No manager'}
              </span>
              {change.subtree_size > 0 && (
                <span className="text-xs">
                  (+{change.subtree_size} report{change.subtree_size === 1 ? '' : 's'})
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Delta({ label, from, to }: { label: string; from: number; to: number }) {
  const change = Math.round((to - from) * 100) / 100
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="type-numeric text-xl font-bold text-brand-primary tabular-nums">
        {from} &rarr; {to}
        <span className="ml-1 text-xs font-medium text-muted-foreground">
          ({change > 0 ? '+' : ''}
          {change})
        </span>
      </dd>
    </div>
  )
}

export function StructureDiffPanel() {
  const today = todayIso()
  const [from, setFrom] = useState(() => shiftIso(today, { months: -3 }))
  const [to, setTo] = useState(today)
  const [range, setRange] = useState<{ from: string; to: string } | null>(null)

  const query = useQuery({
    queryKey: hierarchyKeys.diff(range?.from ?? '', range?.to ?? ''),
    queryFn: () => fetchStructureDiff(range!.from, range!.to),
    enabled: Boolean(range),
  })

  const diff = query.data

  return (
    <section
      aria-labelledby="structure-diff-heading"
      className="rounded-md border border-border bg-card px-5 py-4"
    >
      <h2
        id="structure-diff-heading"
        className="font-display mb-3 flex items-center gap-1.5 text-sm font-bold text-brand-primary"
      >
        <GitCompareIcon className="size-4" aria-hidden="true" />
        Structure diff
      </h2>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="diff-from" className="text-xs text-muted-foreground">
            From
          </label>
          <input
            id="diff-from"
            type="date"
            value={from}
            max={to}
            onChange={(event) => setFrom(event.target.value)}
            className="rounded-sm border border-input px-2 py-1.5 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="diff-to" className="text-xs text-muted-foreground">
            To
          </label>
          <input
            id="diff-to"
            type="date"
            value={to}
            min={from}
            onChange={(event) => setTo(event.target.value)}
            className="rounded-sm border border-input px-2 py-1.5 text-sm"
          />
        </div>
        <Button size="sm" disabled={!from || !to} onClick={() => setRange({ from, to })}>
          Compare
        </Button>
      </div>

      {query.isError && (
        <p className="mt-3 text-sm text-status-critical">
          {getErrorMessage(query.error, 'Failed to compare the two dates')}
        </p>
      )}

      {range && query.isPending && (
        <div className="mt-4 flex flex-col gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {diff && (
        <div className="mt-4 flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            {formatDate(diff.from_date)} to {formatDate(diff.to_date)}:{' '}
            {diff.manager_changes.length === 0
              ? 'the reporting structure is unchanged.'
              : `${diff.manager_changes.length} reporting change${
                  diff.manager_changes.length === 1 ? '' : 's'
                }, ${diff.branch_moves.length} of which moved a whole branch.`}
          </p>

          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Delta label="Maximum depth" from={diff.max_depth_from} to={diff.max_depth_to} />
            <Delta
              label="Average span of control"
              from={diff.average_span_from}
              to={diff.average_span_to}
            />
            <div>
              <dt className="text-xs text-muted-foreground">Salary that changed branch</dt>
              <dd>
                {hasDiffCost(diff) ? (
                  <span className="type-numeric text-xl font-bold text-brand-primary tabular-nums">
                    {formatCurrency(diff.cost.total_moved, diff.cost.currency)}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground italic">
                    <LockIcon className="size-3.5" aria-hidden="true" />
                    Restricted - requires HR admin access
                  </span>
                )}
              </dd>
            </div>
          </dl>

          <ChangeList title="Branches moved" changes={diff.branch_moves} />
          <ChangeList title="Became a root" changes={diff.became_root} />
          <ChangeList title="Stopped being a root" changes={diff.stopped_being_root} />
          <ChangeList title="All reporting changes" changes={diff.manager_changes} />
        </div>
      )}
    </section>
  )
}
