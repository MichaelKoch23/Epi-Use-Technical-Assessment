import { useEffect, useMemo, useRef, useState } from 'react'
import { useTable } from '@tanstack/react-table'
import { ChevronDownIcon, ChevronUpIcon, PlusIcon, SearchIcon, XIcon } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/components/ui/input-group'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuth } from '@/features/auth/useAuth'
import { getErrorMessage } from '@/lib/apiError'
import type { EmployeeListFilters } from '@/lib/queryKeys'
import { cn } from '@/lib/utils'
import { useDebouncedValue } from '@/lib/useDebouncedValue'
import { buildEmployeeColumns, SORTABLE_COLUMN_IDS } from './columns'
import { CreateEmployeeSheet } from './CreateEmployeeSheet'
import { DeleteEmployeeDialog } from './DeleteEmployeeDialog'
import { EditEmployeeSheet } from './EditEmployeeSheet'
import { EmployeesPagination } from './EmployeesPagination'
import { FilterChipRow } from './FilterChipRow'
import { getFilterChips } from './filterChips'
import { FilterPopover } from './FilterPopover'
import { useRestoreEmployeeMutation } from './mutations'
import { employeeTableFeatures, type EmployeeTableMeta } from './tableFeatures'
import type { EmployeeListItem } from './types'
import { useEmployeesListQuery } from './useEmployeesListQuery'
import { useEmployeesViewState } from './useEmployeesViewState'

const EMPTY_EMPLOYEES: EmployeeListItem[] = []

function toApiFilters(state: ReturnType<typeof useEmployeesViewState>['state']): EmployeeListFilters {
  return {
    q: state.q || undefined,
    position: state.position || undefined,
    manager_id: state.managerId || undefined,
    min_salary: state.minSalary || undefined,
    max_salary: state.maxSalary || undefined,
    min_birth_date: state.minBirthDate || undefined,
    max_birth_date: state.maxBirthDate || undefined,
    sort: state.sort,
    order: state.order,
    page: state.page,
    page_size: state.pageSize,
    deleted: state.deleted || undefined,
  }
}

