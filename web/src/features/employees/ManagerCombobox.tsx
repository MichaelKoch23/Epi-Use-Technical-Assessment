import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckIcon, ChevronsUpDownIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { apiClient, getActorId } from '@/lib/apiClient'
import { useDebouncedValue } from '@/lib/useDebouncedValue'
import { cn } from '@/lib/utils'

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

/** Async manager search-and-select (§ shadcn component map: "Manager
 * picker: command; async search"), reused here to drive the manager
 * filter rather than a raw manager_id typed into a text box. */
export function ManagerCombobox({
  value,
  label,
  onChange,
}: {
  value: string
  label: string
  onChange: (id: string, label: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 250)

  const { data: options = [] } = useQuery({
    queryKey: ['employees', 'manager-search', debouncedSearch],
    queryFn: () => searchEmployees(debouncedSearch),
    enabled: open,
  })

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={<Button variant="outline" className="w-full justify-between font-normal" />}
      >
        <span className={cn('truncate', !value && 'text-muted-foreground')}>
          {value ? label : 'Any manager'}
        </span>
        <ChevronsUpDownIcon className="size-4 shrink-0 opacity-50" />
      </PopoverTrigger>
      <PopoverContent className="w-(--anchor-width) p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search employees..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>No employees found.</CommandEmpty>
            <CommandGroup>
              {value && (
                <CommandItem
                  onSelect={() => {
                    onChange('', '')
                    setOpen(false)
                  }}
                >
                  <CheckIcon className="opacity-0" />
                  Any manager
                </CommandItem>
              )}
              {options.map((employee) => (
                <CommandItem
                  key={employee.id}
                  value={employee.id}
                  data-checked={employee.id === value}
                  onSelect={() => {
                    onChange(employee.id, `${employee.first_name} ${employee.last_name}`)
                    setOpen(false)
                  }}
                >
                  {employee.first_name} {employee.last_name}
                  <span className="ml-auto text-xs text-muted-foreground">
                    {employee.employee_number}
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
