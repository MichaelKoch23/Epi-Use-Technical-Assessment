import type { components } from '@/lib/api-types'

export type ChartEmployee =
  | components['schemas']['EmployeeRead']
  | components['schemas']['EmployeeReadRestricted']

export function hasSalary(
  employee: ChartEmployee
): employee is components['schemas']['EmployeeRead'] {
  return 'salary' in employee
}

export interface ChartNodeData {
  employee: ChartEmployee
  depth: number
  childIds: string[]
  hasChildren: boolean | undefined
  expanded: boolean
  isRoot: boolean
}
