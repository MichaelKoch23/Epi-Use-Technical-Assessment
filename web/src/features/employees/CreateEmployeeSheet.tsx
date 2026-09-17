import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { FormProvider, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { getErrorMessage } from '@/lib/apiError'
import { EmployeeFormFields } from './EmployeeFormFields'
import { useCreateEmployeeMutation } from './mutations'
import {
  employeeCreateSchema,
  type EmployeeCreateFormInput,
  type EmployeeCreateFormValues,
} from './schema'

const DEFAULT_VALUES: EmployeeCreateFormInput = {
  employee_number: '',
  first_name: '',
  last_name: '',
  email: '',
  birth_date: '',
  position: '',
  salary: 0,
  currency: 'ZAR',
  avatar_override_url: '',
  manager_id: '',
}

export function CreateEmployeeSheet({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [managerLabel, setManagerLabel] = useState('')
  const form = useForm<EmployeeCreateFormInput, unknown, EmployeeCreateFormValues>({
    resolver: zodResolver(employeeCreateSchema),
    defaultValues: DEFAULT_VALUES,
  })
  const createEmployee = useCreateEmployeeMutation()

  useEffect(() => {
    if (open) {
      form.reset(DEFAULT_VALUES)
      setManagerLabel('')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await createEmployee.mutateAsync({
        employee_number: values.employee_number,
        first_name: values.first_name,
        last_name: values.last_name,
        email: values.email,
        birth_date: values.birth_date,
        position: values.position,
        salary: values.salary,
        currency: values.currency,
        manager_id: values.manager_id || null,
        avatar_override_url: values.avatar_override_url || null,
      })
      toast.success(`${values.first_name} ${values.last_name} was created`)
      onOpenChange(false)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to create employee'))
    }
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-[420px]">
        <SheetHeader>
          <SheetTitle>Add employee</SheetTitle>
        </SheetHeader>

        <FormProvider {...form}>
          <form
            id="create-employee-form"
            onSubmit={onSubmit}
            className="flex-1 overflow-y-auto px-4"
          >
            <EmployeeFormFields
              showManager
              managerLabel={managerLabel}
              onManagerLabelChange={setManagerLabel}
            />
          </form>
        </FormProvider>

        <SheetFooter className="flex-row justify-end">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="create-employee-form" disabled={createEmployee.isPending}>
            {createEmployee.isPending ? 'Creating…' : 'Create employee'}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
