import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { SearchIcon } from 'lucide-react'
import { EmployeeAvatar } from '@/components/employee-avatar'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { apiClient, getActorId } from '@/lib/apiClient'
import { useDebouncedValue } from '@/lib/useDebouncedValue'
import type { ChartEmployee } from './types'

async function searchEmployees(q: string): Promise<ChartEmployee[]> {
  if (!q) return []
  const { data, error } = await apiClient.GET('/api/v1/employees', {
    params: {
      query: { q, page: 1, page_size: 8, sort: 'last_name', order: 'asc' },
      header: { 'X-Actor-Id': getActorId() ?? '' },
    },
  })
  if (error) return []
  return data.items
}

/** Search wired to the chart (§7.3): finding a person expands their
 * collapsed ancestors and centres the view on them — it never just filters
 * the canvas out from under the rest of the tree. */
export function ChartSearch({ onSelect }: { onSelect: (employee: ChartEmployee) => void }) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 250)

  const { data: results = [] } = useQuery({
    queryKey: ['employees', 'chart-search', debouncedSearch],
    queryFn: () => searchEmployees(debouncedSearch),
    enabled: open && debouncedSearch.length > 0,
  })

  return (
    <Popover open={open && results.length > 0} onOpenChange={setOpen}>
      <PopoverTrigger nativeButton={false} render={<div className="w-64" />}>
        <InputGroup className="w-full">
          <InputGroupAddon>
            <SearchIcon />
          </InputGroupAddon>
          <InputGroupInput
            type="search"
            aria-label="Find an employee in the chart"
            placeholder="Find in chart..."
            value={search}
            onFocus={() => setOpen(true)}
            onChange={(event) => {
              setSearch(event.target.value)
              setOpen(true)
            }}
          />
        </InputGroup>
      </PopoverTrigger>
      <PopoverContent className="w-(--anchor-width) p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput value={search} onValueChange={setSearch} className="sr-only" />
          <CommandList>
            <CommandEmpty>No employees found.</CommandEmpty>
            <CommandGroup>
              {results.map((employee) => (
                <CommandItem
                  key={employee.id}
                  value={employee.id}
                  onSelect={() => {
                    onSelect(employee)
                    setSearch('')
                    setOpen(false)
                  }}
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
                    <span className="text-xs text-muted-foreground">{employee.position}</span>
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
