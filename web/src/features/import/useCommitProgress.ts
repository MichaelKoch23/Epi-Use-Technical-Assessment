import { useEffect, useState } from 'react'

const LONG_RUNNING_SECONDS = 15

export function useCommitProgress(isCommitting: boolean) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!isCommitting) return
    const startedAt = Date.now()
    const id = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
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

export function useUnloadWarning(active: boolean) {
  useEffect(() => {
    if (!active) return
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [active])
}
