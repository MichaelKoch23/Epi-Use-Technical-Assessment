import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

type HealthResponse = {
  status: string
  db: string
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Relative path: the SPA and API share an origin in production, so an
    // absolute URL like http://localhost:8080/... would break there.
    fetch('/api/v1/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<HealthResponse>
      })
      .then(setHealth)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 font-sans">
      <h1 className="font-display text-3xl font-bold">
        Employee Hierarchy Management System
      </h1>

      {error && (
        <Badge variant="destructive">API unreachable: {error}</Badge>
      )}

      {!error && !health && <Skeleton className="h-6 w-48" />}

      {health && (
        <Badge variant={health.status === 'ok' ? 'default' : 'destructive'}>
          status: {health.status} · db: {health.db}
        </Badge>
      )}
    </main>
  )
}

export default App
