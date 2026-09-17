import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRightIcon, LockIcon } from 'lucide-react'
import { Link } from 'react-router'
import { Skeleton } from '@/components/ui/skeleton'
import type { components } from '@/lib/api-types'
import { employeeKeys } from '@/lib/queryKeys'
import { formatCurrency, formatDate, formatDateTime } from './format'
import { fetchAuditLog } from './mutations'

type AuditLogEntry = components['schemas']['AuditLogRead']
type Snapshot = Record<string, unknown> | null

const ACTION_LABELS: Record<string, string> = {
  'employee.created': 'Employee created',
  'employee.deleted': 'Employee deleted',
  'employee.restored': 'Employee restored',
  'employee.reassigned': 'Reporting line changed',
}

const FIELD_LABELS: Record<string, string> = {
  employee_number: 'Employee number',
  first_name: 'First name',
  last_name: 'Last name',
  email: 'Email',
  birth_date: 'Date of birth',
  position: 'Position',
  salary: 'Salary',
  currency: 'Currency',
  avatar_override_url: 'Avatar',
}

const DIFF_IGNORED_FIELDS = new Set(['version', 'manager_id', 'deleted_at'])

function changedFields(before: Snapshot, after: Snapshot): string[] {
  if (!before || !after) return []
  const keys = new Set([...Object.keys(before), ...Object.keys(after)])
  return [...keys].filter(
    (key) => !DIFF_IGNORED_FIELDS.has(key) && before[key] !== after[key]
  )
}

function formatFieldValue(field: string, value: unknown, currency: string): string {
  if (value === null || value === undefined) return '-'
  if (field === 'birth_date') return formatDate(String(value))
  if (field === 'salary') return formatCurrency(String(value), currency)
  return String(value)
}

function actionLabel(entry: AuditLogEntry, fields: string[]): string {
  const fixed = ACTION_LABELS[entry.action]
  if (fixed) return fixed
  const displayFields = fields.map((f) => FIELD_LABELS[f] ?? f)
  if (displayFields.length === 0) {
    return entry.salary_changed ? 'Salary updated' : 'Employee updated'
  }
  return `${displayFields.join(', ')} updated`
}

export function AuditEntry({
  entry,
  employeeName,
  employeeId,
}: {
  entry: AuditLogEntry
  employeeName?: string
  employeeId?: string
}) {
  const currency =
    (entry.after?.currency as string | undefined) ??
    (entry.before?.currency as string | undefined) ??
    'ZAR'
  const fields = changedFields(entry.before, entry.after).filter((f) => f !== 'salary')
  const isReassignment = entry.action === 'employee.reassigned'

  return (
    <li className="flex flex-col gap-1.5 border-b border-border py-3 last:border-none">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-semibold text-foreground">
          {employeeName && employeeId && (
            <>
              <Link
                to={`/employees/${employeeId}`}
                className="text-brand-mid underline underline-offset-2"
              >
                {employeeName}
              </Link>
              <span className="font-normal text-muted-foreground"> - </span>
            </>
          )}
          {actionLabel(entry, fields)}
        </span>
        {entry.salary_changed && (
          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
            <LockIcon className="size-3" aria-hidden="true" />
            Values restricted
          </span>
        )}
      </div>
      <div className="text-xs text-muted-foreground">
        {entry.actor_email} · {formatDateTime(entry.occurred_at)}
      </div>

      {isReassignment && (
        <div className="flex items-center gap-1.5 text-sm">
          <span className="text-muted-foreground">
            {entry.manager_before_name ?? 'No manager'}
          </span>
          <ArrowRightIcon className="size-3.5 text-muted-foreground" aria-hidden="true" />
          <span className="font-medium text-foreground">
            {entry.manager_after_name ?? 'No manager'}
          </span>
        </div>
      )}

      {!isReassignment && fields.length > 0 && (
        <ul className="flex flex-col gap-1">
          {fields.map((field) => (
            <li key={field} className="flex flex-wrap items-center gap-1.5 text-sm">
              <span className="text-xs text-muted-foreground">
                {FIELD_LABELS[field] ?? field}:
              </span>
              <span className="text-muted-foreground line-through decoration-muted-foreground/50">
                {formatFieldValue(field, entry.before?.[field], currency)}
              </span>
              <ArrowRightIcon className="size-3.5 text-muted-foreground" aria-hidden="true" />
              <span className="font-medium text-foreground">
                {formatFieldValue(field, entry.after?.[field], currency)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

export function AuditTimeline({ employeeId }: { employeeId: string }) {
  const [page, setPage] = useState(1)
  const query = useQuery({
    queryKey: employeeKeys.auditLog(employeeId, page),
    queryFn: () => fetchAuditLog(employeeId, page),
  })

  return (
    <section aria-label="Change history" className="flex flex-col gap-2">
      <h2 className="font-display text-lg font-semibold">Change history</h2>

      {query.isPending ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : query.isError ? (
        <p className="text-sm text-muted-foreground">Could not load change history.</p>
      ) : query.data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No changes recorded yet.</p>
      ) : (
        <ul>
          {query.data.items.map((entry) => (
            <AuditEntry key={entry.id} entry={entry} />
          ))}
        </ul>
      )}

      {query.data && query.data.total > query.data.page_size && (
        <div className="flex items-center justify-end gap-3 text-sm">
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
  )
}
