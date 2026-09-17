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
