import { Loader2Icon } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * The one spinner in the app, so "something is happening" always looks the same.
 *
 * Under prefers-reduced-motion it slows down rather than stopping: a frozen
 * spinner reads as a hung request, which is the opposite of what it is for.
 */
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
