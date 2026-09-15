import { createColumnHelper } from '@tanstack/react-table'
import { LockIcon, MoreHorizontalIcon } from 'lucide-react'
import { Link } from 'react-router'
import { EmployeeAvatar } from '@/components/employee-avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { formatCurrency, formatDate } from './format'
import { employeeTableFeatures } from './tableFeatures'
import { hasSalary, type EmployeeListItem } from './types'

const columnHelper = createColumnHelper<typeof employeeTableFeatures, EmployeeListItem>()

// Maps a column id to the `sort` query value the API accepts for it —
// absence from this map means the column can't be sorted server-side
// (the backend's SORTABLE_COLUMNS allow-list has no equivalent).
export const SORTABLE_COLUMN_IDS: Partial<Record<string, string>> = {
  name: 'last_name',
  employee_number: 'employee_number',
  position: 'position',
  birth_date: 'birth_date',
  salary: 'salary',
}

// Wrapped in `columnHelper.columns(...)` rather than a plain array literal
// so each element's inferred `TValue` survives instead of being widened —
// a plain array here fails `useTable`'s columns assignability check.
export const employeeColumns = columnHelper.columns([
  columnHelper.display({
    id: 'name',
    header: 'Employee',
    cell: ({ row }) => {
      const employee = row.original
      return (
        <Link
          to={`/employees/${employee.id}`}
          className="flex items-center gap-2 text-foreground no-underline hover:underline"
        >
          <EmployeeAvatar
            email={employee.email}
            firstName={employee.first_name}
            lastName={employee.last_name}
            overrideUrl={employee.avatar_override_url}
          />
          <span className="font-medium">
            {employee.first_name} {employee.last_name}
          </span>
        </Link>
      )
    },
  }),
  columnHelper.accessor('employee_number', {
    id: 'employee_number',
    header: 'Employee no.',
  }),
  columnHelper.accessor('position', {
    id: 'position',
    header: 'Position',
  }),
  columnHelper.display({
    id: 'reports_to',
    header: 'Reports to',
    cell: ({ row }) =>
      row.original.manager_name ?? <Badge variant="secondary">No manager</Badge>,
  }),
  columnHelper.accessor('birth_date', {
    id: 'birth_date',
    header: 'Birth date',
    cell: ({ getValue }) => formatDate(getValue()),
  }),
  columnHelper.display({
    id: 'salary',
    header: () => <span className="block text-right">Salary</span>,
    cell: ({ row }) => {
      const employee = row.original
      return (
        <div className="text-right tabular-nums">
          {hasSalary(employee) ? (
            formatCurrency(employee.salary, employee.currency)
          ) : (
            <span className="inline-flex items-center gap-1 text-muted-foreground">
              <LockIcon className="size-3.5" /> Restricted
            </span>
          )}
        </div>
      )
    },
  }),
  columnHelper.accessor('direct_report_count', {
    id: 'direct_report_count',
    header: () => <span className="block text-right">Reports</span>,
    cell: ({ getValue }) => <div className="text-right tabular-nums">{getValue()}</div>,
  }),
  columnHelper.display({
    id: 'actions',
    header: '',
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />}>
          <MoreHorizontalIcon className="size-4" />
          <span className="sr-only">Row actions</span>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem render={<Link to={`/employees/${row.original.id}`} />}>
            View details
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  }),
])
