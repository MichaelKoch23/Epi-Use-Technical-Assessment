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

export const SORTABLE_COLUMN_IDS: Partial<Record<string, string>> = {
  name: 'last_name',
  employee_number: 'employee_number',
  position: 'position',
  birth_date: 'birth_date',
  salary: 'salary',
}

export const NUMERIC_COLUMN_IDS: ReadonlySet<string> = new Set([
  'salary',
  'direct_report_count',
])

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
          header: 'Salary',
          cell: ({ row }) => {
            const employee = row.original
            return (
              <span className="tabular-nums">
                {hasSalary(employee) && formatCurrency(employee.salary, employee.currency)}
              </span>
            )
          },
        }),
      ]
    : []),
  columnHelper.accessor('direct_report_count', {
    id: 'direct_report_count',
    header: 'Reports',
    cell: ({ getValue }) => <span className="tabular-nums">{getValue()}</span>,
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
