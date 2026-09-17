import { useState } from 'react'
import { EmployeeAvatar } from '@/components/employee-avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { DeleteEmployeeDialog } from '@/features/employees/DeleteEmployeeDialog'
import { EditEmployeeSheet } from '@/features/employees/EditEmployeeSheet'
import { formatCurrency, formatDate } from '@/features/employees/format'
import type { EmployeeListItem } from '@/features/employees/types'
import { AssignmentHistoryTimeline } from './AssignmentHistoryTimeline'
import { ReportingLineBreadcrumb } from './ReportingLineBreadcrumb'
import { hasSalary, type ChartEmployee } from './types'

function toListItemShape(
  employee: ChartEmployee,
  managerName: string | null,
  directReportCount: number
): EmployeeListItem {
  return {
    ...employee,
    manager_name: managerName,
    direct_report_count: directReportCount,
  } as EmployeeListItem
}

export function EmployeeDetailDrawer({
  employee,
  managerName,
  directReportCount,
  open,
  onOpenChange,
  onSelectAncestor,
  canEdit,
  asOf,
}: {
  employee: ChartEmployee | null
  managerName: string | null
  directReportCount: number
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelectAncestor: (id: string) => void
  canEdit: boolean
  asOf: string
}) {
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const listItem = employee ? toListItemShape(employee, managerName, directReportCount) : null

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="w-full sm:max-w-[420px]">
          {employee && (
            <>
              <SheetHeader>
                <SheetTitle className="sr-only">
                  {employee.first_name} {employee.last_name}
                </SheetTitle>
                <ReportingLineBreadcrumb
                  employeeId={employee.id}
                  employeeName={`${employee.first_name} ${employee.last_name}`}
                  asOf={asOf}
                  onSelect={onSelectAncestor}
                />
              </SheetHeader>

              <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4">
                <div className="flex items-center gap-3">
                  <EmployeeAvatar
                    avatarUrl={employee.avatar_url}
                    firstName={employee.first_name}
                    lastName={employee.last_name}
                    size={56}
                  />
                  <div className="min-w-0">
                    <div className="truncate text-lg font-semibold">
                      {employee.first_name} {employee.last_name}
                    </div>
                    <div className="truncate text-sm text-muted-foreground">
                      {employee.position}
                    </div>
                  </div>
                </div>

                <dl className="grid grid-cols-2 gap-x-3 gap-y-3 text-sm">
                  <div>
                    <dt className="text-muted-foreground">Employee no.</dt>
                    <dd>{employee.employee_number}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Email</dt>
                    <dd className="truncate">{employee.email}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Reports to</dt>
                    <dd>{managerName ?? <Badge variant="secondary">No manager</Badge>}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Direct reports</dt>
                    <dd>{directReportCount}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Birth date</dt>
                    <dd>{formatDate(employee.birth_date)}</dd>
                  </div>
                  {hasSalary(employee) && (
                    <div>
                      <dt className="text-muted-foreground">Salary</dt>
                      <dd>{formatCurrency(employee.salary, employee.currency)}</dd>
                    </div>
                  )}
                </dl>

                <AssignmentHistoryTimeline employeeId={employee.id} />
              </div>

              {canEdit && (
                <SheetFooter className="flex-row justify-end">
                  <Button variant="outline" onClick={() => setDeleteOpen(true)}>
                    Delete
                  </Button>
                  <Button onClick={() => setEditOpen(true)}>Edit</Button>
                </SheetFooter>
              )}
            </>
          )}
        </SheetContent>
      </Sheet>

      <EditEmployeeSheet employee={listItem} open={editOpen} onOpenChange={setEditOpen} />
      <DeleteEmployeeDialog
        employee={listItem}
        open={deleteOpen}
        onOpenChange={(next) => {
          setDeleteOpen(next)
          if (!next) onOpenChange(false)
        }}
      />
    </>
  )
}
