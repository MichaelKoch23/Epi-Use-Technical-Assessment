import { HistoryIcon, TelescopeIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/features/employees/format'
import { cn } from '@/lib/utils'
import type { AsOfState } from './useAsOf'

export function AsOfBanner({ state }: { state: AsOfState }) {
  const { asOf, isToday, isPast, setAsOf } = state
  if (isToday) return null

  const Icon = isPast ? HistoryIcon : TelescopeIcon

  return (
    <div
      role="status"
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 rounded-md border px-4 py-2.5 print:hidden',
        isPast
          ? 'border-status-alert/30 bg-status-alert/10 text-status-alert'
          : 'border-brand-teal/30 bg-brand-teal/10 text-brand-teal'
      )}
    >
      <p className="flex items-center gap-2 text-sm font-medium">
        <Icon className="size-4 shrink-0" aria-hidden="true" />
        <span>
          Viewing the organisation as at {formatDate(asOf)}.
          <span className="font-normal">
            {' '}
            This is a {isPast ? 'historical' : 'scheduled future'} view, so editing is
            disabled.
          </span>
        </span>
      </p>
      <Button variant="outline" size="sm" onClick={() => setAsOf(null)}>
        Return to today
      </Button>
    </div>
  )
}
