import { useRef, useState } from 'react'
import { CameraIcon, Trash2Icon, UploadIcon } from 'lucide-react'
import { toast } from 'sonner'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { EmployeeAvatar } from '@/components/employee-avatar'
import { cn } from '@/lib/utils'

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
const MAX_BYTES = 5 * 1024 * 1024

export function AvatarEditor({
  avatarUrl,
  firstName,
  lastName,
  size = 96,
  hasUpload,
  isBusy,
  onUpload,
  onRemove,
  layout = 'row',
  className,
}: {
  avatarUrl: string
  firstName: string
  lastName: string
  size?: number
  hasUpload: boolean
  isBusy: boolean
  onUpload: (file: File) => void
  onRemove: () => void
  layout?: 'row' | 'stack'
  className?: string
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [confirmRemove, setConfirmRemove] = useState(false)

  function pick(file: File | undefined) {
    if (!file) return
    if (!ACCEPTED_TYPES.includes(file.type)) {
      toast.error('Choose a JPEG, PNG, WebP or GIF image')
      return
    }
    if (file.size > MAX_BYTES) {
      toast.error('Images must be 5 MB or smaller')
      return
    }
    onUpload(file)
  }

  return (
    <div
      className={cn(
        'flex gap-4',
        layout === 'row' ? 'flex-wrap items-center' : 'flex-col items-center',
        className
      )}
    >
      <button
        type="button"
        aria-label={hasUpload ? 'Change photo' : 'Upload photo'}
        disabled={isBusy}
        onClick={() => inputRef.current?.click()}
        className="group relative shrink-0 rounded-full focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        <EmployeeAvatar
          avatarUrl={avatarUrl}
          firstName={firstName}
          lastName={lastName}
          size={size}
          className="text-2xl ring-4 ring-card"
        />
        <span
          className={cn(
            'absolute inset-0 grid place-items-center rounded-full bg-brand-primary/60 text-white transition-opacity',
            isBusy ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100'
          )}
        >
          {isBusy ? <Spinner className="size-6" label="Working" /> : <CameraIcon className="size-6" />}
        </span>
      </button>

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" disabled={isBusy} onClick={() => inputRef.current?.click()}>
          {isBusy ? <Spinner /> : <UploadIcon />} {hasUpload ? 'Change photo' : 'Upload photo'}
        </Button>
        {hasUpload && (
          <Button variant="ghost" size="sm" disabled={isBusy} onClick={() => setConfirmRemove(true)}>
            <Trash2Icon /> Remove
          </Button>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        className="hidden"
        onChange={(event) => {
          pick(event.target.files?.[0])
          event.target.value = ''
        }}
      />

      <ConfirmDialog
        open={confirmRemove}
        onOpenChange={setConfirmRemove}
        title="Remove this photo?"
        description={
          <>
            The uploaded photo for{' '}
            <span className="font-medium text-foreground">
              {firstName} {lastName}
            </span>{' '}
            is deleted. A Gravatar or the initials will be shown instead, and a new photo can be
            uploaded at any time.
          </>
        }
        confirmLabel="Remove photo"
        pendingLabel="Removing..."
        cancelLabel="Keep photo"
        isPending={isBusy}
        onConfirm={() => {
          setConfirmRemove(false)
          onRemove()
        }}
      />
    </div>
  )
}
