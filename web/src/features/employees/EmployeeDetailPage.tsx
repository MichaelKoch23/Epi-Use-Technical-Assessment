import { useParams } from 'react-router'

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()

  return (
    <div>
      <h1 className="font-display text-2xl font-bold">Employee {id}</h1>
      <p className="text-muted-foreground">Coming soon.</p>
    </div>
  )
}
