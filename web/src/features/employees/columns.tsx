import { createColumnHelper } from '@tanstack/react-table'
import { MoreHorizontalIcon } from 'lucide-react'
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

// Maps a column id to the `sort` query value the API accepts for it -
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
// so each element's inferred `TValue` survives instead of being widened -
// a plain array here fails `useTable`'s columns assignability check.
//
// §9.2/§9.3: a viewer's response payload never has a `salary` key at all,
// so the column itself is omitted rather than rendered with a "Restricted"
// placeholder - the capability flag from `/auth/me` decides this once, up
// front, rather than every row re-deriving it from `hasSalary`.
export function buildEmployeeColumns(canViewSalary: boolean) {
  return columnHelper.columns([
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
            avatarUrl={employee.avatar_url}
            firstName={employee.first_name}
            lastName={employee.last_name}
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
  ...(canViewSalary
    ? [
        columnHelper.display({
          id: 'salary',
          header: () => <span className="block text-right">Salary</span>,
          cell: ({ row }) => {
            const employee = row.original
            return (
              <div className="text-right tabular-nums">
                {hasSalary(employee) && formatCurrency(employee.salary, employee.currency)}
              </div>
            )
          },
        }),
      ]
    : []),
  columnHelper.accessor('direct_report_count', {
    id: 'direct_report_count',
    header: () => <span className="block text-right">Reports</span>,
    cell: ({ getValue }) => <div className="text-right tabular-nums">{getValue()}</div>,
  }),
  columnHelper.display({
    id: 'actions',
    header: '',
    cell: ({ row, table }) => {
      const employee = row.original
      const meta = table.options.meta!
      return (
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />}>
            <MoreHorizontalIcon className="size-4" />
            <span className="sr-only">Row actions</span>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {meta.showRestore ? (
              meta.canEdit && (
                <DropdownMenuItem onClick={() => meta.onRestore(employee)}>
                  Restore
                </DropdownMenuItem>
              )
            ) : (
              <>
                <DropdownMenuItem render={<Link to={`/employees/${employee.id}`} />}>
                  View details
                </DropdownMenuItem>
                {meta.canEdit && (
                  <>
                    <DropdownMenuItem onClick={() => meta.onEdit(employee)}>Edit</DropdownMenuItem>
                    <DropdownMenuItem variant="destructive" onClick={() => meta.onDelete(employee)}>
                      Delete
                    </DropdownMenuItem>
                  </>
                )}
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      )
    },
  }),
  ])
}
