import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { EmployeeAvatar } from '@/components/employee-avatar'
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { searchKeys } from '@/lib/queryKeys'
import { useDebouncedValue } from '@/lib/useDebouncedValue'
import { searchAll } from './api'

/**
 * The topbar search button's command palette (§6.2 FR-7, `GET /search`).
 * Selecting a result focuses that employee in the org chart, reusing the
 * `?focus={id}` deep link the analytics anomaly panel and branch explorer
 * already navigate to.
 */
export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 250)

  const { data: results = [], isFetching } = useQuery({
    queryKey: searchKeys.results(debouncedSearch),
    queryFn: () => searchAll(debouncedSearch),
    enabled: open && debouncedSearch.length > 0,
    placeholderData: (previous) => previous,
  })

  // Never reopen on a stale query — a fresh open should start from empty,
  // not wherever the last search left off.
  useEffect(() => {
    if (!open) setSearch('')
  }, [open])

  const selectResult = (id: string) => {
    onOpenChange(false)
    navigate(`/chart?focus=${id}`)
  }

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Search"
      description="Find an employee by name, employee number or position"
    >
      {/* Server-side filtering (§ FR-7): `q` already narrowed `results`,
       * so cmdk must not re-filter them client-side against its own
       * fuzzy match on `value` — same reasoning as `ManagerPicker`. */}
      <Command shouldFilter={false}>
        <CommandInput
          placeholder="Search by name, employee number or position..."
          value={search}
          onValueChange={setSearch}
        />
        <CommandList>
          <CommandEmpty>
            {search.length === 0
              ? 'Start typing to search employees.'
              : isFetching
                ? 'Searching…'
                : 'No employees found.'}
          </CommandEmpty>
          <CommandGroup>
            {results.map((employee) => (
              <CommandItem
                key={employee.id}
                value={employee.id}
                onSelect={() => selectResult(employee.id)}
              >
                <EmployeeAvatar
                  avatarUrl={employee.avatar_url}
                  firstName={employee.first_name}
                  lastName={employee.last_name}
                  size={24}
                />
                <span className="flex flex-1 flex-col">
                  <span>
                    {employee.first_name} {employee.last_name}
                  </span>
                  {/* `text-muted-foreground` on `CommandItem`'s own
                   * `data-selected:bg-muted` background falls just under
                   * AA (4.34:1) — `group-data-selected` bumps it to the
                   * full-contrast foreground colour on the highlighted row. */}
                  <span className="text-xs text-muted-foreground group-data-selected/command-item:text-foreground">
                    {employee.position}
                  </span>
                </span>
                <span className="text-xs text-muted-foreground group-data-selected/command-item:text-foreground">
                  {employee.employee_number}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  )
}
