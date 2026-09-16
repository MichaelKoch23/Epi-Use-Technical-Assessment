import type { components } from '@/lib/api-types'

export type ChartEmployee =
  | components['schemas']['EmployeeRead']
  | components['schemas']['EmployeeReadRestricted']

/** A `viewer` payload omits `salary` entirely (§9.3) rather than nulling it. */
export function hasSalary(
  employee: ChartEmployee
): employee is components['schemas']['EmployeeRead'] {
  return 'salary' in employee
}

/** One employee as laid out in the chart: the record itself, its distance
 * from the nearest root (drives the depth token / left-border colour), and
 * whatever the client currently knows about its children. */
export interface ChartNodeData {
  employee: ChartEmployee
  depth: number
  childIds: string[]
  /** `undefined` until this node's own subtree has been fetched at least
   * once - we don't know yet whether it has children to expand. */
  hasChildren: boolean | undefined
  expanded: boolean
  isRoot: boolean
}
