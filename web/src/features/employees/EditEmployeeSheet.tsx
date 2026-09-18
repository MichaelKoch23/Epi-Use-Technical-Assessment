import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Label } from '@/components/ui/label'
import { getErrorMessage } from '@/lib/apiError'
import { EmployeeFormFields } from './EmployeeFormFields'
import { formatDate } from './format'
import {
  fetchEmployee,
  useReassignManagerMutation,
  useUpdateEmployeeMutation,
  VersionConflict,
} from './mutations'
import { ManagerPicker } from './ManagerPicker'
import {
  employeeUpdateSchema,
  type EmployeeUpdateFormInput,
  type EmployeeUpdateFormValues,
} from './schema'
import type { EmployeeListItem } from './types'

const FIELD_LABELS: Record<keyof EmployeeUpdateFormInput, string> = {
  employee_number: 'Employee number',
  first_name: 'First name',
  last_name: 'Last name',
  email: 'Email',
  birth_date: 'Birth date',
  position: 'Position',
  salary: 'Salary',
  currency: 'Currency',
  avatar_override_url: 'Avatar URL',
}

interface EditableEmployee {
  employee_number: string
  first_name: string
  last_name: string
  email: string
  birth_date: string
  position: string
  currency: string
  avatar_override_url: string | null
  salary?: string
}

function toFormValues(employee: EditableEmployee): EmployeeUpdateFormInput {
  return {
    employee_number: employee.employee_number,
    first_name: employee.first_name,
    last_name: employee.last_name,
    email: employee.email,
    birth_date: employee.birth_date,
    position: employee.position,
    salary: employee.salary !== undefined ? Number(employee.salary) : 0,
    currency: employee.currency,
    avatar_override_url: employee.avatar_override_url ?? '',
  }
}

function displayValue(value: unknown, field: keyof EmployeeUpdateFormInput): string {
  if (field === 'birth_date') return formatDate(String(value))
  if (value === '' || value == null) return '-'
  return String(value)
}

export function EditEmployeeSheet({
  employee,
  open,
  onOpenChange,
}: {
  employee: EmployeeListItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [version, setVersion] = useState(employee?.version ?? 1)
  const [managerId, setManagerId] = useState(employee?.manager_id ?? '')
  const [managerLabel, setManagerLabel] = useState(employee?.manager_name ?? '')
  const [conflict, setConflict] = useState<{
    serverValues: EmployeeUpdateFormInput
    serverVersion: number
  } | null>(null)

  const form = useForm<EmployeeUpdateFormInput, unknown, EmployeeUpdateFormValues>({
    resolver: zodResolver(employeeUpdateSchema),
    values: employee ? toFormValues(employee) : undefined,
  })
  const updateEmployee = useUpdateEmployeeMutation()
  const reassignManager = useReassignManagerMutation()

  useEffect(() => {
    if (employee) {
      setVersion(employee.version)
      setManagerId(employee.manager_id ?? '')
      setManagerLabel(employee.manager_name ?? '')
      setConflict(null)
    }
  }, [employee])

  const submitWithVersion = async (values: EmployeeUpdateFormValues, asOfVersion: number) => {
    if (!employee) return
    try {
      const updated = await updateEmployee.mutateAsync({
        id: employee.id,
        version: asOfVersion,
        body: {
          employee_number: values.employee_number,
          first_name: values.first_name,
          last_name: values.last_name,
          email: values.email,
          birth_date: values.birth_date,
          position: values.position,
          salary: values.salary,
          currency: values.currency,
          avatar_override_url: values.avatar_override_url || null,
        },
      })

      if (managerId !== (employee.manager_id ?? '')) {
        try {
          await reassignManager.mutateAsync({
            id: employee.id,
            version: updated.version,
            managerId: managerId || null,
          })
        } catch (reassignError) {
          toast.error(
            getErrorMessage(reassignError, 'Saved the other changes, but the manager change failed')
          )
          setConflict(null)
          onOpenChange(false)
          return
        }
      }

      toast.success('Changes saved', {
        description: `${values.first_name} ${values.last_name}'s record has been updated.`,
      })
      setConflict(null)
      onOpenChange(false)
    } catch (error) {
      if (error instanceof VersionConflict) {
        const server = await fetchEmployee(error.employeeId)
        setConflict({
          serverValues: toFormValues({ ...server, salary: 'salary' in server ? String(server.salary) : undefined }),
          serverVersion: server.version,
        })
        return
      }
      toast.error('Could not save these changes', {
        description: getErrorMessage(error, 'The record is unchanged. Try again in a moment.'),
      })
    }
  }

  const onSubmit = form.handleSubmit((values) => submitWithVersion(values, version))

  const keepMine = () => {
    if (!conflict) return
    void form.handleSubmit((values) => submitWithVersion(values, conflict.serverVersion))()
  }

  const useTheirs = () => {
    if (!conflict) return
    form.reset(conflict.serverValues)
    setVersion(conflict.serverVersion)
    setConflict(null)
  }

  const changedFields = conflict
    ? (Object.keys(FIELD_LABELS) as (keyof EmployeeUpdateFormInput)[]).filter(
        (field) => String(form.getValues(field)) !== String(conflict.serverValues[field])
      )
    : []

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="w-full sm:max-w-[420px]">
          <SheetHeader>
            <SheetTitle>Edit employee</SheetTitle>
          </SheetHeader>

          <FormProvider {...form}>
            <form
              id="edit-employee-form"
              onSubmit={onSubmit}
              className="flex-1 overflow-y-auto px-4"
            >
              <EmployeeFormFields showManager={false} />

              {employee && (
                <div className="mt-4 flex flex-col gap-1.5">
                  <Label>Reports to</Label>
                  <ManagerPicker
                    value={managerId}
                    label={managerLabel}
                    excludeEmployeeId={employee.id}
                    triggerAriaLabel="Reports to"
                    onChange={(id, label) => {
                      setManagerId(id)
                      setManagerLabel(label)
                    }}
                  />
                </div>
              )}
            </form>
          </FormProvider>

          <SheetFooter className="flex-row justify-end">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" form="edit-employee-form" disabled={updateEmployee.isPending}>
              {updateEmployee.isPending ? (
                <>
                  <Spinner /> Saving...
                </>
              ) : (
                'Save changes'
              )}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      <Dialog open={Boolean(conflict)} onOpenChange={(next) => !next && setConflict(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>This record changed since you opened it</DialogTitle>
            <DialogDescription>
              Someone else saved changes to this employee while you were editing. Choose which
              version to keep for the fields that differ.
            </DialogDescription>
          </DialogHeader>

          <DialogBody>
            {conflict && (
              <div className="flex flex-col gap-3 text-sm">
                <div className="grid grid-cols-[1fr_1fr_1fr] gap-2 font-medium text-muted-foreground">
                  <span>Field</span>
                  <span>Your version</span>
                  <span>Current version</span>
                </div>
                {changedFields.length === 0 ? (
                  <p className="text-muted-foreground">
                    No overlapping fields differ - you can safely keep your changes.
                  </p>
                ) : (
                  changedFields.map((field) => (
                    <div key={field} className="grid grid-cols-[1fr_1fr_1fr] gap-2">
                      <span className="text-muted-foreground">{FIELD_LABELS[field]}</span>
                      <span className="font-medium">
                        {displayValue(form.getValues(field), field)}
                      </span>
                      <span>{displayValue(conflict.serverValues[field], field)}</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </DialogBody>

          <DialogFooter>
            <Button variant="outline" onClick={useTheirs}>
              Use current version
            </Button>
            <Button onClick={keepMine} disabled={updateEmployee.isPending}>
              Keep my changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
