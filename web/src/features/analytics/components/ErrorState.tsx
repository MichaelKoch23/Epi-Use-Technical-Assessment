import { AlertTriangleIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

/** A named failure plus a retry — never a bare toast with the section left
 * blank (§ analytics states). */
export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry: () => void
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-md border border-status-critical/30 bg-status-critical/5 px-6 py-10 text-center">
      <AlertTriangleIcon className="size-6 text-status-critical" aria-hidden="true" />
      <div>
        <p className="text-sm font-medium text-foreground">{message}</p>
        <p className="text-sm text-muted-foreground">Nothing was changed.</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Retry
      </Button>
    </div>
  )
}
