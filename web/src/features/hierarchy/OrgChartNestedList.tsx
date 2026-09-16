import { EmployeeAvatar } from '@/components/employee-avatar'
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

/**
 * The accessible, keyboard-navigable equivalent of the chart - a plain
 * nested list, reachable from the chart toolbar, and also the print
 * layout (§ accessibility requirements: "It is not a fallback - it is a
 * supported view").
 */
export function OrgChartNestedList({
  onSelect,
  className,
}: {
  onSelect: (employee: ChartEmployee) => void
  className?: string
}) {
  const { tree, isLoading, isError } = useFullHierarchy()

  return (
    <div className={cn('org-chart-list', className)}>
      <h2 className="font-display text-lg font-semibold">Org chart - list view</h2>
      {isLoading && <p className="text-sm text-muted-foreground">Loading hierarchy…</p>}
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
