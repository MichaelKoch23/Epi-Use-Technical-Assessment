import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { ChevronRightIcon } from 'lucide-react'
import { EmployeeAvatar } from '@/components/employee-avatar'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { depthToken } from './depthToken'
import type { ChartEmployee } from './types'

export interface EmployeeNodeData extends Record<string, unknown> {
  employee: ChartEmployee
  depth: number
  isRoot: boolean
  hasChildren: boolean | undefined
  expanded: boolean
  dropValidity: 'valid' | 'invalid' | null
  isDimmed: boolean
  childNodeIds: string[]
  onToggleExpand: (id: string) => void
}

export type EmployeeFlowNode = Node<EmployeeNodeData, 'employee'>

export function EmployeeNode({ id, data, selected, dragging }: NodeProps<EmployeeFlowNode>) {
  const {
    employee,
    depth,
    isRoot,
    hasChildren,
    expanded,
    dropValidity,
    isDimmed,
    childNodeIds,
    onToggleExpand,
  } = data
  const fullName = `${employee.first_name} ${employee.last_name}`

  return (
    <div
      id={`org-node-${id}`}
      data-depth={Math.min(depth, 4)}
      data-testid="employee-node"
      className={cn(
        'relative grid w-65 grid-cols-[40px_1fr] gap-3 rounded-md border border-l-4 border-border bg-card p-3 text-left shadow-sm transition-shadow duration-150',
        depthToken(depth),
        selected && 'border-brand-primary shadow-[0_0_0_2px_var(--color-brand-primary)]',
        dragging && 'opacity-60 shadow-md',
        dropValidity === 'valid' &&
          'border-status-safe! shadow-[0_0_0_2px_var(--color-status-safe)]',
        dropValidity === 'invalid' &&
          'cursor-not-allowed border-status-critical! shadow-[0_0_0_2px_var(--color-status-critical)]',
        isDimmed && 'opacity-35'
      )}
    >
      <Handle type="target" position={Position.Left} className="bg-border!" />
      <Handle type="source" position={Position.Right} className="bg-border!" />

      <EmployeeAvatar
        avatarUrl={employee.avatar_url}
        firstName={employee.first_name}
        lastName={employee.last_name}
        size={40}
      />

      <div className="min-w-0">
        <div className="truncate font-medium text-foreground">{fullName}</div>
        <div className="truncate text-sm text-muted-foreground">{employee.position}</div>
        <div className="mt-1 flex items-center gap-2">
          {isRoot && <Badge variant="secondary">Root</Badge>}
          {hasChildren && (
            <span className="text-xs text-muted-foreground">
              {childNodeIds.length} report{childNodeIds.length === 1 ? '' : 's'}
            </span>
          )}
        </div>
      </div>

      {hasChildren !== false && (
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={
            expanded ? childNodeIds.map((childId) => `org-node-${childId}`).join(' ') : undefined
          }
          aria-label={`${expanded ? 'Collapse' : 'Expand'} ${fullName}'s branch`}
          onClick={(event) => {
            event.stopPropagation()
            onToggleExpand(id)
          }}
          className="absolute top-1/2 -right-5.5 grid size-11 -translate-y-1/2 place-items-center rounded-full"
        >
          <span className="grid size-6 place-items-center rounded-full border border-border bg-background shadow-sm">
            <ChevronRightIcon className={cn('size-3.5 transition-transform', expanded && 'rotate-180')} />
          </span>
        </button>
      )}
    </div>
  )
}
