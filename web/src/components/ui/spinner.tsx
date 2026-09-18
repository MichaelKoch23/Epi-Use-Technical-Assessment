import { Loader2Icon } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Spinner({ className, label }: { className?: string; label?: string }) {
  return (
    <>
      <Loader2Icon
        aria-hidden="true"
        className={cn('size-4 shrink-0 animate-spin motion-reduce:[animation-duration:2s]', className)}
      />
      {label && <span className="sr-only">{label}</span>}
    </>
  )
}
