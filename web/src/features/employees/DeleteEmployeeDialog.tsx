import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { getErrorMessage } from '@/lib/apiError'
import { fetchDeletionPreview, useDeleteEmployeeMutation } from './mutations'
import type { EmployeeListItem } from './types'

const POLICIES = [
  {
    value: 'reparent',
    label: 'Reparent',
    description: 'Direct reports move up to this employee’s own manager.',
  },
  {
    value: 'promote_to_root',
    label: 'Promote to root',
    description: 'Direct reports become top-level (no manager).',
  },
  {
    value: 'cascade',
    label: 'Cascade delete',
    description: 'This employee and their entire subtree are deleted.',
  },
] as const

type Policy = (typeof POLICIES)[number]['value']

export function DeleteEmployeeDialog({
  employee,
  open,
  onOpenChange,
}: {
  employee: EmployeeListItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [policy, setPolicy] = useState<Policy>('reparent')
  const cancelRef = useRef<HTMLButtonElement>(null)
  const deleteEmployee = useDeleteEmployeeMutation()

  const previews = useQuery({
    queryKey: ['employees', 'deletion-preview', employee?.id],
    queryFn: async () => {
      const [reparent, promoteToRoot, cascade] = await Promise.all([
        fetchDeletionPreview(employee!.id, 'reparent'),
        fetchDeletionPreview(employee!.id, 'promote_to_root'),
        fetchDeletionPreview(employee!.id, 'cascade'),
      ])
      return { reparent, promote_to_root: promoteToRoot, cascade }
    },
    enabled: open && Boolean(employee),
  })

  // Fully controlled by the parent (no AlertDialogTrigger of its own to
  // fire `onOpenChange`) - a fresh target resets the chosen policy back
  // to the default rather than carrying over the previous employee's pick.
  useEffect(() => {
    if (employee) setPolicy('reparent')
  }, [employee])

  const confirmDelete = async () => {
    if (!employee) return
    try {
      await deleteEmployee.mutateAsync({ id: employee.id, policy })
      toast.success(`${employee.first_name} ${employee.last_name} was deleted`)
      onOpenChange(false)
    } catch (error) {
      toast.error(getErrorMessage(error, 'Failed to delete employee'))
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="sm:max-w-md" initialFocus={cancelRef}>
        <AlertDialogHeader>
          <AlertDialogTitle>
            Delete {employee ? `${employee.first_name} ${employee.last_name}` : 'employee'}?
          </AlertDialogTitle>
          <AlertDialogDescription>
            Choose what happens to their direct reports. This cannot be undone from here, but a
            deleted employee can still be restored from the Deleted filter.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <RadioGroup value={policy} onValueChange={(value) => setPolicy(value as Policy)}>
          {POLICIES.map((option) => {
            const count = previews.data?.[option.value]?.length
            return (
              <Label
                key={option.value}
                htmlFor={`policy-${option.value}`}
                className="flex cursor-pointer items-start gap-2 rounded-md border border-border p-3 font-normal has-data-checked:border-primary"
              >
                <RadioGroupItem value={option.value} id={`policy-${option.value}`} />
                <span className="flex flex-col gap-0.5">
                  <span className="flex items-center gap-2 font-medium">
                    {option.label}
                    <span className="text-xs font-normal text-muted-foreground">
                      {previews.isPending
                        ? 'Counting…'
                        : `${count ?? 0} employee${count === 1 ? '' : 's'} affected`}
                    </span>
                  </span>
                  <span className="text-xs text-muted-foreground">{option.description}</span>
                </span>
              </Label>
            )
          })}
        </RadioGroup>

        <AlertDialogFooter>
          <AlertDialogCancel ref={cancelRef}>Cancel</AlertDialogCancel>
          <Button variant="destructive" onClick={confirmDelete} disabled={deleteEmployee.isPending}>
            {deleteEmployee.isPending ? 'Deleting…' : 'Delete'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
