import { Skeleton } from '@/components/ui/skeleton'
import type { OrgSummary } from '../types'

const DEPTH_FILL_TOKENS = [
  'bg-depth-0',
  'bg-depth-1',
  'bg-depth-2',
  'bg-depth-3',
  'bg-depth-4',
] as const

function depthFillToken(depth: number): (typeof DEPTH_FILL_TOKENS)[number] {
  return DEPTH_FILL_TOKENS[Math.min(Math.max(depth, 0), DEPTH_FILL_TOKENS.length - 1)]!
}

export function DepthDistributionChart({
  data,
  isPending,
}: {
  data: OrgSummary['depth_distribution'] | undefined
  isPending: boolean
}) {
  if (isPending || !data) {
    return (
      <section aria-hidden="true" className="rounded-md border border-border bg-card px-5 py-4">
        <Skeleton className="mb-4 h-4 w-40" />
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-5 w-full" />
          ))}
        </div>
      </section>
    )
  }

  const maxCount = Math.max(1, ...data.map((row) => row.count))
  const totalEmployees = data.reduce((sum, row) => sum + row.count, 0)

  return (
    <section
      aria-labelledby="depth-distribution-heading"
      className="rounded-md border border-border bg-card px-5 py-4"
    >
      <h2 id="depth-distribution-heading" className="font-display text-sm font-bold text-brand-primary">
        Depth distribution
      </h2>
      <p className="mb-4 text-xs text-muted-foreground">
        How many employees sit at each level below the top of the organisation.
      </p>

      <div
        role="img"
        aria-label={`Depth distribution across ${totalEmployees} reachable employees, from the root at depth 0 to the deepest level.`}
        className="space-y-1.5"
      >
        {data.map((row) => (
          <div key={row.depth} className="grid grid-cols-[5rem_1fr_3.5rem] items-center gap-3">
            <span className="text-xs text-muted-foreground">Depth {row.depth}</span>
            <div className="h-4 rounded-sm bg-muted">
              <div
                className={`h-full rounded-sm ${depthFillToken(row.depth)}`}
                style={{ width: `${(row.count / maxCount) * 100}%` }}
              />
            </div>
            <span className="type-numeric text-right text-xs tabular-nums text-muted-foreground">
              {row.count}
            </span>
          </div>
        ))}
      </div>

      <table className="sr-only">
        <caption>Number of employees by depth below the top of the organisation</caption>
        <thead>
          <tr>
            <th scope="col">Depth</th>
            <th scope="col">Employees</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.depth}>
              <td>{row.depth}</td>
              <td>{row.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
