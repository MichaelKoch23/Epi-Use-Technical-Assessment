import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangleIcon, ArrowRightIcon, CalendarClockIcon, LockIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { formatCurrency, formatDate } from '@/features/employees/format'
import { fetchMovePreview, hasCostDelta } from './api'
import { todayIso } from './useAsOf'

export interface PendingMove {
  employeeId: string
  employeeName: string
  newManagerId: string | null
  newManagerName: string
}

function DepthChange({ change }: { change: number }) {
  if (change === 0) return <>Stays at the same level</>
  const levels = Math.abs(change) === 1 ? 'level' : 'levels'
  return (
    <>
      Moves {Math.abs(change)} {levels} {change > 0 ? 'deeper' : 'higher'}
    </>
  )
}

export function MovePreviewDialog({
  move,
  onOpenChange,
  onConfirm,
  isSubmitting,
}: {
  move: PendingMove | null
  onOpenChange: (open: boolean) => void
  onConfirm: (args: { effectiveFrom: string; reason: string }) => void
  isSubmitting: boolean
}) {
  const today = todayIso()
  const [effectiveFrom, setEffectiveFrom] = useState(today)
  const [reason, setReason] = useState('')

  useEffect(() => {
    if (move) {
      setEffectiveFrom(todayIso())
      setReason('')
    }
  }, [move])

  // The preview is validated at the date the move would take effect, so moving
  // the date picker re-checks it rather than leaving a stale verdict on screen.
  const query = useQuery({
    queryKey: ['move-preview', move?.employeeId, move?.newManagerId, effectiveFrom],
    queryFn: () => fetchMovePreview(move!.employeeId, move!.newManagerId, effectiveFrom),
    enabled: Boolean(move),
  })

  const preview = query.data
  const blocked = preview?.blocked ?? false

  return (
    <Dialog open={Boolean(move)} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>
            {preview
              ? `Moving ${move?.employeeName} moves ${preview.headcount} ${
                  preview.headcount === 1 ? 'employee' : 'employees'
                }`
              : `Moving ${move?.employeeName}`}
          </DialogTitle>
          <DialogDescription>
            New manager: <span className="font-medium">{move?.newManagerName}</span>
          </DialogDescription>
        </DialogHeader>

        {query.isPending ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : query.isError || !preview ? (
          <p className="text-sm text-muted-foreground">Could not load the move preview.</p>
        ) : (
          <div className="flex flex-col gap-4">
            {blocked && (
              <div
                role="alert"
                className="flex flex-col gap-1.5 rounded-md border-l-4 border-l-status-critical bg-status-critical/10 px-3 py-2.5 text-sm text-status-critical"
              >
                <span className="flex items-center gap-1.5 font-semibold">
                  <AlertTriangleIcon className="size-4" aria-hidden="true" />
                  This move would create a reporting cycle
                  {preview.blocked_at && <> as at {formatDate(preview.blocked_at)}</>}
                </span>
                <span className="flex flex-wrap items-center gap-1 text-xs">
                  {(preview.blocked_chain_names ?? []).map((name, i) => (
                    <span key={`${name}-${i}`} className="flex items-center gap-1">
                      {i > 0 && <ArrowRightIcon className="size-3" aria-hidden="true" />}
                      {name}
                    </span>
                  ))}
                </span>
              </div>
            )}

            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Currently reports to</dt>
                <dd>{preview.current_manager?.name ?? 'No manager'}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Depth change</dt>
                <dd>
                  <DepthChange change={preview.depth_change} />
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-xs text-muted-foreground">Cost moving between branches</dt>
                <dd>
                  {hasCostDelta(preview) ? (
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-muted-foreground">
                        {preview.current_manager?.name ?? 'No branch'} &minus;
                        {formatCurrency(
                          preview.cost_delta.leaving,
                          preview.cost_delta.currency
                        )}
                      </span>
                      <ArrowRightIcon className="size-3.5" aria-hidden="true" />
                      <span className="font-medium">
                        {move?.newManagerName} +
                        {formatCurrency(
                          preview.cost_delta.arriving,
                          preview.cost_delta.currency
                        )}
                      </span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground italic">
                      <LockIcon className="size-3.5" aria-hidden="true" />
                      Restricted - the cost impact requires HR admin access
                    </span>
                  )}
                </dd>
              </div>
            </dl>

            {preview.supersedes.length > 0 && (
              <section
                aria-label="Scheduled changes this will cancel"
                className="rounded-md border-l-4 border-l-status-alert bg-status-alert/10 px-3 py-2.5"
              >
                <h3 className="flex items-center gap-1.5 text-sm font-semibold text-status-alert">
                  <CalendarClockIcon className="size-4" aria-hidden="true" />
                  This will cancel {preview.supersedes.length} scheduled change
                  {preview.supersedes.length === 1 ? '' : 's'}
                </h3>
                <ul className="mt-1.5 flex flex-col gap-1 text-xs">
                  {preview.supersedes.map((row) => (
                    <li key={row.id}>
                      {formatDate(row.effective_from)}: move to{' '}
                      <span className="font-medium">{row.manager_name ?? 'No manager'}</span>
                      {row.reason && <span className="text-muted-foreground"> ({row.reason})</span>}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <section aria-label="Affected employees" className="flex flex-col gap-1">
              <h3 className="text-sm font-semibold">
                Employees who move ({preview.affected.length})
              </h3>
              <ul className="max-h-44 overflow-y-auto rounded-md border border-border">
                {preview.affected.map((person) => (
                  <li
                    key={person.id}
                    className="flex items-center justify-between gap-3 border-b border-border px-3 py-1.5 text-sm last:border-none"
                    style={{ paddingLeft: `${12 + person.depth * 14}px` }}
                  >
                    <span className="truncate font-medium">{person.name}</span>
                    <span className="shrink-0 truncate text-xs text-muted-foreground">
                      {person.position}
                    </span>
                  </li>
                ))}
              </ul>
            </section>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="flex flex-col gap-1">
                <label htmlFor="move-effective-from" className="text-xs text-muted-foreground">
                  Effective from
                </label>
                <input
                  id="move-effective-from"
                  type="date"
                  value={effectiveFrom}
                  onChange={(event) => setEffectiveFrom(event.target.value || today)}
                  className="rounded-sm border border-input px-2 py-1.5 text-sm"
                />
                {effectiveFrom > today && (
                  <span className="text-xs text-brand-teal">
                    Scheduled - takes effect on {formatDate(effectiveFrom)}
                  </span>
                )}
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="move-reason" className="text-xs text-muted-foreground">
                  Reason (optional)
                </label>
                <Textarea
                  id="move-reason"
                  rows={2}
                  value={reason}
                  maxLength={500}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="Team restructure"
                />
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={blocked || query.isPending || isSubmitting}
            onClick={() => onConfirm({ effectiveFrom, reason: reason.trim() })}
          >
            {effectiveFrom > today ? 'Schedule move' : 'Confirm move'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
