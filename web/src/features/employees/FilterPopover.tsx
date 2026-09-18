import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { SlidersHorizontalIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverHeader, PopoverTitle, PopoverTrigger } from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { apiClient } from '@/lib/apiClient'
import { employeeKeys } from '@/lib/queryKeys'
import { ManagerPicker } from './ManagerPicker'
import { fetchFilterManagers } from './mutations'
import type { EmployeesFilterState } from './useEmployeesViewState'

type PopoverFilterState = Omit<EmployeesFilterState, 'q'>

const EMPTY_DRAFT: PopoverFilterState = {
  position: '',
  managerId: '',
  managerName: '',
  minSalary: '',
  maxSalary: '',
  minBirthDate: '',
  maxBirthDate: '',
}

async function fetchPositions() {
  const { data, error } = await apiClient.GET('/api/v1/employees/positions')
  if (error) return []
  return data
}

function toPopoverState(filters: EmployeesFilterState): PopoverFilterState {
  const { q: _q, ...rest } = filters
  return rest
}

/**
 * A range with its bounds the wrong way round can never match anyone, so
 * applying it would empty the table and blame the data. Both ends are only
 * compared when both are filled in - a one-sided range is perfectly valid.
 * ISO dates compare lexicographically, which is also chronologically.
 */
function rangeError(min: string, max: string, numeric: boolean): string | null {
  if (!min || !max) return null
  const inverted = numeric ? Number(min) > Number(max) : min > max
  return inverted ? 'The minimum cannot be greater than the maximum.' : null
}

export function FilterPopover({
  filters,
  activeCount,
  salaryFilterAllowed,
  onApply,
}: {
  filters: EmployeesFilterState
  activeCount: number
  salaryFilterAllowed: boolean
  onApply: (patch: Partial<PopoverFilterState>) => void
}) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<PopoverFilterState>(() => toPopoverState(filters))
  const { data: positions = [] } = useQuery({
    queryKey: employeeKeys.positions(),
    queryFn: fetchPositions,
    staleTime: 5 * 60 * 1000,
  })
  const positionOptions =
    draft.position && !positions.includes(draft.position)
      ? [draft.position, ...positions]
      : positions

  // Driven by the draft, not the applied filters, so choosing a position and
  // then opening "Reports to" already offers that position's managers.
  const managerQueryParams = {
    position: draft.position || undefined,
    min_salary: salaryFilterAllowed && draft.minSalary ? draft.minSalary : undefined,
    max_salary: salaryFilterAllowed && draft.maxSalary ? draft.maxSalary : undefined,
    min_birth_date: draft.minBirthDate || undefined,
    max_birth_date: draft.maxBirthDate || undefined,
  }
  const { data: managerSuggestions = [], isFetching: managersLoading } = useQuery({
    queryKey: [...employeeKeys.all, 'filter-managers', managerQueryParams],
    queryFn: () => fetchFilterManagers(managerQueryParams),
    enabled: open,
    placeholderData: (previous) => previous,
  })

  const salaryError = rangeError(draft.minSalary, draft.maxSalary, true)
  const birthDateError = rangeError(draft.minBirthDate, draft.maxBirthDate, false)
  const hasError = Boolean(salaryError || birthDateError)

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        if (next) setDraft(toPopoverState(filters))
        setOpen(next)
      }}
    >
      <PopoverTrigger render={<Button variant="outline" />}>
        <SlidersHorizontalIcon /> Filters
        {activeCount > 0 && (
          <span className="ml-1 grid size-4 place-items-center rounded-full bg-brand-primary text-[10px] font-semibold text-white">
            {activeCount}
          </span>
        )}
      </PopoverTrigger>
      <PopoverContent className="w-80" align="start">
        <PopoverHeader>
          <PopoverTitle>Filter employees</PopoverTitle>
        </PopoverHeader>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="filter-position">Position</Label>
          <Select
            value={draft.position || null}
            onValueChange={(value) => setDraft((d) => ({ ...d, position: value ?? '' }))}
          >
            <SelectTrigger id="filter-position" className="w-full">
              <SelectValue placeholder="Any position" />
            </SelectTrigger>
            <SelectContent alignItemWithTrigger={false} className="max-h-72">
              <SelectItem value={null}>Any position</SelectItem>
              {positionOptions.map((position) => (
                <SelectItem key={position} value={position}>
                  {position}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Reports to</Label>
          <ManagerPicker
            value={draft.managerId}
            label={draft.managerName}
            clearLabel="Any manager"
            suggestions={managerSuggestions}
            suggestionsLoading={managersLoading}
            suggestionsHeading={
              draft.position ? `Managers of ${draft.position}` : 'Managers in this selection'
            }
            onChange={(managerId, managerName) =>
              setDraft((d) => ({ ...d, managerId, managerName }))
            }
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Salary range</Label>
          {salaryFilterAllowed ? (
            <>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  inputMode="decimal"
                  min={0}
                  placeholder="Min"
                  aria-label="Minimum salary"
                  aria-invalid={salaryError !== null}
                  aria-describedby={salaryError ? 'filter-salary-error' : undefined}
                  value={draft.minSalary}
                  onChange={(e) => setDraft((d) => ({ ...d, minSalary: e.target.value }))}
                />
                <span className="text-muted-foreground">–</span>
                <Input
                  type="number"
                  inputMode="decimal"
                  min={0}
                  placeholder="Max"
                  aria-label="Maximum salary"
                  aria-invalid={salaryError !== null}
                  aria-describedby={salaryError ? 'filter-salary-error' : undefined}
                  value={draft.maxSalary}
                  onChange={(e) => setDraft((d) => ({ ...d, maxSalary: e.target.value }))}
                />
              </div>
              {salaryError && (
                <p id="filter-salary-error" role="alert" className="text-xs text-status-critical">
                  {salaryError}
                </p>
              )}
            </>
          ) : (
            <p className="text-xs text-muted-foreground">Requires HR admin access.</p>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Date of birth range</Label>
          <div className="flex items-center gap-2">
            <Input
              type="date"
              aria-label="Earliest date of birth"
              aria-invalid={birthDateError !== null}
              aria-describedby={birthDateError ? 'filter-birth-date-error' : undefined}
              value={draft.minBirthDate}
              onChange={(e) => setDraft((d) => ({ ...d, minBirthDate: e.target.value }))}
            />
            <span className="text-muted-foreground">–</span>
            <Input
              type="date"
              aria-label="Latest date of birth"
              aria-invalid={birthDateError !== null}
              aria-describedby={birthDateError ? 'filter-birth-date-error' : undefined}
              value={draft.maxBirthDate}
              onChange={(e) => setDraft((d) => ({ ...d, maxBirthDate: e.target.value }))}
            />
          </div>
          {birthDateError && (
            <p id="filter-birth-date-error" role="alert" className="text-xs text-status-critical">
              {birthDateError}
            </p>
          )}
        </div>

        <div className="flex justify-between pt-1">
          <Button
            variant="ghost"
            onClick={() => {
              onApply(EMPTY_DRAFT)
              setOpen(false)
            }}
          >
            Reset
          </Button>
          <Button
            disabled={hasError}
            onClick={() => {
              if (hasError) return
              onApply(draft)
              setOpen(false)
            }}
          >
            Apply filters
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
