import { useEffect, useState } from 'react'

/**
 * Elapsed seconds while a commit is in flight, and a warning once it runs long.
 *
 * A commit is one POST with no progress signal - the server writes every row in
 * a single transaction and answers once. There is nothing honest to fill a
 * progress bar with, so the page shows elapsed time instead: enough to tell a
 * slow write apart from a hung one, without inventing a percentage.
 */
const LONG_RUNNING_SECONDS = 15

export function useCommitProgress(isCommitting: boolean) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!isCommitting) return
    const startedAt = Date.now()
    const id = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    // Cleared on the way out rather than on the way in, so the next commit
    // starts from zero without this render having to reset anything.
    return () => {
      window.clearInterval(id)
      setElapsed(0)
    }
  }, [isCommitting])

  return { elapsed, isLongRunning: elapsed >= LONG_RUNNING_SECONDS }
}

export function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`
}

/**
 * Warn before a reload or a tab close takes the commit's connection with it.
 *
 * The write itself is one transaction, so an abandoned request does not leave
 * half an import behind - but it does leave the person with no idea whether
 * their file landed, which is worth one dialog to avoid.
 */
export function useUnloadWarning(active: boolean) {
  useEffect(() => {
    if (!active) return
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      // Set for older browsers; modern ones show their own wording.
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [active])
}