export function EmployeesListPage() {
  const { canViewSalary, canEdit } = useAuth()
  const { state, applyFilters, clearFilters, setSort, setPage, setPageSize, setDeleted } =
    useEmployeesViewState()
  const columns = useMemo(() => buildEmployeeColumns(canViewSalary), [canViewSalary])

  const [createOpen, setCreateOpen] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState<EmployeeListItem | null>(null)
  const [deletingEmployee, setDeletingEmployee] = useState<EmployeeListItem | null>(null)
  const restoreEmployee = useRestoreEmployeeMutation()

  const [searchInput, setSearchInput] = useState(state.q)
  const debouncedSearch = useDebouncedValue(searchInput, 300)

  // Tracks the last value *this component* pushed into the URL, so the
  // sync-back effect below can tell "the URL caught up with what I just
  // typed" (ignore — `state.q` update lags a render behind `applyFilters`,
  // and treating that echo as external would overwrite a newer local edit)
  // from "the URL changed for some other reason, e.g. the back button"
  // (apply it).
  const lastAppliedQRef = useRef(state.q)

  useEffect(() => {
    lastAppliedQRef.current = debouncedSearch
    applyFilters({ q: debouncedSearch })
    // Only the debounced value should trigger a URL update.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch])

  useEffect(() => {
    if (state.q !== lastAppliedQRef.current) {
      lastAppliedQRef.current = state.q
      setSearchInput(state.q)
    }
  }, [state.q])

  const filters = toApiFilters(state)
  const query = useEmployeesListQuery(filters)

  useEffect(() => {
    if (!query.isError) return
    const message = getErrorMessage(query.error, 'Failed to load employees')
    toast.error(message)
    if (message.toLowerCase().includes('hr_admin')) {
      applyFilters({ minSalary: '', maxSalary: '' })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query.error])

  const employees = query.data?.items ?? EMPTY_EMPLOYEES
  const salaryFilterAllowed = canViewSalary

  const meta: EmployeeTableMeta = {
    onEdit: setEditingEmployee,
    onDelete: setDeletingEmployee,
    onRestore: (employee) => {
      restoreEmployee.mutate(employee.id, {
        onSuccess: () => toast.success(`${employee.first_name} ${employee.last_name} was restored`),
        onError: (error) => toast.error(getErrorMessage(error, 'Failed to restore employee')),
      })
    },
    showRestore: state.deleted,
    canEdit,
  }

  // Server owns sorting, filtering and pagination entirely (§ manual mode);
  // the table gets one already-processed page and never reprocesses it.
  const table = useTable({
    features: employeeTableFeatures,
    columns,
    data: employees,
    getRowId: (row) => row.id,
    manualSorting: true,
    manualFiltering: true,
    manualPagination: true,
    rowCount: query.data?.total ?? 0,
    meta,
  })

  const chips = getFilterChips(state, applyFilters)
  const hasAnyFilter = chips.length > 0

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold">Employees</h1>
          <p className="text-muted-foreground">Browse, search and filter the full roster.</p>
        </div>
        {canEdit && (
          <Button onClick={() => setCreateOpen(true)}>
            <PlusIcon /> Add employee
          </Button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <InputGroup className="max-w-sm">
          <InputGroupAddon>
            <SearchIcon />
          </InputGroupAddon>
          <InputGroupInput
            type="search"
            aria-label="Search employees"
            placeholder="Search by name..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
          {searchInput && (
            <InputGroupAddon align="inline-end">
              <InputGroupButton
                aria-label="Clear search"
                size="icon-xs"
                onClick={() => setSearchInput('')}
              >
                <XIcon />
              </InputGroupButton>
            </InputGroupAddon>
          )}
        </InputGroup>

        <FilterPopover
          filters={state}
          activeCount={chips.length}
          salaryFilterAllowed={salaryFilterAllowed}
          onApply={applyFilters}
        />

        {hasAnyFilter && (
          <button
            type="button"
            className="text-sm text-muted-foreground underline-offset-2 hover:underline"
            onClick={clearFilters}
          >
            Clear all
          </button>
        )}

        <Button
          variant="outline"
          className={cn('ml-auto', state.deleted && 'border-primary text-primary')}
          onClick={() => setDeleted(!state.deleted)}
        >
          {state.deleted ? 'Showing deleted' : 'Deleted'}
        </Button>
      </div>

      <FilterChipRow chips={chips} />

      <div className="overflow-hidden rounded-md border border-border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const sortField = SORTABLE_COLUMN_IDS[header.column.id]
                  const sortable =
                    sortField && (sortField !== 'salary' || salaryFilterAllowed)
                  const isSorted = state.sort === sortField

                  return (
                    <TableHead key={header.id}>
                      {sortable ? (
                        <button
                          type="button"
                          className="inline-flex items-center gap-1 hover:text-foreground"
                          onClick={() => setSort(sortField)}
                        >
                          <table.FlexRender header={header} />
                          {isSorted &&
                            (state.order === 'asc' ? (
                              <ChevronUpIcon className="size-3.5" />
                            ) : (
                              <ChevronDownIcon className="size-3.5" />
                            ))}
                        </button>
                      ) : (
                        <table.FlexRender header={header} />
                      )}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {query.isPending ? (
              Array.from({ length: state.pageSize > 10 ? 10 : state.pageSize }).map((_, i) => (
                <TableRow key={`skeleton-${i}`}>
                  {columns.map((column) => (
                    <TableCell key={column.id}>
                      <Skeleton className="h-5 w-full max-w-32" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                  {query.isError ? 'Could not load employees.' : 'No employees match these filters.'}
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getAllCells().map((cell) => (
                    <TableCell key={cell.id}>
                      <table.FlexRender cell={cell} />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <EmployeesPagination
        page={state.page}
        pageSize={state.pageSize}
        total={query.data?.total ?? 0}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
      />

      <CreateEmployeeSheet open={createOpen} onOpenChange={setCreateOpen} />
      <EditEmployeeSheet
        employee={editingEmployee}
        open={Boolean(editingEmployee)}
        onOpenChange={(open) => !open && setEditingEmployee(null)}
      />
      <DeleteEmployeeDialog
        employee={deletingEmployee}
        open={Boolean(deletingEmployee)}
        onOpenChange={(open) => !open && setDeletingEmployee(null)}
      />
    </div>
  )
}
