import { useState } from 'react'
import {
  AlertOctagonIcon,
  AlertTriangleIcon,
  ChevronDownIcon,
  ShieldCheckIcon,
  UsersIcon,
} from 'lucide-react'
import { Link } from 'react-router'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import type { OrgSummary } from '../types'
import { EmptyState } from './EmptyState'

type Anomalies = OrgSummary['anomalies']

// Entries beyond this are hidden behind "and N more" - the panel never
// shows more than `anomalies.*` already contains (itself capped server-side
// at `ANOMALY_LIST_LIMIT`, §1.3), just fewer of them at once.
const INLINE_LIMIT = 5

interface GroupEntry {
  id: string
  name: string
  line: string
}

function AnomalyGroup({
  id,
  title,
  icon: Icon,
  badgeClassName,
  entries,
}: {
  id: string
  title: string
  icon: typeof AlertTriangleIcon
  badgeClassName: string
  entries: GroupEntry[]
}) {
  const [expanded, setExpanded] = useState(true)
  const [showAll, setShowAll] = useState(false)
  if (entries.length === 0) return null

  const visible = showAll ? entries : entries.slice(0, INLINE_LIMIT)
  const remaining = entries.length - visible.length
  const panelId = `anomaly-group-${id}`

  return (
    <div className="border-b border-border py-3 last:border-none">
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={panelId}
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center gap-2 text-left"
      >
        <ChevronDownIcon
          className={cn('size-4 shrink-0 text-muted-foreground transition-transform', !expanded && '-rotate-90')}
          aria-hidden="true"
        />
        <Icon className="size-4 shrink-0" aria-hidden="true" />
        <span className="flex-1 text-sm font-semibold text-foreground">{title}</span>
        <Badge className={badgeClassName}>{entries.length}</Badge>
      </button>

      <ul id={panelId} hidden={!expanded} className="mt-2 ml-6 space-y-2">
        {visible.map((entry) => (
          <li key={entry.id} className="text-sm">
            <Link
              to={`/chart?focus=${entry.id}`}
              className="text-brand-mid underline-offset-2 hover:underline"
            >
              {entry.line}
            </Link>
          </li>
        ))}
        {remaining > 0 && (
          <li>
            <button
              type="button"
              className="text-sm text-muted-foreground underline-offset-2 hover:underline"
              onClick={() => setShowAll(true)}
            >
              and {remaining} more
            </button>
          </li>
        )}
      </ul>
    </div>
  )
}

export function AnomalyPanel({
  data,
  isPending,
}: {
  data: Anomalies | undefined
  isPending: boolean
}) {
  if (isPending || !data) {
    return (
      <section aria-hidden="true" className="rounded-md border border-border bg-card px-5 py-4">
        <Skeleton className="mb-4 h-4 w-40" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-full" />
          ))}
        </div>
      </section>
    )
  }

  const wideSpans: GroupEntry[] = data.wide_spans.map((row) => ({
    id: row.id,
    name: row.name,
    line: `${row.name} has ${row.direct_reports} direct reports - above the healthy range of 3–10`,
  }))
  const singleReportManagers: GroupEntry[] = data.single_report_managers.map((row) => ({
    id: row.id,
    name: row.name,
    line: `${row.name} manages one person - this may be a redundant reporting layer`,
  }))
  const deepChains: GroupEntry[] = data.deep_chains.map((row) => ({
    id: row.id,
    name: row.name,
    line: `${row.name} is ${row.depth} levels below the top of the organisation`,
  }))
  const unreachable: GroupEntry[] = data.unreachable.map((row) => ({
    id: row.id,
    name: row.name,
    line: `${row.name} is not reachable from any root - their manager may have been deleted without reassignment`,
  }))

  const isEmpty =
    wideSpans.length === 0 &&
    singleReportManagers.length === 0 &&
    deepChains.length === 0 &&
    unreachable.length === 0

  return (
    <section aria-labelledby="anomaly-panel-heading" className="rounded-md border border-border bg-card px-5 py-4">
      <h2 id="anomaly-panel-heading" className="font-display mb-1 text-sm font-bold text-brand-primary">
        Structural anomalies
      </h2>

      {isEmpty ? (
        <EmptyState icon={ShieldCheckIcon} title="No structural issues found">
          Checked for wide spans of control (more than 10 direct reports), single-report
          managers, reporting chains 6 levels deep or more, and employees unreachable from
          any root. None found.
        </EmptyState>
      ) : (
        <div>
          <AnomalyGroup
            id="wide-spans"
            title="Wide span of control"
            icon={AlertTriangleIcon}
            badgeClassName="bg-status-alert/15 text-brand-primary"
            entries={wideSpans}
          />
          <AnomalyGroup
            id="single-report"
            title="Single-report managers"
            icon={UsersIcon}
            badgeClassName="bg-muted text-muted-foreground"
            entries={singleReportManagers}
          />
          <AnomalyGroup
            id="deep-chains"
            title="Deep reporting chains"
            icon={AlertTriangleIcon}
            badgeClassName="bg-status-alert/15 text-brand-primary"
            entries={deepChains}
          />
          <AnomalyGroup
            id="unreachable"
            title="Unreachable employees"
            icon={AlertOctagonIcon}
            badgeClassName="bg-status-critical/10 text-status-critical"
            entries={unreachable}
          />
        </div>
      )}
    </section>
  )
}
