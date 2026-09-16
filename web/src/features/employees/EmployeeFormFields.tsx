import { Controller, useFormContext } from 'react-hook-form'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ManagerPicker } from './ManagerPicker'
import type { EmployeeCreateFormInput } from './schema'

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className="text-xs text-destructive">{message}</p>
}

/** Shared field set for the create and edit forms - everything
 * `EmployeeCreate`/`EmployeeUpdate` have in common. `manager_id` is only
 * rendered when present in the form's values (create only: the API
 * deliberately excludes it from `EmployeeUpdate`, since reassignment
 * carries its own cycle-prevention invariant and lives on its own
 * endpoint - see `PUT /employees/{id}/manager`). */
export function EmployeeFormFields({
  showManager,
  managerLabel,
  onManagerLabelChange,
}: {
  showManager: boolean
  managerLabel?: string
  onManagerLabelChange?: (label: string) => void
}) {
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<EmployeeCreateFormInput>()

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="employee_number">Employee number</Label>
          <Input id="employee_number" {...register('employee_number')} />
          <FieldError message={errors.employee_number?.message} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="position">Position</Label>
          <Input id="position" {...register('position')} />
          <FieldError message={errors.position?.message} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="first_name">First name</Label>
          <Input id="first_name" {...register('first_name')} />
          <FieldError message={errors.first_name?.message} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="last_name">Last name</Label>
          <Input id="last_name" {...register('last_name')} />
          <FieldError message={errors.last_name?.message} />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" {...register('email')} />
        <FieldError message={errors.email?.message} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="birth_date">Birth date</Label>
          <Input id="birth_date" type="date" {...register('birth_date')} />
          <FieldError message={errors.birth_date?.message} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="avatar_override_url">Avatar URL (optional)</Label>
          <Input id="avatar_override_url" type="url" {...register('avatar_override_url')} />
          <FieldError message={errors.avatar_override_url?.message} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="salary">Salary</Label>
          <Input id="salary" type="number" min={0} step="0.01" {...register('salary')} />
          <FieldError message={errors.salary?.message} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="currency">Currency</Label>
          <Input id="currency" maxLength={3} {...register('currency')} />
          <FieldError message={errors.currency?.message} />
        </div>
      </div>

      {showManager && (
        <div className="flex flex-col gap-1.5">
          <Label>Manager</Label>
          <Controller
            control={control}
            name="manager_id"
            render={({ field }) => (
              <ManagerPicker
                value={field.value ?? ''}
                label={managerLabel ?? ''}
                onChange={(id, label) => {
                  field.onChange(id)
                  onManagerLabelChange?.(label)
                }}
              />
            )}
          />
        </div>
      )}
    </div>
  )
}
