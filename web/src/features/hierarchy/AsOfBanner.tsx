import { HistoryIcon, TelescopeIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/features/employees/format'
import { cn } from '@/lib/utils'
import type { AsOfState } from './useAsOf'

/**
 * Past and future views are deliberately different colours: --status-alert for
 * a historical view, and the palette's teal for a scheduled one. Mistaking one
 * for the other is the whole risk this banner exists to remove.
 */
export function AsOfBanner({ state }: { state: AsOfState }) {
  const { asOf, isToday, isPast, setAsOf } = state
  if (isToday) return null

  const Icon = isPast ? HistoryIcon : TelescopeIcon

  return (
    <div
      role="status"
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 rounded-md border-l-4 px-4 py-2.5 print:hidden',
        isPast
          ? 'border-l-status-alert bg-status-alert/10 text-status-alert'
          : 'border-l-depth-4 bg-depth-4/10 text-depth-4'
      )}
    >
      <p className="flex items-center gap-2 text-sm font-medium">
        <Icon className="size-4 shrink-0" aria-hidden="true" />
        <span>
          Viewing the organisation as at {formatDate(asOf)}
          <span className="font-normal">
            {' '}
            &mdash; {isPast ? 'a historical view' : 'a scheduled future view'}. Editing is
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
