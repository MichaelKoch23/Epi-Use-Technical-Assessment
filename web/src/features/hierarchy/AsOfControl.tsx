import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CalendarClockIcon, RotateCcwIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/features/employees/format'
import { hierarchyKeys } from '@/lib/queryKeys'
import { cn } from '@/lib/utils'
import { fetchScheduled } from './api'
import { shiftIso, type AsOfState } from './useAsOf'

export function AsOfControl({ state }: { state: AsOfState }) {
  const { asOf, today, isToday, setAsOf } = state

  const scheduledQuery = useQuery({
    queryKey: hierarchyKeys.scheduled(),
    queryFn: fetchScheduled,
    staleTime: 60_000,
  })

  const changeDates = useMemo(() => {
    const dates = new Set((scheduledQuery.data ?? []).map((row) => row.effective_from))
    return [...dates].sort()
  }, [scheduledQuery.data])

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-card px-3 py-2 print:hidden">
      <label
        htmlFor="as-of-date"
        className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground"
      >
        <CalendarClockIcon className="size-4" aria-hidden="true" />
        Viewing as at
      </label>
      <input
        id="as-of-date"
        type="date"
        value={asOf}
        onChange={(event) => setAsOf(event.target.value || null)}
        className="rounded-sm border border-input px-2 py-1 text-sm"
      />

      <div className="flex items-center gap-1">
        <Button
          variant={isToday ? 'default' : 'outline'}
          size="sm"
          aria-pressed={isToday}
          onClick={() => setAsOf(null)}
        >
          <RotateCcwIcon className="size-3.5" aria-hidden="true" /> Today
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setAsOf(shiftIso(today, { months: -3 }))}
        >
          &minus;3 months
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setAsOf(shiftIso(today, { months: -12 }))}
        >
          &minus;1 year
        </Button>
      </div>

      {changeDates.length > 0 && (
        <div className="flex flex-wrap items-center gap-1 border-l border-border pl-2">
          <span className="text-xs text-muted-foreground">Jump to change:</span>
          {changeDates.map((date) => (
            <Button
              key={date}
              variant="outline"
              size="sm"
              aria-pressed={asOf === date}
              className={cn(
                'border-brand-teal/40 text-brand-teal',
                asOf === date && 'bg-brand-teal/10'
              )}
              onClick={() => setAsOf(date)}
            >
              {formatDate(date)}
            </Button>
          ))}
        </div>
      )}
    </div>
  )
}
