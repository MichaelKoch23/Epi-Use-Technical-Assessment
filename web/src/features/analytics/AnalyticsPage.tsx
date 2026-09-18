import { UploadIcon } from 'lucide-react'
import { Link } from 'react-router'
import { getErrorMessage } from '@/lib/apiError'
import { formatDateTime } from '@/features/employees/format'
import { AnomalyPanel } from './components/AnomalyPanel'
import { BranchExplorer } from './components/BranchExplorer'
import { CostPanel } from './components/CostPanel'
import { DepthDistributionChart } from './components/DepthDistributionChart'
import { EmptyState } from './components/EmptyState'
import { ErrorState } from './components/ErrorState'
import { SpanDistributionChart } from './components/SpanDistributionChart'
import { StructureDiffPanel } from './components/StructureDiffPanel'
import { SummaryStatGrid } from './components/SummaryStatGrid'
import { hasCost } from './types'
import { useOrgSummary } from './useOrgSummary'

export function AnalyticsPage() {
  const query = useOrgSummary()
  const data = query.data

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-bold">Organisation analytics</h1>
        <p className="text-muted-foreground">
          {!data
            ? 'Loading the current org structure...'
            : `${data.headcount.toLocaleString()} employees, as of ${formatDateTime(
                new Date(query.dataUpdatedAt).toISOString()
              )}.`}
        </p>
      </div>

      {query.isError ? (
        <ErrorState
          message={getErrorMessage(query.error, 'Failed to load organisation analytics')}
          onRetry={() => query.refetch()}
        />
      ) : data && data.headcount === 0 ? (
        <EmptyState icon={UploadIcon} title="No employees yet">
          There's nothing to analyse until the organisation has at least one employee.
          Import a roster to get started.
          <div className="mt-4">
            <Link
              to="/import"
              className="text-sm font-medium text-brand-mid underline-offset-2 hover:underline"
            >
              Go to import
            </Link>
          </div>
        </EmptyState>
      ) : (
        <>
          <SummaryStatGrid data={data} isPending={query.isPending} />

          <CostPanel
            cost={data && hasCost(data) ? data.cost : undefined}
            restricted={!query.isPending && !!data && !hasCost(data)}
            isPending={query.isPending}
          />

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <SpanDistributionChart data={data?.span_distribution} isPending={query.isPending} />
            <DepthDistributionChart data={data?.depth_distribution} isPending={query.isPending} />
          </div>

          <AnomalyPanel data={data?.anomalies} isPending={query.isPending} />
        </>
      )}

      <BranchExplorer />

      <StructureDiffPanel />
    </div>
  )
}
