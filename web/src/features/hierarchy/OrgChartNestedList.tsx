import { EmployeeAvatar } from '@/components/employee-avatar'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'
import type { ChartEmployee } from './types'
import { useFullHierarchy, type HierarchyTreeNode } from './useFullHierarchy'

function HierarchyBranch({
  nodes,
  onSelect,
}: {
  nodes: HierarchyTreeNode[]
  onSelect: (employee: ChartEmployee) => void
}) {
  return (
    <ul className="ml-4 list-none border-l border-border pl-3 first:ml-0 first:border-l-0 first:pl-0">
      {nodes.map(({ employee, children }) => (
        <li key={employee.id} className="py-1">
          <button
            type="button"
            className="flex w-full items-center gap-2 rounded-sm text-left hover:bg-muted"
            onClick={() => onSelect(employee)}
          >
            <EmployeeAvatar
              avatarUrl={employee.avatar_url}
              firstName={employee.first_name}
              lastName={employee.last_name}
              size={24}
            />
            <span className="font-medium">
              {employee.first_name} {employee.last_name}
            </span>
            <span className="text-sm text-muted-foreground">{employee.position}</span>
          </button>
          {children.length > 0 && <HierarchyBranch nodes={children} onSelect={onSelect} />}
        </li>
      ))}
    </ul>
  )
}

export function OrgChartNestedList({
  onSelect,
  asOf,
  className,
}: {
  onSelect: (employee: ChartEmployee) => void
  asOf: string
  className?: string
}) {
  const { tree, isLoading, isError } = useFullHierarchy(asOf)

  return (
    <div className={cn('org-chart-list', className)}>
      <h2 className="font-display text-lg font-semibold">Org chart - list view</h2>
      {isLoading && (
        <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Loading hierarchy...
        </p>
      )}
      {isError && (
        <p role="alert" className="text-sm text-status-critical">
          Could not load the hierarchy.
        </p>
      )}
      {!isLoading && !isError && tree.length === 0 && (
        <p className="text-sm text-muted-foreground">No employees yet.</p>
      )}
      {!isLoading && !isError && tree.length > 0 && (
        <HierarchyBranch nodes={tree} onSelect={onSelect} />
      )}
    </div>
  )
}
