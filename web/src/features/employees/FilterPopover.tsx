import { useState } from 'react'
import { SlidersHorizontalIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverHeader, PopoverTitle, PopoverTrigger } from '@/components/ui/popover'
import { ManagerPicker } from './ManagerPicker'
import type { EmployeesFilterState } from './useEmployeesViewState'

// The popover never touches `q` (the search bar owns that field), so its
// draft excludes it — applying the draft as a whole must not be able to
// clobber a search the user has already typed or cleared elsewhere.
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

function toPopoverState(filters: EmployeesFilterState): PopoverFilterState {
  const { q: _q, ...rest } = filters
  return rest
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

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        // Reset the draft from the applied filters right as it opens,
        // rather than in an effect — this is the event that should own it.
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
          <Input
            id="filter-position"
            placeholder="e.g. Software Engineer"
            value={draft.position}
            onChange={(e) => setDraft((d) => ({ ...d, position: e.target.value }))}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Reports to</Label>
          <ManagerPicker
            value={draft.managerId}
            label={draft.managerName}
            clearLabel="Any manager"
            onChange={(managerId, managerName) =>
              setDraft((d) => ({ ...d, managerId, managerName }))
            }
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Salary range</Label>
          {salaryFilterAllowed ? (
            <div className="flex items-center gap-2">
              <Input
                type="number"
                inputMode="decimal"
                min={0}
                placeholder="Min"
                value={draft.minSalary}
                onChange={(e) => setDraft((d) => ({ ...d, minSalary: e.target.value }))}
              />
              <span className="text-muted-foreground">–</span>
              <Input
                type="number"
                inputMode="decimal"
                min={0}
                placeholder="Max"
                value={draft.maxSalary}
                onChange={(e) => setDraft((d) => ({ ...d, maxSalary: e.target.value }))}
              />
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">Requires HR admin access.</p>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Date of birth range</Label>
          <div className="flex items-center gap-2">
            <Input
              type="date"
              value={draft.minBirthDate}
              onChange={(e) => setDraft((d) => ({ ...d, minBirthDate: e.target.value }))}
            />
            <span className="text-muted-foreground">–</span>
            <Input
              type="date"
              value={draft.maxBirthDate}
              onChange={(e) => setDraft((d) => ({ ...d, maxBirthDate: e.target.value }))}
            />
          </div>
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
            onClick={() => {
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
