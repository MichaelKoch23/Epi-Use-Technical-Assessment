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
import { apiClient } from '@/lib/apiClient'
import { useDebouncedValue } from '@/lib/useDebouncedValue'
import { cn } from '@/lib/utils'

async function searchEmployees(q: string) {
  const { data, error } = await apiClient.GET('/api/v1/employees', {
    params: {
      query: { q: q || undefined, page: 1, page_size: 8, sort: 'last_name', order: 'asc' },
    },
  })
  if (error) return []
  return data.items
}

async function fetchExcludedIds(employeeId: string): Promise<Set<string>> {
  const { data, error } = await apiClient.GET('/api/v1/employees/{employee_id}/subtree', {
    params: { path: { employee_id: employeeId } },
  })
  if (error) return new Set([employeeId])
  return new Set([employeeId, ...data.map((node) => node.employee.id)])
}

export function ManagerPicker({
  value,
  label,
  onChange,
  excludeEmployeeId,
  clearLabel = 'No manager',
  triggerAriaLabel,
}: {
  value: string
  label: string
  onChange: (id: string, label: string) => void
  excludeEmployeeId?: string
  clearLabel?: string
  triggerAriaLabel?: string
}) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 250)

  const { data: options = [], isFetching } = useQuery({
    queryKey: ['employees', 'manager-search', debouncedSearch],
    queryFn: () => searchEmployees(debouncedSearch),
    enabled: open,
    placeholderData: (previous) => previous,
  })

  const { data: excludedIds } = useQuery({
    queryKey: ['employees', 'manager-exclude', excludeEmployeeId],
    queryFn: () => fetchExcludedIds(excludeEmployeeId!),
    enabled: open && Boolean(excludeEmployeeId),
  })

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        aria-label={triggerAriaLabel}
        render={<Button variant="outline" className="w-full justify-between font-normal" />}
      >
        <span className={cn('truncate', !value && 'text-muted-foreground')}>
          {value ? label : clearLabel}
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
            <CommandEmpty>{isFetching ? 'Searching…' : 'No employees found.'}</CommandEmpty>
            <CommandGroup>
              {value && (
                <CommandItem
                  onSelect={() => {
                    onChange('', '')
                    setOpen(false)
                  }}
                >
                  <CheckIcon className="opacity-0" />
                  {clearLabel}
                </CommandItem>
              )}
              {options.map((employee) => {
                const isSelf = employee.id === excludeEmployeeId
                const disabled = excludedIds?.has(employee.id) ?? false
                return (
                  <CommandItem
                    key={employee.id}
                    value={employee.id}
                    disabled={disabled}
                    data-checked={employee.id === value}
                    onSelect={() => {
                      if (disabled) return
                      onChange(employee.id, `${employee.first_name} ${employee.last_name}`)
                      setOpen(false)
                    }}
                  >
                    <span className="flex flex-1 flex-col">
                      <span>
                        {employee.first_name} {employee.last_name}
                      </span>
                      {disabled && (
                        <span className="text-xs text-muted-foreground">
                          {isSelf
                            ? "An employee can't manage themselves"
                            : 'Would create a reporting cycle'}
                        </span>
                      )}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {employee.employee_number}
                    </span>
                  </CommandItem>
                )
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
