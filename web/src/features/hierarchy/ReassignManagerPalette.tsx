import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { apiClient, getActorId } from '@/lib/apiClient'
import { useDebouncedValue } from '@/lib/useDebouncedValue'
import type { ChartEmployee } from './types'

async function searchEmployees(q: string) {
  const { data, error } = await apiClient.GET('/api/v1/employees', {
    params: {
      query: { q: q || undefined, page: 1, page_size: 8, sort: 'last_name', order: 'asc' },
      header: { 'X-Actor-Id': getActorId() ?? '' },
    },
  })
  if (error) return []
  return data.items
}

/**
 * The keyboard/non-drag path for reassignment (§ accessibility
 * requirements: "Drag-to-reassign has a keyboard path: select an employee,
 * press M, choose a manager from the command palette"). Shares the same
 * cycle-exclusion messaging as `ManagerPicker`, on a global `CommandDialog`
 * instead of a per-field popover.
 */
export function ReassignManagerPalette({
  open,
  onOpenChange,
  employee,
  excludedIds,
  onSelect,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  employee: ChartEmployee | null
  excludedIds: Set<string>
  onSelect: (managerId: string | null, managerLabel: string) => void
}) {
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 250)

  useEffect(() => {
    if (!open) setSearch('')
  }, [open])

  const { data: options = [], isFetching } = useQuery({
    queryKey: ['employees', 'manager-search', debouncedSearch],
    queryFn: () => searchEmployees(debouncedSearch),
    enabled: open,
    placeholderData: (previous) => previous,
  })

  if (!employee) return null
  const fullName = `${employee.first_name} ${employee.last_name}`

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Reassign ${fullName}'s manager`}
      description="Search for a new manager, or clear it to make them a root."
    >
      <CommandInput
        placeholder={`Choose ${fullName}'s new manager...`}
        value={search}
        onValueChange={setSearch}
      />
      <CommandList>
        <CommandEmpty>{isFetching ? 'Searching…' : 'No employees found.'}</CommandEmpty>
        <CommandGroup>
          <CommandItem onSelect={() => onSelect(null, 'no manager')}>
            No manager (make root)
          </CommandItem>
          {options.map((option) => {
            const isSelf = option.id === employee.id
            const disabled = excludedIds.has(option.id)
            return (
              <CommandItem
                key={option.id}
                value={option.id}
                disabled={disabled}
                onSelect={() => {
                  if (disabled) return
                  onSelect(option.id, `${option.first_name} ${option.last_name}`)
                }}
              >
                <span className="flex flex-1 flex-col">
                  <span>
                    {option.first_name} {option.last_name}
                  </span>
                  {disabled && (
                    <span className="text-xs text-muted-foreground">
                      {isSelf
                        ? "An employee can't manage themselves"
                        : 'Would create a reporting cycle'}
                    </span>
                  )}
                </span>
                <span className="text-xs text-muted-foreground">{option.employee_number}</span>
              </CommandItem>
            )
          })}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
