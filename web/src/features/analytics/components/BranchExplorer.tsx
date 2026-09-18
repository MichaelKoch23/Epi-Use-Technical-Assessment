import { NetworkIcon, SearchIcon } from 'lucide-react'
import { Link, useSearchParams } from 'react-router'
import { Skeleton } from '@/components/ui/skeleton'
import { ManagerPicker } from '@/features/employees/ManagerPicker'
import { getErrorMessage } from '@/lib/apiError'
import { useBranchSummary } from '../useBranchSummary'
import { hasCost } from '../types'
import { CostPanel } from './CostPanel'
import { EmptyState } from './EmptyState'
import { ErrorState } from './ErrorState'

const BRANCH_PARAM = 'branch'

export function BranchExplorer() {
  const [searchParams, setSearchParams] = useSearchParams()
  const branchId = searchParams.get(BRANCH_PARAM)
  const query = useBranchSummary(branchId)

  const selectBranch = (id: string) => {
    const next = new URLSearchParams(searchParams)
    if (id) next.set(BRANCH_PARAM, id)
    else next.delete(BRANCH_PARAM)
    setSearchParams(next, { replace: true })
  }

  return (
    <section aria-labelledby="branch-explorer-heading" className="rounded-md border border-border bg-card px-5 py-4">
      <h2 id="branch-explorer-heading" className="font-display mb-3 text-sm font-bold text-brand-primary">
        Branch explorer
      </h2>

      <div className="mb-4 max-w-sm">
        <ManagerPicker
          value={branchId ?? ''}
          label={query.data?.employee.name ?? ''}
          onChange={(id) => selectBranch(id)}
          clearLabel="Choose an employee..."
          triggerAriaLabel="Choose an employee to explore their branch"
        />
      </div>

      {!branchId ? (
        <EmptyState icon={SearchIcon} title="Choose an employee">
          Pick anyone in the organisation to see headcount, span of control and cost for
          everyone reporting up to them.
        </EmptyState>
      ) : query.isPending ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i}>
              <Skeleton className="mb-2 h-3 w-20" />
              <Skeleton className="h-6 w-14" />
            </div>
          ))}
        </div>
      ) : query.isError ? (
        <ErrorState
          message={getErrorMessage(query.error, 'Failed to load this branch')}
          onRetry={() => query.refetch()}
        />
      ) : (
        <div className="space-y-4">
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <dt className="text-xs text-muted-foreground">Headcount</dt>
              <dd className="type-numeric text-xl font-bold text-brand-primary tabular-nums">
                {query.data.headcount}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Direct reports</dt>
              <dd className="type-numeric text-xl font-bold text-brand-primary tabular-nums">
                {query.data.direct_reports}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Depth below</dt>
              <dd className="type-numeric text-xl font-bold text-brand-primary tabular-nums">
                {query.data.depth_below}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Avg. span of control</dt>
              <dd className="type-numeric text-xl font-bold text-brand-primary tabular-nums">
                {query.data.average_span_of_control.toFixed(1)}
              </dd>
            </div>
          </dl>

          <CostPanel
            cost={hasCost(query.data) ? query.data.cost : undefined}
            restricted={!hasCost(query.data)}
            isPending={false}
          />

          <Link
            to={`/chart?focus=${branchId}`}
            className="inline-flex items-center gap-1.5 text-sm text-brand-mid underline-offset-2 hover:underline"
          >
            <NetworkIcon className="size-4" aria-hidden="true" />
            View in org chart
          </Link>
        </div>
      )}
    </section>
  )
}
