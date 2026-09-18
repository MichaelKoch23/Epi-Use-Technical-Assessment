import { useRef, type ReactNode } from 'react'
import {
  AlertDialog,
  AlertDialogBody,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'

/**
 * Asks before anything that writes. Opens with focus on Cancel, per the style
 * guide's rule for destructive dialogs, so Enter never confirms by accident.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  confirmLabel,
  pendingLabel,
  cancelLabel = 'Keep as is',
  variant = 'destructive',
  isPending = false,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: ReactNode
  /** Extra detail - the rows about to change, the name being removed. */
  children?: ReactNode
  confirmLabel: string
  pendingLabel?: string
  cancelLabel?: string
  variant?: 'destructive' | 'default'
  isPending?: boolean
  onConfirm: () => void
}) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent initialFocus={cancelRef}>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
        </AlertDialogHeader>

        <AlertDialogBody>
          <AlertDialogDescription>{description}</AlertDialogDescription>
          {children}
        </AlertDialogBody>

        <AlertDialogFooter>
          <AlertDialogCancel ref={cancelRef} disabled={isPending}>
            {cancelLabel}
          </AlertDialogCancel>
          <Button variant={variant} onClick={onConfirm} disabled={isPending}>
            {isPending ? (
              <>
                <Spinner /> {pendingLabel ?? confirmLabel}
              </>
            ) : (
              confirmLabel
            )}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
